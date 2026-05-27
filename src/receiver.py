#!/usr/bin/env python3
"""
Script Receptor — Transferencia de Archivos QR-NET
==================================================
Captura fragmentos de archivos desde QRs usando cámara y reensambl el archivo.

Uso:
    python receiver.py [--camera 0]

Ejemplo:
    python receiver.py --camera 0
    
El receptor:
1. Conecta la cámara y comienza a capturar QRs
2. Decodifica los fragmentos a medida que llegan
3. Guarda los fragmentos temporales en `temp-rx/<transfer_id>`
4. Reensambl automáticamente cuando se reciben todos los fragmentos
5. Guarda el archivo recibido como `reconstructed_file`
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


class ReceiverApp:
    """Aplicación receptora de archivos con captura de QRs."""

    def __init__(self, camera_index: int = 0):
        print("\n" + "="*70)
        print("QR-NET FILE TRANSFER — RECEPTOR")
        print("="*70)

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
        while time.time() - start_time < timeout:
            completed = self._find_completed_files()
            if completed:
                for path in completed:
                    print(f"\n✓ Archivo completado: {path}")
                return True
            time.sleep(1)

        return False

    def list_received_files(self) -> None:
        """Lista los archivos recibidos."""
        completed = self._find_completed_files()

        if not completed:
            print("\n[Receptor] No hay archivos recibidos.\n")
            return

        print(f"\n{'─'*70}")
        print(f"Archivos recibidos ({len(completed)}):")
        print(f"{'─'*70}")

        for i, path in enumerate(completed, 1):
            size = os.path.getsize(path) if os.path.exists(path) else 0
            transfer_id = os.path.basename(os.path.dirname(path))

            print(f"\n{i}. {os.path.basename(path)}")
            print(f"   Transfer ID: {transfer_id}")
            print(f"   Tamaño: {size} bytes")
            print(f"   Guardado en: {path}")

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

    def _find_completed_files(self) -> list[str]:
        base_dir = "temp-rx"
        completed = []
        if not os.path.exists(base_dir):
            return completed

        for transfer_id in os.listdir(base_dir):
            transfer_dir = os.path.join(base_dir, transfer_id)
            if not os.path.isdir(transfer_dir):
                continue
            output_path = os.path.join(transfer_dir, "reconstructed_file")
            if os.path.isfile(output_path):
                completed.append(output_path)
        return sorted(completed)

    def cleanup(self):
        """Limpia recursos."""
        self.stop_camera_capture()
        print("[Receptor] Aplicación cerrada.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Receptor de archivos QR-NET",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python receiver.py
  python receiver.py --camera 1  # Usar segunda cámara
        """
    )

    parser.add_argument("--camera", type=int, default=0, help="Índice de cámara (default: 0)")
    parser.add_argument("--timeout", type=float, default=300, help="Timeout en segundos (default: 300)")
    parser.add_argument("--no-listen", action="store_true", help="No capturar con cámara")

    args = parser.parse_args()

    try:
        # Crear aplicación receptora
        receiver = ReceiverApp(args.camera)

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
