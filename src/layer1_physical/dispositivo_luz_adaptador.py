"""
DispositivoLuzAdaptador
=======================
Biblioteca de Capa 1 (Medio Físico) del protocolo QR-NET.

Responsabilidades:
- Codificar tramas en códigos QR para transmisión por luz.
- Decodificar códigos QR capturados por cámara.
- Verificación de checksum (CRC-16).
- Control de acceso al medio (CSMA-like).
- Manejo de versiones del protocolo.
- Dirección física (análogo a MAC Address).

Restricciones de trama:
  - Tamaño máximo: 128 bytes
  - Campos de longitud dinámica declarados explícitamente
"""
import base64
import json
import os
import struct
import hashlib
import time
import uuid

import numpy as np
import qrcode
import cv2

from tools import extract_chunk_number


try:
    from pyzbar import pyzbar
except Exception:
    pyzbar = None
from PIL import Image

CAMERA_URL = "http://10.100.43.106:8080/video"

# ---------------------------------------------------------------------------
# Constantes del protocolo
# ---------------------------------------------------------------------------
PROTOCOL_VERSION  = 1          # Versión actual del protocolo
MAX_FRAME_SIZE    = 256        # Bytes máximos por trama
PREAMBLE          = 0xAB       # Byte de inicio de trama
FRAME_TYPE_DATA   = 0x01
FRAME_TYPE_ACK    = 0x02
FRAME_TYPE_HELLO  = 0x03
BROADCAST_MAC     = b"\xff\xff\xff\xff\xff\xff"


# ---------------------------------------------------------------------------
# Trama de Capa 1
#
# Formato (bytes):
#  0        : PREAMBLE          (1 byte)
#  1        : VERSION           (1 byte)
#  2        : FRAME_TYPE        (1 byte)
#  3-8      : SRC_MAC           (6 bytes)
#  9-14     : DST_MAC           (6 bytes)
#  15       : PAYLOAD_LEN       (1 byte)  ← longitud dinámica
#  16..N    : PAYLOAD           (0-105 bytes)
#  N+1..N+2 : CHECKSUM CRC-16   (2 bytes)
# ---------------------------------------------------------------------------

HEADER_SIZE   = 18   # bytes fijos antes del payload
CHECKSUM_SIZE = 2
MAX_PAYLOAD   = MAX_FRAME_SIZE - HEADER_SIZE - CHECKSUM_SIZE  # 236 bytes


def generate_mac() -> bytes:
    """Genera una dirección física única de 6 bytes (análogo a MAC)."""
    node = uuid.getnode()
    return node.to_bytes(6, byteorder='big')


