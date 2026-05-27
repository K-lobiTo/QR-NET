#!/usr/bin/env python3
"""
Ejemplo: Transferencia de Archivos QR-NET
==========================================

Este script demuestra cómo usar la API de transferencia de archivos QR-NET.
Usa broadcast QR para transmitir archivos sin necesidad de red.
"""

import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sender import SenderApp
from receiver import ReceiverApp


def example_sender():
    """
    Ejemplo: Emisor de archivo con visualización de QRs
    """
    print("\n" + "="*70)
    print("EJEMPLO: EMISOR DE ARCHIVO")
    print("="*70 + "\n")

    ruta_archivo = input("Ingresa ruta del archivo a enviar: ").strip()

    if not os.path.exists(ruta_archivo):
        print(f"✗ Archivo no encontrado: {ruta_archivo}")
        return

    try:
        print(f"\nEnviando {ruta_archivo}...\n")
        sender = SenderApp()
        sender.send_file_with_qr_display(ruta_archivo, show_display=True)
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sender.cleanup()


def example_receiver():
    """
    Ejemplo: Receptor de archivo con captura de cámara
    """
    print("\n" + "="*70)
    print("EJEMPLO: RECEPTOR DE ARCHIVO")
    print("="*70 + "\n")

    camera_index = input("Índice de cámara (default: 0): ").strip()
    camera_index = int(camera_index) if camera_index else 0

    try:
        print(f"\nEsperando archivos en cámara {camera_index}...\n")
        receiver = ReceiverApp(camera_index)
        receiver.start_camera_capture()
        receiver.wait_for_file(timeout=300)
        receiver.list_received_files()

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        receiver.cleanup()


def main():
    """
    Menú principal
    """
    print("\n" + "="*70)
    print("QR-NET FILE TRANSFER — EJEMPLOS DE USO")
    print("="*70)

    print("\nOpciones:")
    print("  1. Emisor (enviar archivo)")
    print("  2. Receptor (recibir archivo)")
    print("  3. Salir")

    choice = input("\nElige una opción (1-3): ").strip()

    if choice == "1":
        example_sender()

    elif choice == "2":
        example_receiver()

    elif choice == "3":
        print("Adiós\n")
    else:
        print("Opción inválida\n")



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelado por el usuario.\n")
    except Exception as e:
        print(f"\n✗ Error: {e}\n")
        import traceback
        traceback.print_exc()
