"""
Transferencia de Archivos — Implementación
===========================================
"""

import os
import json
import time
import uuid
import hashlib
import base64
from enum import Enum
from dataclasses import dataclass, asdict, field
from typing import Optional, Callable, Dict
import threading


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
MAX_FRAGMENT_PAYLOAD = 90  # bytes por fragmento (debe caber en JSON de capa 7)
MSG_TYPE_FILE_START = "FILE_START"
MSG_TYPE_FILE_CHUNK = "FILE_CHUNK"
MSG_TYPE_FILE_ACK   = "FILE_ACK"
MSG_TYPE_FILE_END   = "FILE_END"


class TransferState(Enum):
    """Estados de una transferencia."""
    PENDING     = "PENDING"     # Esperando iniciar
    IN_PROGRESS = "IN_PROGRESS" # Transfiriendo fragmentos
    COMPLETED   = "COMPLETED"   # Completado exitosamente
    FAILED      = "FAILED"      # Error durante la transferencia
    CANCELLED   = "CANCELLED"   # Cancelada por el usuario


@dataclass
class FileTransferInfo:
    """Metadatos de un archivo en transferencia."""
    transfer_id: str          # ID único de la transferencia
    filename: str             # Nombre del archivo original
    file_size: int            # Tamaño total en bytes
    file_hash: str            # SHA256 del archivo completo
    total_chunks: int         # Número total de fragmentos
    timestamp: float = field(default_factory=time.time)
    state: TransferState = TransferState.PENDING


@dataclass
class FileFragment:
    """Un fragmento de archivo."""
    transfer_id: str          # ID de la transferencia
    chunk_number: int         # Número de este fragmento (0-indexed)
    total_chunks: int         # Total de fragmentos en la transferencia
    data: str                 # Datos en base64 (seguro para JSON)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @staticmethod
    def from_json(raw: str) -> "FileFragment":
        return FileFragment(**json.loads(raw))


