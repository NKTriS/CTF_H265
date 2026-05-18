#!/usr/bin/env python3
from pathlib import Path
import csv
import sys


def bits_to_text(bits):
    chars = []
    for pos in range(0, len(bits), 8):
        chunk = bits[pos:pos + 8]
        if len(chunk) < 8:
            break
        value = 0
        for bit in chunk:
            value = (value << 1) | bit
        chars.append(chr(value))
    return "".join(chars)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../public/merge_trace.csv")
    bits = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["merge_flag"]) == 1 and int(row["candidate_count"]) >= 2 and int(row["usable"]) == 1:
                bits.append(int(row["merge_idx"]) % 2)
    print(bits_to_text(bits[:29 * 8]))


if __name__ == "__main__":
    main()
