#!/usr/bin/env python3
from pathlib import Path
import sys

FD_NUT = 38


def find_start_codes(data):
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
    return starts


def iter_nals(data):
    starts = find_start_codes(data)
    for idx, (start, size) in enumerate(starts):
        header = start + size
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
        if header + 2 <= end:
            nal_type = (data[header] >> 1) & 0x3f
            yield nal_type, data[header + 2:end]


def bits_to_text(bits):
    out = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i:i + 8]
        if len(chunk) < 8:
            break
        value = 0
        for bit in chunk:
            value = (value << 1) | bit
        out.append(value)
    return out.decode("ascii", errors="replace")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../public/warehouse-suspect.hevc")
    bits = []
    for nal_type, payload in iter_nals(path.read_bytes()):
        if nal_type != FD_NUT:
            continue
        ff_count = 0
        for byte in payload:
            if byte == 0xff:
                ff_count += 1
            else:
                break
        bits.append(ff_count % 2)
    print(bits_to_text(bits))


if __name__ == "__main__":
    main()
