"""
Aplicación de Transferencia de Archivos
========================================
Integra Capa 5 (transferencia) con Capa 7 (aplicación anónima).
Maneja el flujo de envío/recepción de archivos sobre remote-QR-net.
"""

import json
import time
import threading
from typing import Optional, Callable
from layer5_transfer.file_transfer import (
    FileTransferManager,
    FileFragment,
    MSG_TYPE_FILE_START,
    MSG_TYPE_FILE_CHUNK,
    MSG_TYPE_FILE_ACK,
    MSG_TYPE_FILE_END,
)
from layer7_anonymous.app import AppMessage, MSG_POST


class FileTransferApp:
    """
    Aplicación de transferencia de archivos.
    
    Uso:
        # Emisor
        app = FileTransferApp(anonymous_app)
        app.send_file(dst_node, "archivo.bin")
        
        # Receptor
        received_file = app.receive_files()[0]
    """

    def __init__(self, anonymous_app):
        """
        Args:
            anonymous_app: Instancia de AnonymousApp (Capa 7)
        """
        self.anon_app = anonymous_app
        self.manager = FileTransferManager()
        self._received_files: dict = {}
        self._send_lock = threading.Lock()
        self._receive_lock = threading.Lock()
        
        # Registrar callback para recibir mensajes
        self.anon_app.on_message(self._on_message_received)
        
        print("[FileTransferApp] Aplicación de transferencia iniciada")

    # -----------------------------------------------------------------------
    # EMISOR
    # -----------------------------------------------------------------------

    def send_file(self, dst_node: str, filepath: str, topic: str = "files") -> str:
        """
        Envía un archivo fragmentado a otro nodo.

        Args:
            dst_node: ID del nodo receptor
            filepath: Ruta al archivo local
            topic: Tópico donde publicar los fragmentos (para sincronización)

        Returns:
            transfer_id único para rastrear la transferencia

        Raises:
            FileNotFoundError: Si el archivo no existe
        """
        with self._send_lock:
            # Fragmentar el archivo
            transfer_info, fragments = self.manager.split_file(filepath)
            transfer_id = transfer_info.transfer_id

            print(f"\n[FileTransferApp-TX] Iniciando transferencia {transfer_id}")
            print(f"  Archivo: {transfer_info.filename}")
            print(f"  Tamaño: {transfer_info.file_size} bytes")
            print(f"  Fragmentos: {transfer_info.total_chunks}")
            print(f"  Hash: {transfer_info.file_hash[:16]}...")

            # 1. Enviar mensaje FILE_START
            start_msg = {
                "msg_type": MSG_TYPE_FILE_START,
                "transfer_id": transfer_id,
                "filename": transfer_info.filename,
                "file_size": transfer_info.file_size,
                "file_hash": transfer_info.file_hash,
                "total_chunks": transfer_info.total_chunks,
            }
            
            app_msg = AppMessage(
                msg_type="FILE_TRANSFER",
                content=json.dumps(start_msg),
                is_public=True,
            )
            self.anon_app.send_chat(dst_node, app_msg.to_json())
            time.sleep(0.5)

            # 2. Enviar cada fragmento
            for i, fragment in enumerate(fragments, 1):
                chunk_msg = {
                    "msg_type": MSG_TYPE_FILE_CHUNK,
                    "transfer_id": transfer_id,
                    "chunk_number": fragment.chunk_number,
                    "total_chunks": fragment.total_chunks,
                    "data": fragment.data,
                }
                
                app_msg = AppMessage(
                    msg_type="FILE_TRANSFER",
                    content=json.dumps(chunk_msg),
                    is_public=True,
                )
                self.anon_app.send_chat(dst_node, app_msg.to_json())
                
                progress = f"{i}/{transfer_info.total_chunks}"
                print(f"  [{progress}] Fragmento {i} enviado")
                time.sleep(0.1)  # Pequeña pausa entre fragmentos

            # 3. Enviar FILE_END
            end_msg = {
                "msg_type": MSG_TYPE_FILE_END,
                "transfer_id": transfer_id,
                "file_hash": transfer_info.file_hash,
            }
            
            app_msg = AppMessage(
                msg_type="FILE_TRANSFER",
                content=json.dumps(end_msg),
                is_public=True,
            )
            self.anon_app.send_chat(dst_node, app_msg.to_json())
            
            print(f"\n[FileTransferApp-TX] Transferencia {transfer_id} completada\n")
            return transfer_id

    # -----------------------------------------------------------------------
    # RECEPTOR
    # -----------------------------------------------------------------------

    def _on_message_received(self, msg: AppMessage) -> None:
        """Callback interno para procesar mensajes de transferencia de archivos."""
        if msg.msg_type != "FILE_TRANSFER":
            return

        try:
            data = json.loads(msg.content)
            msg_type = data.get("msg_type")
            transfer_id = data.get("transfer_id")

            if msg_type == MSG_TYPE_FILE_START:
                self._handle_file_start(transfer_id, data)
            elif msg_type == MSG_TYPE_FILE_CHUNK:
                self._handle_file_chunk(transfer_id, data)
            elif msg_type == MSG_TYPE_FILE_END:
                self._handle_file_end(transfer_id, data)

        except json.JSONDecodeError:
            print("[FileTransferApp-RX] Error decodificando mensaje de transferencia")

    def _handle_file_start(self, transfer_id: str, data: dict) -> None:
        """Procesa el inicio de una transferencia."""
        with self._receive_lock:
            filename = data.get("filename")
            file_size = data.get("file_size")
            total_chunks = data.get("total_chunks")
            file_hash = data.get("file_hash")

            self._received_files[transfer_id] = {
                "filename": filename,
                "file_size": file_size,
                "total_chunks": total_chunks,
                "file_hash": file_hash,
                "received_chunks": 0,
            }

            print(f"\n[FileTransferApp-RX] Recibiendo archivo: {filename}")
            print(f"  Transfer ID: {transfer_id}")
            print(f"  Tamaño: {file_size} bytes")
            print(f"  Fragmentos: {total_chunks}")
            print(f"  Hash: {file_hash[:16]}...")

    def _handle_file_chunk(self, transfer_id: str, data: dict) -> None:
        """Procesa un fragmento recibido."""
        chunk_number = data.get("chunk_number")
        total_chunks = data.get("total_chunks")
        encoded_data = data.get("data")

        # Crear fragmento y procesarlo
        fragment = FileFragment(
            transfer_id=transfer_id,
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            data=encoded_data,
        )

        is_complete = self.manager.receive_fragment(fragment)

        with self._receive_lock:
            if transfer_id in self._received_files:
                self._received_files[transfer_id]["received_chunks"] += 1
                progress = self._received_files[transfer_id]["received_chunks"]
                print(f"  [{progress}/{total_chunks}] Fragmento recibido")

        if is_complete:
            self._handle_file_end_auto(transfer_id)

    def _handle_file_end(self, transfer_id: str, data: dict) -> None:
        """Procesa el fin de una transferencia."""
        print(f"\n[FileTransferApp-RX] Transferencia {transfer_id} finalizada")

    def _handle_file_end_auto(self, transfer_id: str) -> None:
        """Maneja automáticamente el final de una transferencia cuando llegan todos los fragmentos."""
        with self._receive_lock:
            if transfer_id not in self._received_files:
                return

            file_info = self._received_files[transfer_id]
            filename = file_info["filename"]
            file_hash = file_info["file_hash"]

        # Ruta de salida
        output_path = f"received_{filename}"

        # Reensamblar
        if self.manager.reassemble_file(transfer_id, output_path):
            # Verificar integridad
            if self.manager.verify_transferred_file(transfer_id, output_path):
                print(f"\n✓ Archivo guardado: {output_path}")
                with self._receive_lock:
                    self._received_files[transfer_id]["status"] = "completed"
                    self._received_files[transfer_id]["output_path"] = output_path
            else:
                print(f"\n✗ Verificación de hash fallida")
                with self._receive_lock:
                    self._received_files[transfer_id]["status"] = "failed"
        else:
            print(f"\n✗ Error reensamblando archivo")
            with self._receive_lock:
                self._received_files[transfer_id]["status"] = "failed"

    # -----------------------------------------------------------------------
    # Utilidades
    # -----------------------------------------------------------------------

    def receive_files(self) -> list:
        """Retorna la lista de archivos recibidos."""
        with self._receive_lock:
            return list(self._received_files.values())

    def get_transfer_status(self, transfer_id: str) -> Optional[dict]:
        """Obtiene el estado de una transferencia."""
        with self._receive_lock:
            return self._received_files.get(transfer_id)

    def wait_for_transfer(self, transfer_id: str, timeout: float = 300) -> Optional[str]:
        """
        Espera a que se complete una transferencia.

        Args:
            transfer_id: ID de la transferencia
            timeout: Segundos a esperar máximo

        Returns:
            Ruta del archivo si completa exitosamente, None si falla o timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_transfer_status(transfer_id)
            if status:
                if status.get("status") == "completed":
                    return status.get("output_path")
                elif status.get("status") == "failed":
                    return None

            time.sleep(0.5)

        print(f"[FileTransferApp] Timeout esperando transferencia {transfer_id}")
        return None