def crc16(data: bytes) -> int:
    """Calcula CRC-16/CCITT-FALSE."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def build_frame(src_mac: bytes, dst_mac: bytes,
                payload: bytes, frame_type: int = FRAME_TYPE_DATA) -> bytes:
    """
    Construye una trama de Capa 1.

    Args:
        src_mac:    Dirección física origen (6 bytes).
        dst_mac:    Dirección física destino (6 bytes).
        payload:    Datos a transmitir (máx MAX_PAYLOAD bytes).
        frame_type: Tipo de trama.

    Returns:
        Trama completa como bytes.

    Raises:
        ValueError: Si el payload excede el tamaño máximo.
    """
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"Payload excede {MAX_PAYLOAD} bytes ({len(payload)} recibidos)")

    header = struct.pack(
        "!BBBBB",           # network byte order
        PREAMBLE,
        PROTOCOL_VERSION,
        frame_type,
        len(src_mac),       # siempre 6, pero explícito por diseño extensible
        len(dst_mac),
    )
    header += src_mac + dst_mac
    header += struct.pack("!B", len(payload))
    frame_no_crc = header + payload
    checksum = crc16(frame_no_crc)
    return frame_no_crc + struct.pack("!H", checksum)


def parse_frame(raw: bytes) -> dict | None:
    """
    Parsea una trama cruda.

    Returns:
        Diccionario con los campos de la trama, o None si es inválida.
    """
    if len(raw) < HEADER_SIZE + CHECKSUM_SIZE:
        return None

    if raw[0] != PREAMBLE:
        return None

    checksum_recv = struct.unpack("!H", raw[-2:])[0]
    if crc16(raw[:-2]) != checksum_recv:
        return None   # Checksum inválido

    version    = raw[1]
    frame_type = raw[2]
    src_mac    = raw[5:11]
    dst_mac    = raw[11:17]
    payload_len = raw[17]
    payload    = raw[18:18 + payload_len]

    return {
        "version":    version,
        "frame_type": frame_type,
        "src_mac":    src_mac.hex(":"),
        "dst_mac":    dst_mac.hex(":"),
        "payload_len": payload_len,
        "payload":    payload,
    }


def _decode_qr_frame_to_objs(frame):
    """Decode QR codes from an OpenCV frame. Returns list of objects with .data bytes attribute."""
    if pyzbar:
        try:
            return pyzbar.decode(frame)
        except Exception:
            pass
    detector = cv2.QRCodeDetector()
    decoded_objs = []
    try:
        # detectAndDecodeMulti may return (retval, decoded_info, points, straight_qrcode)
        result = detector.detectAndDecodeMulti(frame)
        if result and len(result) >= 2:
            retval = result[0]
            decoded_info = result[1]
            if retval and decoded_info:
                for s in decoded_info:
                    if not s:
                        continue
                    obj = type("DecodedObj", (), {})()
                    obj.data = s
                    decoded_objs.append(obj)
                return decoded_objs
    except Exception:
        pass
    try:
        # Fallback to single decode
        s_and_points = detector.detectAndDecode(frame)
        if isinstance(s_and_points, tuple):
            s = s_and_points[0]
        else:
            s = s_and_points
        if s:
            obj = type("DecodedObj", (), {})()
            obj.data = s.encode("latin-1")
            decoded_objs.append(obj)
    except Exception:
        pass
    return decoded_objs


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class DispositivoLuzAdaptador:
    """
    Adaptador de red que usa luz (códigos QR) como medio físico.

    Uso básico:
        adaptador = DispositivoLuzAdaptador()
        adaptador.send(dst_mac, b"hola mundo")
        frame = adaptador.receive()
    """

    def __init__(self, camera_index: int = 0):
        self.mac      = generate_mac()
        self.camera   = None
        self.cam_idx  = camera_index
        print(f"[L1] Dispositivo iniciado. MAC: {self.mac.hex(':')}")

    # ------------------------------------------------------------------
    # Transmisión
    # ------------------------------------------------------------------

    def send(self, dst_mac: bytes, payload: bytes,
             frame_type: int = FRAME_TYPE_DATA) -> None:
        """Codifica el payload en un QR y lo muestra en pantalla."""
        frame = build_frame(self.mac, dst_mac, payload, frame_type)
        chunk_number = extract_chunk_number(parse_frame(frame))
        self._save_qr(frame, chunk_number)

    def _save_qr(self, data: bytes, chunk) -> None:
        """Genera y guarda un código QR con los bytes de la trama."""
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        encoded = base64.b64encode(data).decode("ascii")
        qr.add_data(encoded)
        qr.make(fit=True)
        # Imagen PIL
        img = qr.make_image(fill_color="black", back_color="white")
        filename = f"temp-qr/qr-{chunk:010d}.png"
        img.save(filename)
        # img.show()
        # Convertir PIL -> numpy array
        # img_np = np.array(img.convert("RGB"))
        # RGB -> BGR para OpenCV
        # img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        # cv2.imshow("QR-NET Transmisión", img_cv)
        # cv2.waitKey(500)  # Mostrar 500 ms

    # ------------------------------------------------------------------
    # Recepción
    # ------------------------------------------------------------------

    def open_camera(self) -> None:
        """Abre el dispositivo de cámara."""
        self.camera = cv2.VideoCapture(CAMERA_URL)
        if not self.camera.isOpened():
            raise RuntimeError(f"No se pudo abrir la cámara (índice {self.cam_idx})")
        print(f"[L1] Cámara {self.cam_idx} abierta.")

    def close_camera(self) -> None:
        if self.camera:
            self.camera.release()

    def receive(self) -> dict | None:
        """
        Captura un frame de la cámara, intenta decodificar un QR.

        Returns:
            Diccionario con la trama parseada, o None si no se detectó nada válido.
        """
        if not self.camera:
            self.open_camera()

        ret, frame = self.camera.read()
        if not ret:
            return None

        decoded = _decode_qr_frame_to_objs(frame)
        for obj in decoded:
            raw = base64.b64decode(obj.data)
            parsed = parse_frame(raw)
            if parsed:
                # Filtrar tramas no destinadas a este nodo
                if parsed["dst_mac"] != self.mac.hex(":") \
                   and parsed["dst_mac"] != BROADCAST_MAC.hex(":"):
                    continue
                return parsed
        return None

    # ------------------------------------------------------------------
    # Acceso al medio (CSMA simplificado)
    # ------------------------------------------------------------------

    def medium_is_free(self) -> bool:
        """
        Verifica si el medio está libre (no se detecta QR activo).
        Implementación básica: intenta leer y si no hay QR → libre.
        """
        if not self.camera:
            self.open_camera()
        ret, frame = self.camera.read()
        if not ret:
            return True
        decoded = _decode_qr_frame_to_objs(frame)
        return len(decoded) == 0

    def wait_and_send(self, dst_mac: bytes, payload: bytes,
                      max_retries: int = 5) -> bool:
        """
        Espera a que el medio esté libre antes de transmitir (CSMA).

        Returns:
            True si logró enviar, False si superó los reintentos.
        """
        for attempt in range(max_retries):
            if self.medium_is_free():
                self.send(dst_mac, payload)
                return True
            backoff = 0.1 * (2 ** attempt)
            print(f"[L1] Medio ocupado, esperando {backoff:.2f}s...")
            time.sleep(backoff)
        print("[L1] No se pudo acceder al medio.")
        return False
