from pathlib import Path
import random

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

FLAG = "blockChainPTIT{m0r3_blU3_st3g4n0gr4phy_d4_b4_d33}"
BASE_COLOR = (64, 77, 180)
SIZE = 512
SEED = 20260519


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    random.seed(SEED)

    image = Image.new("RGB", (SIZE, SIZE), BASE_COLOR)
    pixels = image.load()

    width = image.size[0] // len(FLAG)
    height = image.size[1] // len(FLAG)

    for index, char in enumerate(FLAG):
        for _ in range(ord(char)):
            x = random.randint(0, width - 1) + width * index
            y = random.randint(0, height - 1) + height * index
            channel = random.randint(0, 2)
            color = list(pixels[x, y])
            color[channel] += 1
            pixels[x, y] = tuple(color)

    image.save(PUBLIC / "blue.png")
    (PUBLIC / "HINT.txt").write_text(
        "Không phải màu xanh nào cũng giống nhau.\n"
        "Nếu nhìn thấy một đường chéo hơi lạ, hãy thử đếm thay vì đoán.\n",
        encoding="utf-8",
    )

    print(FLAG)
    print(PUBLIC / "blue.png")


if __name__ == "__main__":
    main()
