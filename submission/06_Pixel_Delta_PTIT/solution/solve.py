from pathlib import Path
from PIL import Image
import argparse


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SOLUTION = ROOT / "solution"


def bits_to_bytes(bits: str) -> bytes:
    usable = len(bits) - (len(bits) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, usable, 8))


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover the hidden flag from Pixel Delta.")
    parser.add_argument("original", nargs="?", default=SOLUTION / "original.png")
    parser.add_argument("chall", nargs="?", default=PUBLIC / "chall.png")
    args = parser.parse_args()

    original = Image.open(args.original).convert("RGBA")
    suspect = Image.open(args.chall).convert("RGBA")

    if original.size != suspect.size:
        raise SystemExit("image sizes do not match")

    op = original.load()
    sp = suspect.load()
    bits = []

    for x in range(original.size[0]):
        for y in range(original.size[1]):
            ro, _, bo, _ = op[x, y]
            rs, _, bs, _ = sp[x, y]
            if bs - bo == 1:
                diff = rs - ro
                if diff not in (0, 1):
                    raise SystemExit(f"unexpected red delta {diff} at {(x, y)}")
                bits.append(str(diff))

    decoded = bits_to_bytes("".join(bits)).rstrip(b"\x00")
    start = decoded.find(b"blockChainPTIT{")
    end = decoded.find(b"}", start)
    if start == -1 or end == -1:
        raise SystemExit(decoded)

    print(decoded[start:end + 1].decode())


if __name__ == "__main__":
    main()
