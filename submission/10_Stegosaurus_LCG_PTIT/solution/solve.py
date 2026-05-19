from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import sys

from PIL import Image


A = 1664525
C = 1013904223
M = 4294967296
PASSWORD_RE = re.compile(r"_([A-Z0-9]+)\.png$")
LCG_RE = re.compile(r"LCG\[(\d+),(\d+),(\d+)\]")


def lcg(seed: int, a: int, c: int, m: int):
    state = seed
    while True:
        state = (a * state + c) % m
        yield state


def seed_from_password(password: str) -> int:
    return int.from_bytes(sha256(password.encode()).digest()[:4], "little")


def xor_stream(length: int, password: str) -> bytes:
    digest = sha256((password + ":blockChainPTIT").encode()).digest()
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(sha256(digest + counter.to_bytes(4, "little")).digest())
        counter += 1
    return bytes(out[:length])


def bytes_from_bits(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = (byte << 1) | bit
        out.append(byte)
    return bytes(out)


def extract_bits(image: Image.Image, bit_count: int, a: int, c: int, m: int, password: str) -> list[int]:
    pixels = image.load()
    total_pixels = image.size[0] * image.size[1]
    gen = lcg(seed_from_password(password), a, c, m)
    used = set()
    bits = []

    while len(bits) < bit_count:
        pixel_index = next(gen) % total_pixels
        if pixel_index in used:
            continue
        used.add(pixel_index)
        x = pixel_index % image.size[0]
        y = pixel_index // image.size[0]
        bits.extend([pixels[x, y][0] & 1, pixels[x, y][1] & 1, pixels[x, y][2] & 1])

    return bits[:bit_count]


def parse_config(path: Path) -> tuple[int, int, int, str]:
    name = path.name
    lcg_match = LCG_RE.search(name)
    password_match = PASSWORD_RE.search(name)
    if not lcg_match or not password_match:
        raise ValueError("Tên file không chứa đủ cấu hình LCG/password.")
    a, c, m = map(int, lcg_match.groups())
    return a, c, m, password_match.group(1)


def solve(path: Path) -> str:
    a, c, m, password = parse_config(path)
    image = Image.open(path).convert("RGB")

    header = bytes_from_bits(extract_bits(image, 6 * 8, a, c, m, password))
    if header[:4] != b"BCPT":
        raise RuntimeError("Sai cấu hình hoặc sai seed, không đọc được magic.")

    length = int.from_bytes(header[4:6], "big")
    raw = bytes_from_bits(extract_bits(image, (6 + length) * 8, a, c, m, password))
    ciphertext = raw[6:]
    key = xor_stream(length, password)
    return bytes(a ^ b for a, b in zip(ciphertext, key)).decode()


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python {Path(sys.argv[0]).name} <challenge.png>")
        raise SystemExit(1)
    print(solve(Path(sys.argv[1])))


if __name__ == "__main__":
    main()
