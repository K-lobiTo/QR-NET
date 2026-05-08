#!/usr/bin/env python3
"""
Ejemplo: Transferencia de Archivos QR-NET
==========================================

Este script demuestra cómo usar la API de transferencia de archivos.
"""

import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from layer2_3_network.node import QRNetNode
from layer7_anonymous.app import AnonymousApp
from layer7_file_transfer.file_transfer_app import FileTransferApp
import time


def example_sender(host: str = "192.168.1.100", port: int = 9000):
    """
    Ejemplo: Emisor de archivo
    """
    print("\n" + "="*70)
    print("EJEMPLO: EMISOR DE ARCHIVO")
    print("="*70 + "\n")

    # 1. Inicializar nodo
    node = QRNetNode(host, port)
    node.start()
    print(f"✓ Nodo iniciado: {node.node_id[:16]}...")

    # 2. Crear aplicación anónima
    anon_app = AnonymousApp(node)
    print("✓ Aplicación anónima lista")

    # 3. Crear aplicación de transferencia de archivos
    file_app = FileTransferApp(anon_app)
    print("✓ Aplicación de transferencia lista\n")

    # 4. Enviar archivo
    nodo_destino = input("Ingresa ID del nodo receptor: ").strip()
    ruta_archivo = input("Ingresa ruta del archivo a enviar: ").strip()

    if not os.path.exists(ruta_archivo):
        print(f"✗ Archivo no encontrado: {ruta_archivo}")
        node.stop()
        return

    try:
        print(f"\nEnviando {ruta_archivo} a {nodo_destino}...\n")
        transfer_id = file_app.send_file(nodo_destino, ruta_archivo)
        print(f"\n✓ Transferencia completada (ID: {transfer_id})")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        node.stop()


def example_receiver(host: str = "192.168.1.101", port: int = 9000):
    """
    Ejemplo: Receptor de archivo
    """
    print("\n" + "="*70)
    print("EJEMPLO: RECEPTOR DE ARCHIVO")
    print("="*70 + "\n")

    # 1. Inicializar nodo
    node = QRNetNode(host, port)
    node.start()
    print(f"✓ Nodo iniciado: {node.node_id[:16]}...")
    print(f"  Comparte este ID con el emisor: {node.node_id}\n")

    # 2. Crear aplicación anónima
    anon_app = AnonymousApp(node)
    print("✓ Aplicación anónima lista")

    # 3. Crear aplicación de transferencia de archivos
    file_app = FileTransferApp(anon_app)
    print("✓ Aplicación de transferencia lista")

    # 4. Esperar a recibir un archivo
    print(f"\nEsperando archivos (timeout: 300s)...\n")

    try:
        # Esperar por 5 minutos máximo
        timeout = 300
        start_time = time.time()

        while time.time() - start_time < timeout:
            files = file_app.receive_files()

            for f in files:
                if f.get("status") == "completed":
                    output = f.get("output_path")
                    print(f"\n✓ Archivo completado: {output}")
                elif f.get("status") == "failed":
                    print(f"\n✗ Error en transferencia: {f.get('filename')}")
                else:
                    progress = f.get("received_chunks", 0)
                    total = f.get("total_chunks", 0)
                    if total > 0:
                        percent = (progress / total) * 100
                        print(f"  Recibiendo: {f.get('filename')} - {progress}/{total} ({percent:.0f}%)")

            time.sleep(1)

        if not files:
            print("✗ No se recibieron archivos")

    except KeyboardInterrupt:
        print("\n\nCancelado por el usuario")
    finally:
        node.stop()


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
        host = input("Host local (default: 192.168.1.100): ").strip() or "192.168.1.100"
        port = input("Puerto (default: 9000): ").strip()
        port = int(port) if port else 9000
        example_sender(host, port)

    elif choice == "2":
        host = input("Host local (default: 192.168.1.101): ").strip() or "192.168.1.101"
        port = input("Puerto (default: 9000): ").strip()
        port = int(port) if port else 9000
        example_receiver(host, port)

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
