from pathlib import Path
import random

import cv2
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SOLUTION = ROOT / "solution"
TILES = SOLUTION / "emoji_tiles"

FLAG = "blockChainPTIT{stegosaurus_mosaic_qr}"
SEED = 202507
TILE_SIZE = 32

LIGHT_TOKENS = [
    "imagine",
    "rooOreos",
    "rooZyphen",
    "rooYayEt3rnos",
    "thisisfine",
    "rooSunNobooli",
]

DARK_TOKENS = [
    "harold",
    "why",
    "rooFrozenVoid",
    "rooRobin",
    "breadThink",
    "skullfire",
]


def make_tile(path: Path, fill: tuple[int, int, int]) -> None:
    image = Image.new("RGB", (TILE_SIZE, TILE_SIZE), fill)
    image.save(path)


def make_tiles() -> None:
    TILES.mkdir(parents=True, exist_ok=True)
    for index, token in enumerate(LIGHT_TOKENS):
        shade = 246 + (index % 2) * 4
        make_tile(TILES / f"{token}.png", (shade, shade, shade))
    for index, token in enumerate(DARK_TOKENS):
        shade = 0 + (index % 2) * 4
        make_tile(TILES / f"{token}.png", (shade, shade, shade))


def make_qr() -> Image.Image:
    params = cv2.QRCodeEncoder_Params()
    params.correction_level = cv2.QRCodeEncoder_CORRECT_LEVEL_M
    encoder = cv2.QRCodeEncoder_create(params)
    qr = encoder.encode(FLAG)
    qr_image = Image.fromarray(qr).convert("L")
    bordered = Image.new("L", (qr_image.width + 8, qr_image.height + 8), 255)
    bordered.paste(qr_image, (4, 4))
    return bordered


def main() -> None:
    rng = random.Random(SEED)
    make_tiles()

    qr = make_qr()
    qr.save(SOLUTION / "qr_code.png")

    pixels = qr.load()
    rows = []
    for y in range(qr.height):
        row = []
        for x in range(qr.width):
            token_pool = DARK_TOKENS if pixels[x, y] < 128 else LIGHT_TOKENS
            row.append(rng.choice(token_pool))
        rows.append(" ".join(row))

    (PUBLIC / "STEGosaurus.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"built {PUBLIC / 'STEGosaurus.txt'} with flag {FLAG}")


if __name__ == "__main__":
    main()
