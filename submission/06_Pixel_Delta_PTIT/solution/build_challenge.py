from pathlib import Path
from PIL import Image
import random


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SOLUTION = ROOT / "solution"
FLAG = b"blockChainPTIT{pixel_delta_reveals_all}"
SEED = 20260519


def bits_from_bytes(data: bytes) -> list[int]:
    return [int(bit) for byte in data for bit in f"{byte:08b}"]


def main() -> None:
    bits = bits_from_bytes(FLAG)
    image = Image.open(SOLUTION / "original.png").convert("RGBA")
    pixels = image.load()
    rng = random.Random(SEED)

    for x in range(image.size[0]):
        for y in range(image.size[1]):
            if not bits:
                image.save(PUBLIC / "chall.png")
                print(f"embedded {FLAG.decode()}")
                return
            if rng.randint(0, 50) != 1:
                continue

            r, g, b, a = pixels[x, y]
            bit = bits[0]
            if b == 255 or (bit == 1 and r == 255):
                continue
            bits.pop(0)
            pixels[x, y] = (r + bit, g, b + 1, a)

    raise RuntimeError("not enough safe pixels to embed the flag")


if __name__ == "__main__":
    main()
