#!/usr/bin/env python3
import re
import sys
from pathlib import Path


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


def main():
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} bunny_aud_suspect.hevc")
        raise SystemExit(2)

    data = Path(sys.argv[1]).read_bytes()
    bits = []
    aud_count = 0

    for nal in find_nals(data):
        if nal_type(nal) != 35:
            continue
        aud_count += 1
        if len(nal) < 3:
            continue
        primary_pic_type = (nal[2] >> 5) & 0x07
        bits.append(primary_pic_type & 1)

    stream = bits_to_bytes(bits)
    match = re.search(rb"HEVC\{[ -~]+?\}", stream)

    print(f"AUD_NAL_COUNT={aud_count}")
    if not match:
        print(stream[:96])
        raise SystemExit("flag not found")
    print(match.group(0).decode())


if __name__ == "__main__":
    main()
