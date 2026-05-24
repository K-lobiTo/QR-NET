import argparse
import base64
import json
import os
import subprocess

from datetime import datetime
from receiver import ReceiverApp

PK_ID = 1

def make_post(content):
    global PK_ID
    post = {
        "id": PK_ID,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "content": content
    }
    PK_ID += 1
    with open("microblog_posts.txt", "a", encoding="utf-8") as f:
        f.write(json.dumps(post, ensure_ascii=False) + "\n")

def camera_capture(receiver):
    """Loop de captura de QRs desde la cámara."""
    try:
        receiver.luz_device.open_camera()
        receiver.camera_running = True
        print("[Luz-L1] Cámara abierta, buscando QRs...\n")
        while receiver.camera_running:
            try:
                # Intentar decodificar un QR
                frame_data = receiver.luz_device.receive()
                if frame_data is not None:
                    payload = frame_data.get("payload")
                    if payload:
                        receiver.camera_running = False
                        return payload
            except Exception as e:
                print(f"[Luz-L1] Error capturando: {e}")
    except Exception as e:
        print(f"[Luz-L1] Error crítico en captura: {e}")
    finally:
        receiver.luz_device.close_camera()
        receiver.camera_running = False
    return None

def extract_content(payload: bytes):
    try:
        fragment = json.loads(payload.decode())
        encoded_data = fragment["data"]
        content = base64.b64decode(encoded_data).decode('utf-8')
        return content
    except Exception as e:
        print(f"[Receptor] Error procesando fragmento: {e}")

def camera_capture_loop(receiver):
    """Loop de captura de QRs desde la cámara."""
    post_content = ""
    try:
        receiver.luz_device.open_camera()
        print("[Luz-L1] Cámara abierta, buscando QRs...\n")
        while len(post_content) < 15:
            try:
                # Intentar decodificar un QR
                frame_data = receiver.luz_device.receive()
                if frame_data is not None:
                    payload = frame_data.get("payload")
                    if payload:
                        content = extract_content(payload)
                        if content is not None:
                            post_content = post_content + content
            except Exception as e:
                print(f"[Luz-L1] Error capturando: {e}")
    except Exception as e:
        print(f"[Luz-L1] Error crítico en captura: {e}")
    finally:
        receiver.luz_device.close_camera()
        receiver.camera_running = False
    return post_content[:256]

def analyze_payload(receiver: ReceiverApp, payload: bytes):
    """Procesa un fragmento recibido desde la cámara."""
    try:
        # ----------------------------------------------------------
        # Payload JSON -> dict
        # ----------------------------------------------------------
        fragment = json.loads(payload.decode())
        transfer_id = fragment["transfer_id"]
        chunk_number = fragment["chunk_number"]
        total_chunks = fragment["total_chunks"]
        encoded_data = fragment["data"]
        # ----------------------------------------------------------
        # Base64 -> bytes reales
        # ----------------------------------------------------------
        chunk_data = base64.b64decode(encoded_data).decode('utf-8')
        print(f"Caracteres: {len(chunk_data)}")
        server_command = chunk_data.splitlines()[0]
        if server_command == "[POST]":
            global POSTS
            post_content = camera_capture_loop(receiver)
            make_post(post_content)
        if server_command == "[GET]":
            subprocess.run([
                "python3",
                "src/sender.py",
                "microblog_posts.txt",
                "0"
            ])


    except Exception as e:
        print(f"[Receptor] Error procesando fragmento: {e}")

# def build_post(text):

# def running_server():

def start_server(receiver: ReceiverApp):
    while True:
        qr_payload = camera_capture(receiver)
        if qr_payload is not None:
            analyze_payload(receiver, qr_payload)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--host", default="0.0.0.0", help="Host local (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9000, help="Puerto UDP (default: 9000)")
    parser.add_argument("--camera", type=int, default=0, help="Índice de cámara (default: 0)")

    args = parser.parse_args()
    try:
        # Crear aplicación receptora
        receiver = ReceiverApp(args.host, args.port, args.camera)
        # Iniciar captura de cámara
        start_server(receiver)
    except KeyboardInterrupt:
        print("\n\n[Servidor] Cancelado por el usuario.")

if __name__ == '__main__':
    main()