class FileTransferManager:
    """
    Gestiona transferencias de archivos fragmentadas.
    
    Responsabilidades:
    - Fragmentar archivos para transmisión
    - Reensamblar fragmentos recibidos
    - Verificar integridad
    - Rastrear estado de transferencias
    """

    def __init__(self):
        self._transfers: Dict[str, FileTransferInfo] = {}
        self._fragments: Dict[str, Dict[int, bytes]] = {}  # transfer_id -> {chunk_n -> data}
        self._callbacks: Dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    # -----------------------------------------------------------------------
    # EMISOR: Fragmentar un archivo
    # -----------------------------------------------------------------------

    @staticmethod
    def calculate_file_hash(filepath: str) -> str:
        """Calcula el hash SHA256 del archivo."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def split_file(self, filepath: str) -> tuple[FileTransferInfo, list[FileFragment]]:
        """
        Divide un archivo en fragmentos.

        Args:
            filepath: Ruta al archivo a enviar

        Returns:
            Tupla (FileTransferInfo, lista de FileFragments)

        Raises:
            FileNotFoundError: Si el archivo no existe
            IOError: Error de lectura
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        file_hash = self.calculate_file_hash(filepath)
        transfer_id = str(uuid.uuid4())

        # Calcular número de fragmentos necesarios
        total_chunks = (file_size + MAX_FRAGMENT_PAYLOAD - 1) // MAX_FRAGMENT_PAYLOAD

        # Crear info de transferencia
        transfer_info = FileTransferInfo(
            transfer_id=transfer_id,
            filename=filename,
            file_size=file_size,
            file_hash=file_hash,
            total_chunks=total_chunks,
            state=TransferState.IN_PROGRESS
        )

        # Leer archivo y crear fragmentos
        fragments = []
        with open(filepath, 'rb') as f:
            for chunk_num in range(total_chunks):
                chunk_data = f.read(MAX_FRAGMENT_PAYLOAD)
                # Codificar en base64 para seguridad en JSON
                encoded_data = base64.b64encode(chunk_data).decode('utf-8')
                
                fragment = FileFragment(
                    transfer_id=transfer_id,
                    chunk_number=chunk_num,
                    total_chunks=total_chunks,
                    data=encoded_data
                )
                fragments.append(fragment)

        with self._lock:
            self._transfers[transfer_id] = transfer_info

        print(f"[L5-TX] Archivo {filename} fragmentado en {total_chunks} fragmentos")
        return transfer_info, fragments

    # -----------------------------------------------------------------------
    # RECEPTOR: Reensamblar fragmentos
    # -----------------------------------------------------------------------

    def receive_fragment(self, fragment: FileFragment) -> bool:
        """
        Recibe un fragmento.

        Args:
            fragment: FileFragment recibido

        Returns:
            True si la transferencia se completó, False si falta(n) fragmento(s)
        """
        transfer_id = fragment.transfer_id

        with self._lock:
            # Crear entrada si no existe transferencia conocida
            if transfer_id not in self._fragments:
                self._fragments[transfer_id] = {}
            
            # Decodificar base64 a bytes
            try:
                chunk_data = base64.b64decode(fragment.data)
            except Exception as e:
                print(f"[L5-RX] Error decodificando fragmento {fragment.chunk_number}: {e}")
                return False

            # Almacenar fragmento
            self._fragments[transfer_id][fragment.chunk_number] = chunk_data

            # Verificar si está completo
            received_chunks = len(self._fragments[transfer_id])
            total_expected = fragment.total_chunks

            if received_chunks == total_expected:
                # Transferencia completa
                print(f"[L5-RX] Todos los {total_expected} fragmentos recibidos ({transfer_id})")
                return True

        print(f"[L5-RX] Fragmento {fragment.chunk_number + 1}/{fragment.total_chunks} recibido")
        return False

    def reassemble_file(self, transfer_id: str, output_path: str) -> bool:
        """
        Reensambl los fragmentos en un archivo.

        Args:
            transfer_id: ID de la transferencia
            output_path: Ruta donde guardar el archivo

        Returns:
            True si el reensamblaje fue exitoso

        Raises:
            ValueError: Si no hay suficientes fragmentos
        """
        with self._lock:
            if transfer_id not in self._fragments:
                raise ValueError(f"Transferencia desconocida: {transfer_id}")

            fragments_dict = self._fragments[transfer_id]

        # Verificar que están todos los fragmentos
        chunk_numbers = sorted(fragments_dict.keys())
        expected_chunks = set(range(len(fragments_dict)))
        if set(chunk_numbers) != expected_chunks:
            missing = expected_chunks - set(chunk_numbers)
            raise ValueError(f"Faltan fragmentos: {missing}")

        # Escribir archivo
        try:
            with open(output_path, 'wb') as f:
                for chunk_num in chunk_numbers:
                    f.write(fragments_dict[chunk_num])
            print(f"[L5-RX] Archivo reensamblado: {output_path}")
            return True
        except IOError as e:
            print(f"[L5-RX] Error escribiendo archivo: {e}")
            return False

    def verify_transferred_file(self, transfer_id: str, filepath: str) -> bool:
        """
        Verifica que el archivo reensamblado coincida con el original.

        Args:
            transfer_id: ID de la transferencia
            filepath: Ruta al archivo reensamblado

        Returns:
            True si el hash coincide
        """
        if not os.path.exists(filepath):
            print(f"[L5-Verify] Archivo no existe: {filepath}")
            return False

        received_hash = self.calculate_file_hash(filepath)

        with self._lock:
            if transfer_id in self._transfers:
                original_hash = self._transfers[transfer_id].file_hash
                if received_hash == original_hash:
                    print(f"[L5-Verify] Hash verificado correctamente")
                    self._transfers[transfer_id].state = TransferState.COMPLETED
                    return True
                else:
                    print(f"[L5-Verify] Hash mismatch!")
                    print(f"  Original:  {original_hash}")
                    print(f"  Recibido:  {received_hash}")
                    self._transfers[transfer_id].state = TransferState.FAILED
                    return False

        return False

    # -----------------------------------------------------------------------
    # Utilidades
    # -----------------------------------------------------------------------

    def get_transfer_info(self, transfer_id: str) -> Optional[FileTransferInfo]:
        """Obtiene información de una transferencia."""
        with self._lock:
            return self._transfers.get(transfer_id)

    def get_transfer_progress(self, transfer_id: str) -> tuple[int, int]:
        """Retorna (fragmentos_recibidos, fragmentos_totales)."""
        with self._lock:
            if transfer_id not in self._fragments:
                return 0, 0
            received = len(self._fragments[transfer_id])
            if transfer_id in self._transfers:
                total = self._transfers[transfer_id].total_chunks
                return received, total
            return received, 0

    def cleanup_transfer(self, transfer_id: str) -> None:
        """Limpia los datos de una transferencia completada/fallida."""
        with self._lock:
            self._fragments.pop(transfer_id, None)
            # Nota: Mantener _transfers para historial

    # -----------------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------------

    def on_transfer_complete(self, handler: Callable[[str], None]) -> None:
        """Registra callback para cuando completa una transferencia."""
        event_type = "transfer_complete"
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(handler)

    def _trigger_callback(self, event_type: str, *args) -> None:
        """Ejecuta los callbacks registrados para un evento."""
        if event_type in self._callbacks:
            for handler in self._callbacks[event_type]:
                try:
                    handler(*args)
                except Exception as e:
                    print(f"[L5] Error en callback: {e}")
