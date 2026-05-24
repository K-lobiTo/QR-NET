#!/usr/bin/env python3
"""
Script Receptor — Transferencia de Archivos QR-NET
==================================================
Captura fragmentos de archivos desde QRs usando cámara y reensambl el archivo.

Uso:
    python receiver.py [--host 0.0.0.0] [--port 9000] [--camera 0]

Ejemplo:
    python receiver.py --host 192.168.1.101 --port 9000
    
El receptor:
1. Inicia un nodo QR-NET en espera
2. Conecta la cámara y comienza a capturar QRs
3. Decodifica los fragmentos a medida que llegan
4. Reensambl automáticamente cuando completa
5. Verifica integridad con hash SHA256
6. Guarda el archivo recibido como "received_<nombre>"
"""
import base64
import json
import sys
import os
import argparse
import time
import threading

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from layer1_physical.dispositivo_luz_adaptador import DispositivoLuzAdaptador
from layer2_3_network.node import QRNetNode
from layer7_anonymous.app import AnonymousApp
from layer7_file_transfer.file_transfer_app import FileTransferApp


class ReceiverApp:
    """Aplicación receptora de archivos con captura de QRs."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9000, camera_index: int = 0):
        print("\n" + "="*70)
        print("QR-NET FILE TRANSFER — RECEPTOR")
        print("="*70)

        # Inicializar capas
        self.node = QRNetNode(host, port)
        self.node.start()
        print(f"\n[Receptor] Nodo iniciado en {host}:{port}")
        print(f"[Receptor] ID del nodo: {self.node.node_id[:8]}...\n")

        self.anon_app = AnonymousApp(self.node)
        self.file_transfer_app = FileTransferApp(self.anon_app)

        # Dispositivo de luz para capturar QRs
        self.luz_device = DispositivoLuzAdaptador(camera_index=camera_index)
        self.camera_running = False
        self.camera_thread = None

    def start_camera_capture(self) -> None:
        """Inicia la captura de QRs en un thread separado."""
        if self.camera_running:
            return

        self.camera_running = True
        self.camera_thread = threading.Thread(
            target=self._camera_capture_loop,
            daemon=True
        )
        self.camera_thread.start()
        print("[Receptor] Captura de cámara iniciada\n")

    def stop_camera_capture(self) -> None:
        """Detiene la captura de QRs."""
        self.camera_running = False
        if self.camera_thread:
            self.camera_thread.join(timeout=5)
        self.luz_device.close_camera()
        print("[Receptor] Captura de cámara detenida\n")

    def _camera_capture_loop(self) -> None:
        """Loop de captura de QRs desde la cámara."""
        try:
            self.luz_device.open_camera()
            print("[Luz-L1] Cámara abierta, buscando QRs...\n")

            captured_frames = 0
            failed_frames = 0

            while self.camera_running:
                try:
                    # Intentar decodificar un QR
                    frame_data = self.luz_device.receive()

                    if frame_data:
                        captured_frames += 1
                        payload = frame_data.get("payload")
                        if payload:
                            # Procesar el fragment recibido
                            self._process_received_fragment(payload)
                    else:
                        failed_frames += 1

                    # time.sleep(0.1)  # Pequeña pausa entre intentos

                except Exception as e:
                    print(f"[Luz-L1] Error capturando: {e}")
                    failed_frames += 1
                    time.sleep(0.5)

        except Exception as e:
            print(f"[Luz-L1] Error crítico en captura: {e}")
        finally:
            self.luz_device.close_camera()

    def _process_received_fragment(self, raw_payload: bytes) -> None:
        """Procesa un fragmento recibido desde la cámara."""
        try:
            # ----------------------------------------------------------
            # Payload JSON -> dict
            # ----------------------------------------------------------
            fragment = json.loads(raw_payload.decode())
            transfer_id = fragment["transfer_id"]
            chunk_number = fragment["chunk_number"]
            total_chunks = fragment["total_chunks"]
            encoded_data = fragment["data"]
            # ----------------------------------------------------------
            # Base64 -> bytes reales
            # ----------------------------------------------------------
            chunk_data = base64.b64decode(encoded_data)
            # ----------------------------------------------------------
            # Directorio temporal de recepción
            # ----------------------------------------------------------
            transfer_dir = os.path.join(
                "temp-rx",
                transfer_id
            )
            os.makedirs(transfer_dir, exist_ok=True)
            # ----------------------------------------------------------
            # Guardar chunk
            # ----------------------------------------------------------
            chunk_path = os.path.join(
                transfer_dir,
                f"{chunk_number:010d}.chunk"
            )
            with open(chunk_path, "wb") as f:
                f.write(chunk_data)
            print(
                f"[RX] Fragmento {chunk_number + 1}/{total_chunks} "
                f"recibido"
            )
            # ----------------------------------------------------------
            # Verificar completitud
            # ----------------------------------------------------------
            received_chunks = [
                f for f in os.listdir(transfer_dir)
                if f.endswith(".chunk")
            ]
            if len(received_chunks) == total_chunks:
                print("[RX] Todos los fragmentos recibidos")
                self._rebuild_file(
                    transfer_dir,
                    total_chunks
                )
        except Exception as e:
            print(f"[Receptor] Error procesando fragmento: {e}")

    def wait_for_file(self, timeout: float = 300) -> bool:
        """
        Espera a recibir un archivo completamente.

        Args:
            timeout: Segundos a esperar máximo

        Returns:
            True si recibió al menos un archivo
        """
        print(f"[Receptor] Esperando archivos (timeout: {timeout}s)...\n")

        start_time = time.time()
        last_count = 0

        while time.time() - start_time < timeout:
            files = self.file_transfer_app.receive_files()

            # Mostrar progreso si hay nuevos archivos
            if len(files) > last_count:
                last_count = len(files)
                for f in files:
                    if f.get("status") == "completed":
                        print(f"\n✓ Archivo completado: {f.get('output_path')}")
                    else:
                        progress = f.get("received_chunks", 0)
                        total = f.get("total_chunks", 0)
                        percent = (progress / total * 100) if total > 0 else 0
                        print(f"[{progress}/{total}] {f.get('filename')} ({percent:.0f}%)")

            time.sleep(1)

        files = self.file_transfer_app.receive_files()
        return len(files) > 0

    def list_received_files(self) -> None:
        """Lista los archivos recibidos."""
        files = self.file_transfer_app.receive_files()

        if not files:
            print("\n[Receptor] No hay archivos recibidos.\n")
            return

        print(f"\n{'─'*70}")
        print(f"Archivos recibidos ({len(files)}):")
        print(f"{'─'*70}")

        for i, f in enumerate(files, 1):
            filename = f.get("filename")
            size = f.get("file_size")
            status = f.get("status", "unknown")
            output = f.get("output_path", "N/A")

            size_str = f"{size} bytes" if size else "?"
            print(f"\n{i}. {filename}")
            print(f"   Tamaño: {size_str}")
            print(f"   Estado: {status}")
            if status == "completed":
                print(f"   Guardado en: {output}")

        print(f"\n{'─'*70}\n")

    def _rebuild_file(self, transfer_dir: str, total_chunks: int) -> None:

        output_path = os.path.join(
            transfer_dir,
            "reconstructed_file"
        )

        with open(output_path, "wb") as outfile:
            for i in range(total_chunks):
                chunk_path = os.path.join(
                    transfer_dir,
                    f"{i:010d}.chunk"
                )

                with open(chunk_path, "rb") as infile:
                    outfile.write(infile.read())

        print(f"[RX] Archivo reconstruido: {output_path}")

    def cleanup(self):
        """Limpia recursos."""
        self.stop_camera_capture()
        self.node.stop()
        print("[Receptor] Aplicación cerrada.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Receptor de archivos QR-NET",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python receiver.py
  python receiver.py --host 192.168.1.101 --port 9000
  python receiver.py --camera 1  # Usar segunda cámara
        """
    )

    parser.add_argument("--host", default="0.0.0.0", help="Host local (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9000, help="Puerto UDP (default: 9000)")
    parser.add_argument("--camera", type=int, default=0, help="Índice de cámara (default: 0)")
    parser.add_argument("--timeout", type=float, default=300, help="Timeout en segundos (default: 300)")
    parser.add_argument("--no-listen", action="store_true", help="No capturar con cámara")

    args = parser.parse_args()

    try:
        # Crear aplicación receptora
        receiver = ReceiverApp(args.host, args.port, args.camera)

        # Iniciar captura de cámara
        if not args.no_listen:
            receiver.start_camera_capture()

        # Esperar a que lleguen archivos
        receiver.wait_for_file(args.timeout)

        # Mostrar resultado
        receiver.list_received_files()

    except KeyboardInterrupt:
        print("\n\n[Receptor] Cancelado por el usuario.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'receiver' in locals():
            receiver.cleanup()


if __name__ == "__main__":
    main()
