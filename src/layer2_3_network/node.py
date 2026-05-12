"""
remote-QR-net — Capas 2 y 3
============================
Red mesh anónima que opera sobre cualquier interfaz TCP/IP.

Responsabilidades:
- Enrutamiento dinámico entre nodos (mesh).
- Anonimato del originador (onion-style o mixnet simplificado).
- Directorio de nodos (node discovery).
- Circuitos virtuales negociados.
- Soporte de múltiples canales físicos: Ethernet, WiFi, Dispositivo de Transmisión, Video.
"""

import socket
import threading
import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
PROTOCOL_VERSION  = 1
DEFAULT_PORT      = 9000
DIRECTORY_PORT    = 9001
BROADCAST_ADDR    = "255.255.255.255"

MSG_TYPE_HELLO    = "HELLO"
MSG_TYPE_ROUTE    = "ROUTE"
MSG_TYPE_DATA     = "DATA"
MSG_TYPE_ACK      = "ACK"
MSG_TYPE_CIRCUIT  = "CIRCUIT"


# ---------------------------------------------------------------------------
# Estructuras de paquetes (JSON sobre TCP/UDP)
# ---------------------------------------------------------------------------

@dataclass
class QRNetPacket:
    """
    Paquete de red de remote-QR-net.

    Campos de longitud dinámica (payload, path) declarados con su tamaño
    en campos separados: payload_len, path_len.
    """
    version:     int    = PROTOCOL_VERSION
    msg_type:    str    = MSG_TYPE_DATA
    packet_id:   str    = field(default_factory=lambda: str(uuid.uuid4()))
    src_node:    str    = ""          # ID anónimo del nodo origen
    dst_node:    str    = ""          # ID del nodo destino
    circuit_id:  str    = ""          # Circuito virtual negociado
    hop_count:   int    = 0
    ttl:         int    = 16
    # Campos dinámicos
    path_len:    int    = 0           # Número de nodos en el path
    path:        list   = field(default_factory=list)
    payload_len: int    = 0           # Longitud del payload en bytes
    payload:     str    = ""

    def to_json(self) -> str:
        d = asdict(self)
        d["payload_len"] = len(self.payload.encode())
        d["path_len"]    = len(self.path)
        return json.dumps(d)

    @staticmethod
    def from_json(raw: str) -> "QRNetPacket":
        d = json.loads(raw)
        return QRNetPacket(**d)


# ---------------------------------------------------------------------------
# Directorio de Nodos
# ---------------------------------------------------------------------------

class NodeDirectory:
    """
    Servicio de descubrimiento de nodos en remote-QR-net.
    Mantiene una tabla de nodos conocidos con su última actividad.
    """

    def __init__(self):
        self._nodes: dict[str, dict] = {}  # node_id -> {addr, port, last_seen}
        self._lock = threading.Lock()

    def register(self, node_id: str, addr: str, port: int) -> None:
        with self._lock:
            self._nodes[node_id] = {
                "addr": addr,
                "port": port,
                "last_seen": time.time(),
            }

    def get(self, node_id: str) -> Optional[dict]:
        with self._lock:
            return self._nodes.get(node_id)

    def all_nodes(self) -> list[dict]:
        with self._lock:
            return [
                {"node_id": nid, **info}
                for nid, info in self._nodes.items()
                if time.time() - info["last_seen"] < 300  # activos últimos 5 min
            ]

    def remove_stale(self, timeout: int = 300) -> None:
        with self._lock:
            stale = [nid for nid, info in self._nodes.items()
                     if time.time() - info["last_seen"] > timeout]
            for nid in stale:
                del self._nodes[nid]


# ---------------------------------------------------------------------------
# Tabla de Enrutamiento
# ---------------------------------------------------------------------------

@dataclass
class RouteEntry:
    dst_node:    str
    next_hop:    str
    distance:    int
    last_update: float = field(default_factory=time.time)


class RoutingTable:
    """
    Tabla de enrutamiento dinámico para la red mesh.
    Implementa Distance Vector simplificado.
    """

    def __init__(self, local_node_id: str):
        self.local = local_node_id
        self._routes: dict[str, RouteEntry] = {}
        self._lock = threading.Lock()

    def update(self, dst: str, next_hop: str, distance: int) -> bool:
        """Actualiza ruta si mejora la distancia. Retorna True si hubo cambio."""
        with self._lock:
            existing = self._routes.get(dst)
            if existing is None or distance < existing.distance:
                self._routes[dst] = RouteEntry(dst, next_hop, distance)
                return True
        return False

    def get_next_hop(self, dst: str) -> Optional[str]:
        with self._lock:
            entry = self._routes.get(dst)
            return entry.next_hop if entry else None

    def dump(self) -> list[dict]:
        with self._lock:
            return [asdict(e) for e in self._routes.values()]


# ---------------------------------------------------------------------------
# Nodo principal
# ---------------------------------------------------------------------------

