#!/usr/bin/env python3
"""
QR-NET Microblog Demo
======================

Demuestra el uso de la aplicación anónima (`AnonymousApp`) para enviar y recibir
mensajes dentro de remote-QR-net.

Uso:
  python src/microblog_demo.py receive --host 0.0.0.0 --port 9000
  python src/microblog_demo.py send --host 0.0.0.0 --port 9001 --dest-node <node-id> --dest-host 127.0.0.1 --dest-port 9000 --message "Hola"

También permite enviar post a un tópico con `--topic` y `--public`.
"""

import argparse
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from layer2_3_network.node import QRNetNode
from layer7_anonymous.app import AnonymousApp


class MicroblogDemo:
    def __init__(self, host: str, port: int):
        self.node = QRNetNode(host, port)
        self.node.start()
        self.app = AnonymousApp(self.node)

    def run_receiver(self) -> None:
        print("\n[MicroblogDemo] Receptor iniciado")
        print(f"[MicroblogDemo] Node ID: {self.node.node_id}")
        print("[MicroblogDemo] Esperando mensajes... Ctrl+C para salir\n")

        def handler(msg):
            print("\n[MicroblogDemo] Mensaje recibido:")
            print(f"  Tipo: {msg.msg_type}")
            print(f"  Topic: {msg.topic}")
            print(f"  Contenido: {msg.content}")
            print(f"  Público: {msg.is_public}\n")

        self.app.on_message(handler)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[MicroblogDemo] Finalizando receptor...")
            self.node.stop()

    def run_sender(self, dest_node: str, dest_host: str, dest_port: int,
                   message: str, topic: str, public: bool) -> None:
        print("\n[MicroblogDemo] Emisor iniciado")
        print(f"[MicroblogDemo] Node ID: {self.node.node_id}")

        if dest_node and dest_host and dest_port:
            self.node.directory.register(dest_node, dest_host, dest_port)
            self.node.routing.update(dest_node, dest_node, 1)
            print(f"[MicroblogDemo] Nodo destino registrado: {dest_node} @ {dest_host}:{dest_port}")

        if topic:
            print(f"[MicroblogDemo] Enviando post al tópico '{topic}'")
            self.app.post(topic, message, public=public)
            print("[MicroblogDemo] Post enviado")
        else:
            if not dest_node:
                raise ValueError("Se requiere --dest-node para enviar un chat directo")
            print(f"[MicroblogDemo] Enviando chat privado a {dest_node}")
            self.app.send_chat(dest_node, message)
            print("[MicroblogDemo] Chat enviado")

        time.sleep(1)
        self.node.stop()


def main():
    parser = argparse.ArgumentParser(description="QR-NET Microblog Demo")
    subparsers = parser.add_subparsers(dest='mode', required=True)

    receiver_parser = subparsers.add_parser('receive', help='Iniciar receptor de microblog')
    receiver_parser.add_argument('--host', default='0.0.0.0', help='Host local (default 0.0.0.0)')
    receiver_parser.add_argument('--port', type=int, default=9000, help='Puerto UDP (default 9000)')

    sender_parser = subparsers.add_parser('send', help='Enviar mensaje de microblog/chat')
    sender_parser.add_argument('--host', default='0.0.0.0', help='Host local (default 0.0.0.0)')
    sender_parser.add_argument('--port', type=int, default=9001, help='Puerto UDP local (default 9001)')
    sender_parser.add_argument('--dest-node', help='ID del nodo destino')
    sender_parser.add_argument('--dest-host', default='127.0.0.1', help='IP destino para registro directo')
    sender_parser.add_argument('--dest-port', type=int, default=9000, help='Puerto destino para registro directo')
    sender_parser.add_argument('--message', required=True, help='Texto del mensaje')
    sender_parser.add_argument('--topic', help='Tópico para un post de microblog')
    sender_parser.add_argument('--public', action='store_true', help='Marcar post como público para clearnet')

    args = parser.parse_args()

    demo = MicroblogDemo(args.host, args.port)

    if args.mode == 'receive':
        demo.run_receiver()
    elif args.mode == 'send':
        demo.run_sender(
            dest_node=args.dest_node,
            dest_host=args.dest_host,
            dest_port=args.dest_port,
            message=args.message,
            topic=args.topic,
            public=args.public,
        )


if __name__ == '__main__':
    main()
