#!/usr/bin/env python3
import re
import sys
import zlib
import struct
from pathlib import Path
from math import gcd


def find_nals(data: bytes):
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
        yield data[start + sc_len:end]


def nal_type(nal: bytes) -> int:
    if len(nal) < 2:
        return -1
    return (nal[0] >> 1) & 0x3F


def bits_to_bytes(bits):
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        out.append(value)
    return bytes(out)


def read_aud_bits_and_vcl_sizes(data: bytes):
    bits = []
    vcl_sizes = []
    for nal in find_nals(data):
        ntype = nal_type(nal)
        if ntype == 35 and len(nal) >= 3:
            primary_pic_type = (nal[2] >> 5) & 0x07
            bits.append(primary_pic_type & 1)
        elif 0 <= ntype <= 31:
            vcl_sizes.append(len(nal))
    return bits, vcl_sizes


def decode_walk(aud_bits, vcl_bits, start, step):
    walked = []
    pos = start
    for _ in range(len(aud_bits)):
        walked.append(aud_bits[pos] ^ vcl_bits[pos])
        pos = (pos + step) % len(aud_bits)
    raw = bits_to_bytes(walked)
    if len(raw) < 8 or raw[:2] != b"AU":
        return b""
    size = struct.unpack(">H", raw[2:4])[0]
    if not 0 < size < 256 or len(raw) < 4 + size + 4:
        return b""
    plain = raw[4:4 + size]
    crc_expected = struct.unpack(">I", raw[4 + size:8 + size])[0]
    if zlib.crc32(plain) != crc_expected:
        return b""
    return plain


def main():
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} bunny_aud_suspect.hevc")
        raise SystemExit(2)

    data = Path(sys.argv[1]).read_bytes()
    bits, vcl_sizes = read_aud_bits_and_vcl_sizes(data)
    vcl_bits = [
        1 if vcl_sizes[i] > vcl_sizes[(i - 1) % len(vcl_sizes)] else 0
        for i in range(len(bits))
    ]

    print(f"AUD_NAL_COUNT={len(bits)}")

    for start in range(len(bits)):
        for step in range(1, len(bits)):
            if gcd(step, len(bits)) != 1:
                continue
            stream = decode_walk(bits, vcl_bits, start, step)
            match = re.search(rb"HEVC\{[ -~]+?\}", stream)
            if match:
                print(f"WALK_START={start}")
                print(f"WALK_STEP={step}")
                print(match.group(0).decode())
                return

    raise SystemExit("flag not found")


if __name__ == "__main__":
    main()
