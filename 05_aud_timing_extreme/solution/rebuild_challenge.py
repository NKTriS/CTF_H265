#!/usr/bin/env python3
import random
import struct
import zlib
from pathlib import Path

INFILE = Path("../public/bunny_aud_suspect.hevc")
OUTFILE = Path("../public/bunny_aud_suspect.hevc")
FLAG = b"blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}"
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

    packet = b"AU" + struct.pack(">H", len(FLAG)) + FLAG + struct.pack(">I", zlib.crc32(FLAG))
    bits = list(bits_from_bytes(packet))

    noise = random.Random(0xC0DEC0DE)
    for rbsp in aud_offsets:
        primary = noise.randrange(0, 8)
        data[rbsp] = (data[rbsp] & 0x1F) | (primary << 5)

    for k, bit in enumerate(bits):
        pos = (START + STEP * k) % len(aud_offsets)
        rbsp = aud_offsets[pos]
        primary = ((data[rbsp] >> 5) & 0x07)
        # Hide the payload as a relation between AUD and the local VCL size trend.
        # Raw AUD parity alone is only noise; absolute VCL size parity is also not enough.
        trend_bit = 1 if vcl_sizes[pos] > vcl_sizes[(pos - 1) % len(vcl_sizes)] else 0
        wanted_lsb = bit ^ trend_bit
        primary = (primary & 0x06) | wanted_lsb
        data[rbsp] = (data[rbsp] & 0x1F) | (primary << 5)

    OUTFILE.write_bytes(data)
    print(f"AUD={len(aud_offsets)} VCL={len(vcl_sizes)} bits={len(bits)} start={START} step={STEP}")


if __name__ == "__main__":
    main()
