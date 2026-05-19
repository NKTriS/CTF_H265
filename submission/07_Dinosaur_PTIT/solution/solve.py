from pathlib import Path
import argparse
import math

import cv2
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SOLUTION = ROOT / "solution"
DEFAULT_TILES = SOLUTION / "emoji_tiles"
TILE_SIZE = 32


def load_tokens(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").split()


def dimensions(count: int) -> tuple[int, int]:
    side = int(math.isqrt(count))
    if side * side == count:
        return side, side
    for width in range(side, count + 1):
        if count % width == 0:
            return width, count // width
    raise ValueError("could not determine mosaic dimensions")


def reconstruct(tokens: list[str], tiles_dir: Path, output: Path) -> Path:
    width, height = dimensions(len(tokens))
    mosaic = Image.new("RGB", (width * TILE_SIZE, height * TILE_SIZE))

    for index, token in enumerate(tokens):
        tile_path = tiles_dir / f"{token}.png"
        if not tile_path.exists():
            raise FileNotFoundError(f"missing tile image: {tile_path}")
        tile = Image.open(tile_path).convert("RGB").resize((TILE_SIZE, TILE_SIZE))
        x = (index % width) * TILE_SIZE
        y = (index // width) * TILE_SIZE
        mosaic.paste(tile, (x, y))

    output.parent.mkdir(parents=True, exist_ok=True)
    mosaic.save(output)
    return output


def decode_qr(image_path: Path) -> str:
    detector = cv2.QRCodeDetector()
    image = cv2.imread(str(image_path))
    text, _, _ = detector.detectAndDecode(image)
    if text:
        return text

    for size in (820, 410, 205, 164):
        resized = cv2.resize(image, (size, size), interpolation=cv2.INTER_NEAREST)
        text, _, _ = detector.detectAndDecode(resized)
        if text:
            return text
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct the STEGosaurus mosaic and decode its QR flag.")
    parser.add_argument("stegosaurus", nargs="?", default=PUBLIC / "STEGosaurus.txt")
    parser.add_argument("tiles", nargs="?", default=DEFAULT_TILES)
    parser.add_argument("-o", "--output", default=SOLUTION / "reconstructed_mosaic.png")
    args = parser.parse_args()

    tokens = load_tokens(Path(args.stegosaurus))
    output = reconstruct(tokens, Path(args.tiles), Path(args.output))
    flag = decode_qr(output)
    if not flag:
        raise SystemExit(f"could not decode QR from {output}")

    print(flag)
    print(f"mosaic: {output}")


if __name__ == "__main__":
    main()
