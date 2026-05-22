"""
Capa 7 — Aplicación Anónima sobre remote-QR-net
=================================================
Microblogging y chat que reside únicamente dentro de remote-QR-net.
Los mensajes NUNCA salen a clearnet desde este módulo.
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable

# ---------------------------------------------------------------------------
# Tipos de mensajes de aplicación
# ---------------------------------------------------------------------------
MSG_CHAT    = "CHAT"
MSG_POST    = "POST"      # Entrada de microblog
MSG_TOPIC   = "TOPIC"     # Publicación en un tópico


@dataclass
class AppMessage:
    """
    Mensaje de aplicación que viaja sobre remote-QR-net.

    Los campos de longitud dinámica (content, topic) tienen su tamaño
    declarado en content_len y topic_len respectivamente.
    """
    version:     int    = 1
    msg_type:    str    = MSG_CHAT
    message_id:  str    = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:   float  = field(default_factory=time.time)
    topic:       str    = ""
    topic_len:   int    = 0
    content:     str    = ""
    content_len: int    = 0
    is_public:   bool   = False   # Si True, el bot IRC puede publicarlo en clearnet

    def to_json(self) -> str:
        d = asdict(self)
        d["topic_len"]   = len(self.topic.encode())
        d["content_len"] = len(self.content.encode())
        return json.dumps(d)

    @staticmethod
    def from_json(raw: str) -> "AppMessage":
        return AppMessage(**json.loads(raw))


# ---------------------------------------------------------------------------
# Cliente de chat / microblog
# ---------------------------------------------------------------------------

class AnonymousApp:
    """
    Aplicación de microblogging y chat anónimo.

    Depende de un QRNetNode (Capa 2/3) para el transporte.
    """

    def __init__(self, network_node):
        """
        Args:
            network_node: Instancia de QRNetNode ya iniciado.
        """
        self.node = network_node
        self._handlers: list[Callable[[AppMessage], None]] = []
        self._posts: list[AppMessage] = []
        self.node.on_data(self.receive)
        print("[L7-Anon] Aplicación anónima lista.")

    def on_message(self, handler: Callable[[AppMessage], None]) -> None:
        """Registra un callback para mensajes entrantes."""
        self._handlers.append(handler)

    def send_chat(self, dst_node: str, content: str) -> None:
        """Envía un mensaje de chat privado."""
        msg = AppMessage(
            msg_type   = MSG_CHAT,
            content    = content,
            is_public  = False,
        )
        self.node.send_data(dst_node, msg.to_json())

    def post(self, topic: str, content: str, public: bool = False) -> None:
        """
        Publica una entrada de microblog en un tópico.

        Args:
            topic:   Tópico de la publicación.
            content: Contenido del mensaje.
            public:  Si True, el bot IRC podrá replicarlo en clearnet.
        """
        msg = AppMessage(
            msg_type  = MSG_POST,
            topic     = topic,
            content   = content,
            is_public = public,
        )
        self._posts.append(msg)
        # Broadcast a toda la red (dst vacío indica broadcast de aplicación)
        self.node.send_data("", msg.to_json())
        print(f"[L7-Anon] Post publicado en tópico '{topic}' (público={public})")

    def receive(self, raw_payload: str) -> None:
        """Procesa un payload crudo recibido desde la capa de red."""
        try:
            msg = AppMessage.from_json(raw_payload)
            if msg.msg_type == MSG_POST:
                # Evitar duplicados por message_id
                if not any(p.message_id == msg.message_id for p in self._posts):
                    self._posts.append(msg)
            for handler in self._handlers:
                handler(msg)
        except Exception as e:
            print(f"[L7-Anon] Error procesando mensaje: {e}")

    def get_posts(self, topic: Optional[str] = None) -> list[AppMessage]:
        """Retorna publicaciones, opcionalmente filtradas por tópico."""
        if topic:
            return [p for p in self._posts if p.topic == topic]
        return list(self._posts)
