#!/usr/bin/env python3
"""
Script Emisor — Transferencia de Archivos QR-NET
=================================================
Fragmenta un archivo y lo envía mostrando cada fragmento como QR en pantalla.

Uso:
    python sender.py <archivo> <nodo_destino> [--host 0.0.0.0] [--port 9000]

Ejemplo:
    python sender.py documento.pdf node-2 --host 192.168.1.100 --port 9000

El emisor:
1. Carga el archivo
2. Genera fragmentos (cada uno codificado como QR)
3. Muestra cada QR en pantalla durante 2 segundos
4. El receptor captura los QRs con su cámara
5. El receptor reensambl el archivo
"""

import sys
import os
import argparse
import time
import threading

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from layer1_physical.dispositivo_luz_adaptador import BROADCAST_MAC, DispositivoLuzAdaptador
from layer2_3_network.node import QRNetNode
from layer7_anonymous.app import AnonymousApp
from layer7_file_transfer.file_transfer_app import FileTransferApp
from qr_displayer import QRDisplayer


class SenderApp:
    """Aplicación emisora de archivos con visualización de QRs."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9000):
        print("\n" + "="*70)
        print("QR-NET FILE TRANSFER — EMISOR")
        print("="*70)

        # Inicializar capas
        self.node = QRNetNode(host, port)
        self.node.start()
        print(f"\n[Emisor] Nodo iniciado en {host}:{port}")
        print(f"[Emisor] ID del nodo: {self.node.node_id[:8]}...\n")

        self.anon_app = AnonymousApp(self.node)
        self.file_transfer_app = FileTransferApp(self.anon_app)

        # Dispositivo de luz para mostrar QRs
        self.luz_device = DispositivoLuzAdaptador()

    def send_file_with_qr_display(self, filepath: str, dst_node: str) -> bool:
        """
        Envía un archivo mostrando cada fragmento como QR.

        Args:
            filepath: Ruta del archivo a enviar
            dst_node: ID del nodo receptor

        Returns:
            True si envío exitoso
        """
        if not os.path.exists(filepath):
            print(f"\n✗ Archivo no encontrado: {filepath}\n")
            return False

        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)

        print(f"\n{'─'*70}")
        print(f"Archivo: {filename}")
        print(f"Tamaño: {filesize} bytes")
        print(f"Destino: {dst_node}")
        print(f"{'─'*70}\n")

        # Obtener información de fragmentos
        from layer5_transfer.file_transfer import FileTransferManager
        manager = FileTransferManager()
        transfer_info, fragments = manager.split_file(filepath)

        print(f"Fragmentos a enviar: {len(fragments)}\n")

        # Thread para enviar en paralelo
        send_thread = threading.Thread(
            target=self.file_transfer_app.send_file,
            args=(dst_node, filepath),
            daemon=True
        )
        send_thread.start()

        # Mostrar QRs en pantalla
        print("Mostrando fragmentos en pantalla:\n")
        for i, fragment in enumerate(fragments, 1):
            print(f"  [{i}/{len(fragments)}] Mostrando fragmento en pantalla...", end="", flush=True)

            # Codificar fragmento como bytes para mostrar en QR
            import json
            fragment_json = fragment.to_json()
            fragment_bytes = fragment_json.encode('utf-8')

            # Mostrar QR (simula transmisión por luz)
            try:
                # En un sistema real, usarías broadcast para que cualquier receptor pueda leerlo.
                self.luz_device.send(BROADCAST_MAC, fragment_bytes)
                # Por ahora, mostramos solo el fragmento
                # print(f" ✓ ({len(fragment_bytes)} bytes)")
                # time.sleep(2)  # Mostrar 2 segundos
            except Exception as e:
                print(f" ✗ Error: {e}")
                return False

        # Esperar a que termine el envío
        send_thread.join(timeout=60)
        viewer = QRDisplayer()
        viewer.show_sequence(len(fragments))
        print(f"\n{'─'*70}")
        print("✓ Emisión completada\n")
        return True

    def cleanup(self):
        """Limpia recursos."""
        self.node.stop()
        self.luz_device.close_camera()
        print("[Emisor] Aplicación cerrada.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Emisor de archivos QR-NET",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python sender.py documento.pdf node-2
  python sender.py imagen.jpg abc123def456 --host 192.168.1.100 --port 9000
        """
    )

    parser.add_argument("archivo", help="Ruta del archivo a enviar")
    parser.add_argument("destino", help="ID del nodo receptor")
    parser.add_argument("--host", default="0.0.0.0", help="Host local (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9000, help="Puerto UDP (default: 9000)")
    parser.add_argument("--no-display", action="store_true", help="No mostrar QRs (modo silencioso)")

    args = parser.parse_args()

    try:
        # Crear aplicación emisora
        sender = SenderApp(args.host, args.port)

        # Enviar archivo
        if args.no_display:
            # Modo silencioso (solo envía)
            sender.file_transfer_app.send_file(args.destino, args.archivo)
        else:
            # Modo normal (muestra QRs)
            sender.send_file_with_qr_display(args.archivo, args.destino)

    except KeyboardInterrupt:
        print("\n\n[Emisor] Cancelado por el usuario.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'sender' in locals():
            sender.cleanup()


if __name__ == "__main__":
    main()
