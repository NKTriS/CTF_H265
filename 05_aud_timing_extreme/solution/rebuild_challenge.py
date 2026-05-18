#!/usr/bin/env python3
import hashlib
import random
import struct
import zlib
from pathlib import Path

INFILE = Path("../public/bunny_aud_suspect.hevc")
OUTFILE = Path("../public/bunny_aud_suspect.hevc")
FLAG = b"HEVC{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}"
START = 19
STEP = 73


def find_nals(data):
    starts = []
    i = 0
    while i < len(data) - 3:
        if data[i:i + 3] == b"\x00\x00\x01":
            starts.append((i, 3))
            i += 3
        elif data[i:i + 4] == b"\x00\x00\x00\x01":
            starts.append((i, 4))
            i += 4
        else:
            i += 1
    for idx, (start, sc_len) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
        yield start, sc_len, end


def nal_type(nal):
    return ((nal[0] >> 1) & 0x3F) if len(nal) >= 2 else -1


def bits_from_bytes(payload):
    for b in payload:
        for shift in range(7, -1, -1):
            yield (b >> shift) & 1


def keystream(seed, size):
    rng = random.Random(seed)
    return bytes(rng.randrange(0, 256) for _ in range(size))


def main():
    data = bytearray(INFILE.read_bytes())
    aud_offsets = []
    vcl_sizes = []

    for start, sc_len, end in find_nals(data):
        nal = data[start + sc_len:end]
        ntype = nal_type(nal)
        if ntype == 35 and len(nal) >= 3:
            aud_offsets.append(start + sc_len + 2)
        elif 0 <= ntype <= 31:
            vcl_sizes.append(len(nal))

    if len(aud_offsets) < 430:
        raise SystemExit("not enough AUD units")

    # The key is reproducible from image-bearing NAL sizes, but it is not stored as text.
    material = ",".join(map(str, vcl_sizes[:64])).encode()
    seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")

    compressed = zlib.compress(FLAG, level=9)
    mask = keystream(seed, len(compressed))
    cipher = bytes(a ^ b for a, b in zip(compressed, mask))
    packet = b"AU" + struct.pack(">H", len(cipher)) + cipher + struct.pack(">I", zlib.crc32(FLAG))
    bits = list(bits_from_bytes(packet))

    noise = random.Random(0xC0DEC0DE)
    for rbsp in aud_offsets:
        primary = noise.randrange(0, 8)
        data[rbsp] = (data[rbsp] & 0x1F) | (primary << 5)

    for k, bit in enumerate(bits):
        pos = (START + STEP * k) % len(aud_offsets)
        rbsp = aud_offsets[pos]
        primary = ((data[rbsp] >> 5) & 0x07)
        primary = (primary & 0x06) | bit
        data[rbsp] = (data[rbsp] & 0x1F) | (primary << 5)

    OUTFILE.write_bytes(data)
    print(f"AUD={len(aud_offsets)} VCL={len(vcl_sizes)} bits={len(bits)} seed=0x{seed:016x}")


if __name__ == "__main__":
    main()