class QRNetNode:
    """
    Nodo de remote-QR-net.

    Implementa:
    - Descubrimiento de vecinos (HELLO).
    - Enrutamiento dinámico (ROUTE).
    - Forwarding de paquetes con TTL.
    - Anonimato: el node_id es un hash efímero, no vinculado a la IP real.
    - Circuitos virtuales (CIRCUIT).
    """

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT):
        self.node_id      = self._generate_anonymous_id()
        self.host         = host
        self.port         = port
        self.directory    = NodeDirectory()
        self.routing      = RoutingTable(self.node_id)
        self._circuits: dict[str, dict] = {}   # circuit_id -> {src, dst, hops}
        self._data_handler: Optional[Callable[[str], None]] = None
        self._running     = False
        self._sock: Optional[socket.socket] = None
        print(f"[L2/3] Nodo iniciado. ID anónimo: {self.node_id[:16]}...")

    # ------------------------------------------------------------------
    # Anonimato
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_anonymous_id() -> str:
        """
        Genera un ID de nodo anónimo: hash de UUID aleatorio.
        No está vinculado a ningún identificador real del equipo.
        """
        salt = uuid.uuid4().bytes
        return hashlib.sha256(salt).hexdigest()

    # ------------------------------------------------------------------
    # Ciclo de red
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        print(f"[L2/3] Escuchando en {self.host}:{self.port}")

        threading.Thread(target=self._recv_loop, daemon=True).start()
        threading.Thread(target=self._hello_loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False
        if self._sock:
            self._sock.close()

    def _recv_loop(self) -> None:
        while self._running:
            try:
                data, addr = self._sock.recvfrom(4096)
                packet = QRNetPacket.from_json(data.decode())
                self._handle_packet(packet, addr)
            except Exception as e:
                if self._running:
                    print(f"[L2/3] Error en recv_loop: {e}")

    def _hello_loop(self) -> None:
        """Envía HELLO periódicamente para anunciar presencia."""
        while self._running:
            self._broadcast_hello()
            time.sleep(30)

    # ------------------------------------------------------------------
    # Manejo de paquetes
    # ------------------------------------------------------------------

    def _handle_packet(self, packet: QRNetPacket, addr: tuple) -> None:
        if packet.version != PROTOCOL_VERSION:
            print(f"[L2/3] Versión desconocida: {packet.version}, descartando.")
            return

        if packet.msg_type == MSG_TYPE_HELLO:
            self._handle_hello(packet, addr)
        elif packet.msg_type == MSG_TYPE_ROUTE:
            self._handle_route(packet)
        elif packet.msg_type == MSG_TYPE_DATA:
            self._handle_data(packet)
        elif packet.msg_type == MSG_TYPE_CIRCUIT:
            self._handle_circuit(packet)

    def _handle_hello(self, packet: QRNetPacket, addr: tuple) -> None:
        src = packet.src_node
        self.directory.register(src, addr[0], addr[1])
        self.routing.update(src, src, 1)
        print(f"[L2/3] HELLO de {src[:8]}... @ {addr[0]}")

    def _handle_route(self, packet: QRNetPacket) -> None:
        """Actualiza tabla de enrutamiento con la información recibida."""
        routes = json.loads(packet.payload)
        for route in routes:
            self.routing.update(
                route["dst_node"],
                packet.src_node,
                route["distance"] + 1,
            )

    def _handle_data(self, packet: QRNetPacket) -> None:
        if packet.dst_node == self.node_id:
            if self._data_handler:
                self._data_handler(packet.payload)
            else:
                print(f"[L2/3] Paquete para mí: {packet.payload}")
            return

        if packet.ttl <= 0:
            return  # Descartar paquete expirado

        packet.ttl -= 1
        packet.hop_count += 1
        self._forward(packet)

    def _handle_circuit(self, packet: QRNetPacket) -> None:
        """Establece o acepta un circuito virtual."""
        cid = packet.circuit_id
        if cid not in self._circuits:
            self._circuits[cid] = {
                "src": packet.src_node,
                "dst": packet.dst_node,
                "established": time.time(),
            }
            print(f"[L2/3] Circuito {cid[:8]}... establecido.")

    # ------------------------------------------------------------------
    # Forwarding y envío
    # ------------------------------------------------------------------

    def _forward(self, packet: QRNetPacket) -> None:
        next_hop = self.routing.get_next_hop(packet.dst_node)
        if next_hop is None:
            print(f"[L2/3] Sin ruta para {packet.dst_node[:8]}...")
            return
        node_info = self.directory.get(next_hop)
        if node_info:
            self._send_raw(packet, node_info["addr"], node_info["port"])

    def on_data(self, handler: Callable[[str], None]) -> None:
        """Registra un callback para payloads recibidos destinados a este nodo."""
        self._data_handler = handler

    def send_data(self, dst_node: str, payload: str) -> None:
        """Envía datos a un nodo destino a través de la mesh."""
        packet = QRNetPacket(
            msg_type   = MSG_TYPE_DATA,
            src_node   = self.node_id,
            dst_node   = dst_node,
            payload    = payload,
        )
        if dst_node == "":
            # Broadcast a todos los nodos conocidos
            for node_info in self.directory.all_nodes():
                self._send_raw(packet, node_info["addr"], node_info["port"])
            return
        self._forward(packet)

    def _broadcast_hello(self) -> None:
        packet = QRNetPacket(
            msg_type = MSG_TYPE_HELLO,
            src_node = self.node_id,
        )
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet.to_json().encode(), (BROADCAST_ADDR, self.port))
            sock.close()
        except Exception as e:
            print(f"[L2/3] Error en broadcast: {e}")

    def _send_raw(self, packet: QRNetPacket, addr: str, port: int) -> None:
        try:
            self._sock.sendto(packet.to_json().encode(), (addr, port))
        except Exception as e:
            print(f"[L2/3] Error enviando a {addr}:{port} — {e}")
