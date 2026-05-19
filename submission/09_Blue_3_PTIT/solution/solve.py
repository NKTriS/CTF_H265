from collections import Counter
from pathlib import Path
import re
import sys

from PIL import Image


FLAG_RE = re.compile(r"blockChainPTIT\{[0-9A-Za-z_]*\}")


def decode_with_length(image: Image.Image, length: int, main_color: tuple[int, int, int]) -> str:
    pixels = image.load()
    width = image.size[0] // length
    height = image.size[1] // length
    decoded = []

    for index in range(length):
        total = 0
        for x in range(width * index, width * (index + 1)):
            for y in range(height * index, height * (index + 1)):
                total += sum(pixels[x, y][channel] - main_color[channel] for channel in range(3))
        if total > 255:
            return ""
        decoded.append(chr(total))

    return "".join(decoded)


def solve(path: Path) -> str:
    image = Image.open(path).convert("RGB")
    pixels = image.load()
    main_color = Counter(
        pixels[x, y] for x in range(image.size[0]) for y in range(image.size[1])
    ).most_common(1)[0][0]

    for length in range(1, image.size[0] + 1):
        candidate = decode_with_length(image, length, main_color)
        if FLAG_RE.fullmatch(candidate):
            return candidate

    raise RuntimeError("Không tìm thấy flag đúng format.")


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python {Path(sys.argv[0]).name} <blue.png>")
        raise SystemExit(1)
    print(solve(Path(sys.argv[1])))


if __name__ == "__main__":
    main()
