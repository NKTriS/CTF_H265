#!/usr/bin/env python3
from pathlib import Path
import sys


def find_start_codes(data):
    out = []
    i = 0
    while i < len(data) - 3:
        if data[i:i + 4] == b"\x00\x00\x00\x01":
            out.append((i, 4))
            i += 4
        elif data[i:i + 3] == b"\x00\x00\x01":
            out.append((i, 3))
            i += 3
        else:
            i += 1
    return out


def iter_nals(data):
    starts = find_start_codes(data)
    for idx, (start, size) in enumerate(starts):
        off = start + size
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
        if off + 2 <= end:
            payload = data[off:end]
            nal_type = (payload[0] >> 1) & 0x3f
            yield nal_type, payload


def ebsp_to_rbsp(data):
    out = bytearray()
    zeros = 0
    i = 0
    while i < len(data):
        b = data[i]
        if zeros >= 2 and b == 0x03:
            zeros = 0
            i += 1
            continue
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
        i += 1
    return bytes(out)


def read_ff(data, off):
    value = 0
    while off < len(data) and data[off] == 0xff:
        value += 255
        off += 1
    if off < len(data):
        value += data[off]
        off += 1
    return value, off


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../public/suspicious.hevc")
    data = path.read_bytes()
    for nal_type, nal in iter_nals(data):
        if nal_type not in (39, 40):
            continue
        rbsp = ebsp_to_rbsp(nal[2:])
        off = 0
        while off + 2 <= len(rbsp):
            payload_type, off = read_ff(rbsp, off)
            payload_size, off = read_ff(rbsp, off)
            payload = rbsp[off:off + payload_size]
            off += payload_size
            if payload_type != 5 or len(payload) <= 16:
                continue
            encrypted = payload[16:]
            for key in range(256):
                text = bytes(b ^ key for b in encrypted)
                if text.startswith(b"HEVC-LAB{"):
                    print(text.decode())
                    return
    raise SystemExit("flag not found")


if __name__ == "__main__":
    main()
