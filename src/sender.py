#!/usr/bin/env python3
"""
Script Emisor — Transferencia de Archivos QR-NET
=================================================
Fragmenta un archivo y lo envía mostrando cada fragmento como QR en pantalla.

Uso:
    python sender.py <archivo> [--no-display]

Ejemplo:
    python sender.py documento.pdf

El emisor:
1. Carga el archivo
2. Genera fragmentos (cada uno codificado como QR)
3. Codifica cada fragmento como QR
4. Guarda los QR en `temp-qr/`
5. Opcionalmente muestra la secuencia de QRs en pantalla
6. El receptor captura los QRs con su cámara
7. El receptor reensambl el archivo
"""

import sys
import os
import argparse

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from layer1_physical.dispositivo_luz_adaptador import BROADCAST_MAC, DispositivoLuzAdaptador
from qr_displayer import QRDisplayer


class SenderApp:
    """Aplicación emisora de archivos con visualización de QRs."""

    def __init__(self):
        print("\n" + "="*70)
        print("QR-NET FILE TRANSFER — EMISOR")
        print("="*70)

        # Dispositivo de luz para mostrar QRs
        self.luz_device = DispositivoLuzAdaptador()

    def send_file_with_qr_display(self, filepath: str, show_display: bool = True) -> bool:
        """
        Envía un archivo mostrando cada fragmento como QR.

        Args:
            filepath: Ruta del archivo a enviar
            show_display: Si True, muestra la secuencia de QRs en pantalla.

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
        print(f"{'─'*70}\n")

        from layer5_transfer.file_transfer import FileTransferManager
        manager = FileTransferManager()
        transfer_info, fragments = manager.split_file(filepath)

        print(f"Fragmentos a enviar: {len(fragments)}\n")

        print("Mostrando fragmentos en pantalla:\n")
        for i, fragment in enumerate(fragments, 1):
            print(f"  [{i}/{len(fragments)}] Mostrando fragmento en pantalla...", end="", flush=True)

            fragment_bytes = fragment.to_json().encode('utf-8')

            try:
                self.luz_device.send(BROADCAST_MAC, fragment_bytes)
            except Exception as e:
                print(f" ✗ Error: {e}")
                return False

        if show_display:
            viewer = QRDisplayer()
            viewer.show_sequence(len(fragments))

        print(f"\n{'─'*70}")
        print("✓ Emisión completada\n")
        return True

    def cleanup(self):
        """Limpia recursos."""
        self.luz_device.close_camera()
        print("[Emisor] Aplicación cerrada.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Emisor de archivos QR-NET",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python sender.py documento.pdf
  python sender.py imagen.jpg --no-display
        """
    )

    parser.add_argument("archivo", help="Ruta del archivo a enviar")
    parser.add_argument("--no-display", action="store_true", help="No mostrar la secuencia de QRs en pantalla")

    args = parser.parse_args()

    try:
        # Crear aplicación emisora
        sender = SenderApp()

        # Enviar archivo
        sender.send_file_with_qr_display(args.archivo, show_display=not args.no_display)

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
