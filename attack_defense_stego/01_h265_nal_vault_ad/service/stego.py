import hashlib
import random
import struct
import zlib


MAGIC = b"H5AD"
MAX_SECRET_LEN = 2048


class StegoError(ValueError):
    pass


def _nal_header(nal_type: int, temporal_id: int = 1) -> bytes:
    if not 0 <= nal_type <= 63:
        raise StegoError("bad nal type")
    return bytes([(nal_type << 1) & 0x7E, temporal_id & 0x07])


def _nal(nal_type: int, payload: bytes) -> bytes:
    return b"\x00\x00\x00\x01" + _nal_header(nal_type) + payload


def _bytes_to_bits(data: bytes) -> list[int]:
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def _bits_to_bytes(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        out.append(value)
    return bytes(out)


def _randbytes(rng: random.Random, size: int) -> bytes:
    return bytes(rng.randrange(0, 256) for _ in range(size))


def find_nals(data: bytes):
    starts = []
    i = 0
    while i < len(data) - 3:
        if data[i:i + 4] == b"\x00\x00\x00\x01":
            starts.append((i, 4))
            i += 4
        elif data[i:i + 3] == b"\x00\x00\x01":
            starts.append((i, 3))
            i += 3
        else:
            i += 1

    for idx, (start, sc_len) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
        nal = data[start + sc_len:end]
        if nal:
            yield nal


def nal_type(nal: bytes) -> int:
    if len(nal) < 2:
        return -1
    return (nal[0] >> 1) & 0x3F


def embed_secret(secret: str, seed: str) -> bytes:
    secret_bytes = secret.encode("utf-8")
    if len(secret_bytes) > MAX_SECRET_LEN:
        raise StegoError("secret too large")

    packet = MAGIC + struct.pack(">H", len(secret_bytes)) + secret_bytes
    packet += struct.pack(">I", zlib.crc32(secret_bytes) & 0xFFFFFFFF)
    bits = _bytes_to_bits(packet)

    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))

    out = bytearray()
    out += _nal(32, b"\x01HEVC_VPS_NAL_VAULT")
    out += _nal(33, b"\x01HEVC_SPS_160x90")
    out += _nal(34, b"\x01HEVC_PPS")

    for index, bit in enumerate(bits):
        primary_pic_type = (rng.randrange(0, 4) << 1) | bit
        aud_rbsp = bytes([(primary_pic_type << 5) | 0x10])
        out += _nal(35, aud_rbsp)

        vcl_type = 19 if index % 37 == 0 else 1
        payload_len = 24 + (index * 17 + rng.randrange(0, 16)) % 96
        out += _nal(vcl_type, _randbytes(rng, payload_len))

    out += _nal(36, b"\x80")
    return bytes(out)


def extract_secret(bitstream: bytes) -> str:
    bits = []
    for nal in find_nals(bitstream):
        if nal_type(nal) != 35 or len(nal) < 3:
            continue
        primary_pic_type = (nal[2] >> 5) & 0x07
        bits.append(primary_pic_type & 1)

    if len(bits) < 48:
        raise StegoError("not enough aud nals")

    header = _bits_to_bytes(bits[:48])
    if header[:4] != MAGIC:
        raise StegoError("missing magic")

    size = struct.unpack(">H", header[4:6])[0]
    if size > MAX_SECRET_LEN:
        raise StegoError("invalid secret size")

    total_bits = (4 + 2 + size + 4) * 8
    if len(bits) < total_bits:
        raise StegoError("truncated payload")

    packet = _bits_to_bytes(bits[:total_bits])
    secret = packet[6:6 + size]
    crc_expected = struct.unpack(">I", packet[6 + size:10 + size])[0]
    crc_actual = zlib.crc32(secret) & 0xFFFFFFFF
    if crc_actual != crc_expected:
        raise StegoError("bad crc")

    return secret.decode("utf-8")
