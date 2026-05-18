#!/usr/bin/env python3
from pathlib import Path
from dataclasses import dataclass
import sys

MAX_RECORDS = 200


@dataclass
class Nal:
    index: int
    data: bytes

    @property
    def nal_type(self):
        return (self.data[0] >> 1) & 0x3f if len(self.data) >= 2 else -1

    @property
    def is_vcl(self):
        return 0 <= self.nal_type <= 31


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


def parse_annex_b(data):
    starts = find_start_codes(data)
    for idx, (start, size) in enumerate(starts):
        off = start + size
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
        if off < end:
            yield Nal(idx, data[off:end])


def carrier_locations(data, limit=MAX_RECORDS):
    locations = []
    for nal in parse_annex_b(data):
        if not nal.is_vcl or len(nal.data) < 80:
            continue
        for byte_index in (23, 47):
            locations.append((nal, byte_index))
            if len(locations) >= limit:
                return locations
    return locations


def bits_to_text(bits):
    out = bytearray()
    for offset in range(0, len(bits) - 7, 8):
        value = 0
        for bit in bits[offset:offset + 8]:
            value = (value << 1) | bit
        out.append(value)
    return out.decode("utf-8", errors="replace").rstrip("\x00")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../public/cctv.hevc")
    bits = []
    for idx, (nal, byte_index) in enumerate(carrier_locations(path.read_bytes())):
        raw = nal.data[byte_index]
        hidden_bit = raw & 1
        magnitude = (((raw >> 1) + idx) % 11 + 1) * 2
        mv_x = magnitude + hidden_bit
        if idx % 7 == 0:
            mv_x = -mv_x
        bits.append(abs(mv_x) % 2)
    print(bits_to_text(bits))


if __name__ == "__main__":
    main()
