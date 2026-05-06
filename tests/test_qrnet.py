"""
Tests unitarios — QR-NET
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pytest
from layer1_physical.dispositivo_luz_adaptador import (
    build_frame, parse_frame, crc16, generate_mac,
    FRAME_TYPE_DATA, MAX_PAYLOAD
)
from layer2_3_network.node import QRNetPacket, QRNetNode


# ---------------------------------------------------------------------------
# Capa 1
# ---------------------------------------------------------------------------

class TestLayer1:

    def test_crc16_basic(self):
        data = b"hello"
        assert isinstance(crc16(data), int)
        assert 0 <= crc16(data) <= 0xFFFF

    def test_generate_mac(self):
        mac = generate_mac()
        assert len(mac) == 6

    def test_build_and_parse_frame(self):
        src = generate_mac()
        dst = generate_mac()
        payload = b"test payload"
        frame = build_frame(src, dst, payload)
        assert len(frame) <= 128
        parsed = parse_frame(frame)
        assert parsed is not None
        assert parsed["payload"] == payload

    def test_frame_rejects_large_payload(self):
        src = generate_mac()
        dst = generate_mac()
        with pytest.raises(ValueError):
            build_frame(src, dst, b"x" * (MAX_PAYLOAD + 1))

    def test_corrupted_frame_rejected(self):
        src = generate_mac()
        dst = generate_mac()
        frame = bytearray(build_frame(src, dst, b"data"))
        frame[-1] ^= 0xFF   # Corromper checksum
        assert parse_frame(bytes(frame)) is None

    def test_wrong_preamble_rejected(self):
        src = generate_mac()
        dst = generate_mac()
        frame = bytearray(build_frame(src, dst, b"data"))
        frame[0] = 0x00     # Preamble incorrecto
        assert parse_frame(bytes(frame)) is None


# ---------------------------------------------------------------------------
# Capa 2/3
# ---------------------------------------------------------------------------

class TestLayer23:

    def test_packet_serialization(self):
        pkt = QRNetPacket(
            msg_type = "DATA",
            src_node = "aabbcc",
            dst_node = "ddeeff",
            payload  = "hello",
        )
        raw = pkt.to_json()
        restored = QRNetPacket.from_json(raw)
        assert restored.payload == "hello"
        assert restored.payload_len == len("hello".encode())

    def test_anonymous_node_id(self):
        node = QRNetNode.__new__(QRNetNode)
        id1 = QRNetNode._generate_anonymous_id()
        id2 = QRNetNode._generate_anonymous_id()
        assert id1 != id2          # Siempre diferente
        assert len(id1) == 64     # SHA-256 hex = 64 chars
