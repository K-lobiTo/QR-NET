"""
QR-NET — Punto de entrada principal
=====================================
Orquesta todas las capas del sistema.
"""

import argparse
import time

from layer2_3_network.node import QRNetNode
from layer7_anonymous.app import AnonymousApp
from layer7_clearnet.clearnet import ClearnetBridge


def main():
    parser = argparse.ArgumentParser(description="QR-NET Node")
    parser.add_argument("--host",        default="0.0.0.0",       help="Host a escuchar")
    parser.add_argument("--port",        type=int, default=9000,   help="Puerto UDP")
    parser.add_argument("--irc-server",  default="irc.libera.chat")
    parser.add_argument("--irc-port",    type=int, default=6667)
    parser.add_argument("--irc-channel", default="#qrnet")
    parser.add_argument("--irc-nick",    default="qrnet-bot")
    parser.add_argument("--nntp-server", default="localhost")
    parser.add_argument("--no-clearnet", action="store_true",
                        help="Deshabilitar bridge IRC/NNTP")
    args = parser.parse_args()

    # Capa 2/3
    node = QRNetNode(args.host, args.port)
    node.start()

    # Capa 7 anónima
    anon_app = AnonymousApp(node)

    # Capa 7 clearnet (opcional)
    if not args.no_clearnet:
        bridge = ClearnetBridge(
            irc_server   = args.irc_server,
            irc_port     = args.irc_port,
            irc_channel  = args.irc_channel,
            irc_nick     = args.irc_nick,
            nntp_server  = args.nntp_server,
            anonymous_app= anon_app,
        )
        bridge.start()

    print("\n[QR-NET] Sistema iniciado. Ctrl+C para salir.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[QR-NET] Apagando...")
        node.stop()


if __name__ == "__main__":
    main()
