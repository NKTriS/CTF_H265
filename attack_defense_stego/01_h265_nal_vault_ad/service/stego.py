import hashlib
import struct
import zlib
from pathlib import Path


MAGIC = b"H5AD"
MAX_SECRET_LEN = 2048
TEMPLATE_PATH = Path(__file__).with_name("assets") / "cctv_redacted_template.hevc"


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


def _byte_stream(seed: str, label: bytes):
    counter = 0
    seed_bytes = seed.encode("utf-8")
    while True:
        block = hashlib.sha256(label + seed_bytes + counter.to_bytes(4, "big")).digest()
        counter += 1
        for value in block:
            yield value


def _xor_bits(bits: list[int], seed: str) -> list[int]:
    stream = _byte_stream(seed, b"h265-ad-mask:")
    out = []
    current = 0
    remaining = 0
    for bit in bits:
        if remaining == 0:
            current = next(stream)
            remaining = 8
        remaining -= 1
        out.append(bit ^ ((current >> remaining) & 1))
    return out


def _manchester_encode(bits: list[int]) -> list[int]:
    encoded = []
    for bit in bits:
        encoded.extend((1, 0) if bit else (0, 1))
    return encoded


def _manchester_decode(bits: list[int]) -> list[int]:
    decoded = []
    for i in range(0, len(bits) - 1, 2):
        pair = bits[i:i + 2]
        if pair == [0, 1]:
            decoded.append(0)
        elif pair == [1, 0]:
            decoded.append(1)
        else:
            raise StegoError("bad manchester symbol")
    return decoded


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
    bits = _manchester_encode(_xor_bits(_bytes_to_bits(packet), seed))

    template = TEMPLATE_PATH.read_bytes()
    marker = bytearray()
    cadence = _byte_stream(seed, b"h265-ad-cadence:")

    for index, bit in enumerate(bits):
        decoys = 1 + (next(cadence) % 3)
        for _ in range(decoys):
            noise = next(cadence) & 0x07
            marker += _nal(35, bytes([(noise << 5) | 0x10]))

        cover = next(cadence) & 0x03
        primary_pic_type = (cover << 1) | bit
        aud_rbsp = bytes([(primary_pic_type << 5) | 0x10])
        marker += _nal(35, aud_rbsp)

    return template + bytes(marker)


def extract_secret(bitstream: bytes, seed: str) -> str:
    aud_bits = []
    for nal in find_nals(bitstream):
        if nal_type(nal) != 35 or len(nal) < 3:
            continue
        primary_pic_type = (nal[2] >> 5) & 0x07
        aud_bits.append(primary_pic_type & 1)

    encoded = []
    pos = 0
    cadence = _byte_stream(seed, b"h265-ad-cadence:")
    while pos < len(aud_bits):
        decoys = 1 + (next(cadence) % 3)
        for _ in range(decoys):
            if pos >= len(aud_bits):
                break
            next(cadence)
            pos += 1
        if pos >= len(aud_bits):
            break
        next(cadence)
        encoded.append(aud_bits[pos])
        pos += 1

    bits = _xor_bits(_manchester_decode(encoded), seed)

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
