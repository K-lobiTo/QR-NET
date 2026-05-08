"""
Capa 7 — Aplicación Pública (Clearnet)
=======================================
Servidor IRC + bot que hace de puente entre clearnet y remote-QR-net.
Solo los mensajes marcados como públicos (is_public=True) en remote-QR-net
son replicados en IRC y NNTP.
"""

import irc.bot
import irc.strings
import threading
import time
from typing import Optional

# nntplib was removed in Python 3.13, try to import from stdlib
try:
    import nntplib
except ImportError:
    nntplib = None  # Will be handled gracefully in NNTPPublisher


# ---------------------------------------------------------------------------
# Bot IRC
# ---------------------------------------------------------------------------

class QRNetIRCBot(irc.bot.SingleServerIRCBot):
    """
    Bot IRC que actúa como puerta de entrada de remote-QR-net a clearnet.

    - Mensajes públicos de QR-NET → canal IRC.
    - Mensajes del canal IRC → remote-QR-net (si el comando es correcto).
    """

    def __init__(self, server: str, port: int, channel: str,
                 nickname: str, anonymous_app):
        """
        Args:
            server:        Servidor IRC (ej. "irc.libera.chat").
            port:          Puerto IRC (ej. 6667).
            channel:       Canal a unirse (ej. "#qrnet").
            nickname:      Nick del bot.
            anonymous_app: Instancia de AnonymousApp.
        """
        super().__init__([(server, port)], nickname, nickname)
        self.channel  = channel
        self.anon_app = anonymous_app
        print(f"[L7-IRC] Bot configurado → {server}:{port} {channel}")

    # ------------------------------------------------------------------
    # Eventos IRC
    # ------------------------------------------------------------------

    def on_welcome(self, conn, event):
        conn.join(self.channel)
        print(f"[L7-IRC] Conectado y unido a {self.channel}")

    def on_pubmsg(self, conn, event):
        """Mensajes en el canal público → reenviar a QR-NET si se solicita."""
        msg = event.arguments[0]
        if msg.startswith("!qrnet "):
            content = msg[len("!qrnet "):]
            self.anon_app.post("clearnet", content, public=False)

    def broadcast_to_irc(self, message: str) -> None:
        """Envía un mensaje al canal IRC."""
        try:
            self.connection.privmsg(self.channel, message)
        except Exception as e:
            print(f"[L7-IRC] Error enviando a IRC: {e}")

    def on_public_qrnet_message(self, topic: str, content: str) -> None:
        """Callback cuando llega un mensaje público desde QR-NET."""
        self.broadcast_to_irc(f"[QR-NET:{topic}] {content}")
        NNTPPublisher.publish(topic, content)


# ---------------------------------------------------------------------------
# Publicador NNTP
# ---------------------------------------------------------------------------

class NNTPPublisher:
    """
    Publica nuevas entradas de tópicos en un servidor NNTP.
    """

    server:  str = "localhost"
    port:    int = 119
    group:   str = "local.qrnet"

    @classmethod
    def configure(cls, server: str, port: int = 119,
                  group: str = "local.qrnet") -> None:
        cls.server = server
        cls.port   = port
        cls.group  = group

    @classmethod
    def publish(cls, topic: str, content: str) -> None:
        """
        Publica un artículo NNTP con el contenido del tópico.
        Cada nueva entrada de tópico en QR-NET genera un artículo.
        """
        if nntplib is None:
            print(f"[L7-NNTP] NNTP no disponible (Python 3.13+ requiere backport). Omitiendo publicación.")
            return
        
        try:
            article = (
                f"From: qrnet-bot@anonymous.net\r\n"
                f"Newsgroups: {cls.group}\r\n"
                f"Subject: [QR-NET] {topic}\r\n"
                f"Content-Type: text/plain; charset=utf-8\r\n"
                f"\r\n"
                f"{content}\r\n"
            )
            with nntplib.NNTP(cls.server, cls.port) as conn:
                conn.post(article.encode())
            print(f"[L7-NNTP] Artículo publicado en {cls.group}: {topic}")
        except Exception as e:
            print(f"[L7-NNTP] Error publicando en NNTP: {e}")


# ---------------------------------------------------------------------------
# Orquestador Clearnet
# ---------------------------------------------------------------------------

class ClearnetBridge:
    """
    Coordina el bot IRC y el publicador NNTP.
    Escucha mensajes públicos de AnonymousApp y los retransmite.
    """

    def __init__(self, irc_server: str, irc_port: int,
                 irc_channel: str, irc_nick: str,
                 nntp_server: str, anonymous_app):
        self.bot = QRNetIRCBot(irc_server, irc_port, irc_channel,
                               irc_nick, anonymous_app)
        NNTPPublisher.configure(nntp_server)

        # Escuchar mensajes públicos de la app anónima
        anonymous_app.on_message(self._on_anon_message)

    def _on_anon_message(self, msg) -> None:
        if msg.is_public:
            self.bot.on_public_qrnet_message(msg.topic, msg.content)

    def start(self) -> None:
        """Inicia el bot IRC en un hilo separado."""
        t = threading.Thread(target=self.bot.start, daemon=True)
        t.start()
        print("[L7-Clearnet] Bridge IRC/NNTP iniciado.")
