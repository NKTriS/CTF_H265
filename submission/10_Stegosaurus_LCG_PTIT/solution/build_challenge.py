from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import random

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

FILENAME = "LSBSTEGO_CONFIG_LCG[1664525,1013904223,4294967296]_DEFAULT1111.png"
FLAG = "blockChainPTIT{l5b_lcg_4nd_x0r_4r3_4_fun_ch41n}"
PASSWORD = "DEFAULT1111"
A = 1664525
C = 1013904223
M = 4294967296
SIZE = 640


def lcg(seed: int):
    state = seed
    while True:
        state = (A * state + C) % M
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


def bits_from_bytes(data: bytes) -> list[int]:
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def make_cover() -> Image.Image:
    random.seed(20260519)
    image = Image.new("RGB", (SIZE, SIZE), (222, 232, 214))
    draw = ImageDraw.Draw(image)

    for y in range(SIZE):
        r = 218 - y // 28
        g = 232 - y // 36
        b = 214 + y // 40
        draw.line((0, y, SIZE, y), fill=(r, g, b))

    for _ in range(1800):
        x = random.randrange(SIZE)
        y = random.randrange(SIZE)
        color = (
            160 + random.randrange(45),
            178 + random.randrange(40),
            132 + random.randrange(45),
        )
        draw.point((x, y), fill=color)

    body = [(145, 375), (190, 315), (300, 280), (430, 295), (505, 355), (455, 405), (285, 420)]
    draw.polygon(body, fill=(75, 122, 83), outline=(39, 83, 56))
    draw.ellipse((132, 292, 215, 370), fill=(75, 122, 83), outline=(39, 83, 56))
    draw.polygon([(112, 285), (155, 305), (138, 340), (92, 332)], fill=(75, 122, 83), outline=(39, 83, 56))

    plates = [(185, 292), (235, 263), (290, 252), (345, 260), (402, 282)]
    for x, y in plates:
        draw.polygon([(x - 18, y + 25), (x, y - 28), (x + 20, y + 25)], fill=(170, 98, 75), outline=(97, 54, 48))

    for x in (245, 385):
        draw.rectangle((x, 397, x + 28, 478), fill=(54, 100, 67))
        draw.polygon([(x, 478), (x + 46, 478), (x + 35, 492), (x - 5, 490)], fill=(45, 82, 59))

    draw.polygon([(490, 350), (575, 330), (598, 348), (514, 378)], fill=(75, 122, 83), outline=(39, 83, 56))
    draw.ellipse((116, 312, 124, 320), fill=(10, 20, 14))
    return image


def embed(image: Image.Image, payload: bytes) -> Image.Image:
    pixels = image.load()
    total_pixels = image.size[0] * image.size[1]
    bits = bits_from_bytes(payload)
    gen = lcg(seed_from_password(PASSWORD))
    used = set()
    bit_index = 0

    while bit_index < len(bits):
        pixel_index = next(gen) % total_pixels
        if pixel_index in used:
            continue
        used.add(pixel_index)
        x = pixel_index % image.size[0]
        y = pixel_index // image.size[0]
        rgb = list(pixels[x, y])
        for channel in range(3):
            if bit_index >= len(bits):
                break
            rgb[channel] = (rgb[channel] & 0xFE) | bits[bit_index]
            bit_index += 1
        pixels[x, y] = tuple(rgb)

    return image


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)

    plaintext = FLAG.encode()
    key = xor_stream(len(plaintext), PASSWORD)
    ciphertext = bytes(a ^ b for a, b in zip(plaintext, key))
    payload = b"BCPT" + len(ciphertext).to_bytes(2, "big") + ciphertext

    image = embed(make_cover(), payload)
    image.save(PUBLIC / FILENAME)
    (PUBLIC / "HINT.txt").write_text(
        "Tên file lắm lời hơn bạn tưởng.\n"
        "LSB cho biết chỗ đọc bit, LCG cho biết thứ tự đọc, DEFAULT1111 cho biết chìa khóa.\n",
        encoding="utf-8",
    )

    print(FLAG)
    print(PUBLIC / FILENAME)


if __name__ == "__main__":
    main()
