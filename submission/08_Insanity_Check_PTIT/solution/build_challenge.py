from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SOLUTION = ROOT / "solution"

FLAG = "blockChainPTIT{1ns4n1ty_svg_to_1ts_fullest}"
MESSAGE = "blockchainptit 1ns4n1ty svg to 1ts fullest"

MORSE = {
    "a": ".-",
    "b": "-...",
    "c": "-.-.",
    "d": "-..",
    "e": ".",
    "f": "..-.",
    "g": "--.",
    "h": "....",
    "i": "..",
    "j": ".---",
    "k": "-.-",
    "l": ".-..",
    "m": "--",
    "n": "-.",
    "o": "---",
    "p": ".--.",
    "q": "--.-",
    "r": ".-.",
    "s": "...",
    "t": "-",
    "u": "..-",
    "v": "...-",
    "w": ".--",
    "x": "-..-",
    "y": "-.--",
    "z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
}


def message_to_morse(message: str) -> str:
    words = []
    for word in message.lower().split():
        words.append(" ".join(MORSE[c] for c in word))
    return " / ".join(words) + " //"


def lengths(symbol: str) -> tuple[int, int]:
    if symbol == ".":
        return 1, 1
    if symbol == "-":
        return 3, 1
    if symbol == " ":
        return 0, 3
    if symbol == "/":
        return 0, 1
    raise ValueError(f"unexpected morse symbol: {symbol!r}")


def keyframes(morse: str) -> str:
    total_time = sum(sum(lengths(c)) for c in morse)
    cur_time = 0
    lines = []
    for symbol in morse:
        on, off = lengths(symbol)
        if on:
            lines.append(f"{100.0 * cur_time / total_time:.3f}% {{ fill: #FFFF; }}")
            cur_time += on
        if off:
            lines.append(f"{100.0 * cur_time / total_time:.3f}% {{ fill: #FFF6; }}")
            cur_time += off
    lines.append("100% { fill: #FFF6; }")
    return "\n".join(lines)


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    SOLUTION.mkdir(parents=True, exist_ok=True)

    morse = message_to_morse(MESSAGE)
    (SOLUTION / "payload_morse.txt").write_text(morse + "\n", encoding="utf-8")

    svg = f"""<svg width="384" height="576" viewBox="0 0 384 576" xmlns="http://www.w3.org/2000/svg" id="root">
<style>
@keyframes blink {{
{keyframes(morse)}
}}
@keyframes rainbow1 {{
  0% {{ stop-color: hsl(27.3, 100%, 37.5%); }}
  50% {{ stop-color: hsl(0, 100%, 37.5%); }}
  100% {{ stop-color: hsl(27.3, 100%, 37.5%); }}
}}
@keyframes rainbow2 {{
  0% {{ stop-color: hsl(47, 80.9%, 61%); }}
  50% {{ stop-color: hsl(30, 80.9%, 61%); }}
  100% {{ stop-color: hsl(47, 80.9%, 61%); }}
}}
#gradient > stop:first-child {{
  animation: rainbow1 30s infinite linear;
}}
#gradient > stop:last-child {{
  animation: rainbow2 30s infinite linear;
}}
.center {{
  animation: blink 1200s infinite;
  animation-delay: 10s;
  animation-timing-function: steps(1, end);
}}
#center:not(.center) {{
  transform: translate(0, -192px);
}}
</style>
<defs>
<linearGradient id="gradient" gradientTransform="rotate(-30 0.5 0.5)">
  <stop offset="0%" stop-color="#bf5700"/>
  <stop offset="100%" stop-color="#ecc94b"/>
</linearGradient>
</defs>
<rect width="384" height="576" fill="url(#gradient)" stroke="none" />
<path id="lock" d="m64 256h256v256h-256zm192 64h-128v128h128zm-192-256h256v160h-64v-96h-128v96h-64z" fill="#fff" stroke="none"/>
<path id="center" class="center" d="m160 352h64v64h-64z" fill="#fff" stroke="none"/>
<script>
document.getElementById("center").classList.remove("center");
</script>
</svg>
"""
    (PUBLIC / "favicon.svg").write_text(svg, encoding="utf-8")
    (PUBLIC / "demo_page.html").write_text(
        '<!doctype html>\n<html lang="vi">\n  <head>\n    <link rel="icon" href="favicon.svg" type="image/svg+xml" />\n  </head>\n</html>\n',
        encoding="utf-8",
    )
    (PUBLIC / "HINT.txt").write_text(
        "Flag nằm trong CTFd lần này, nhưng như mọi khi, bạn vẫn phải tự làm việc để lấy nó.\n"
        "Không cần brute-force; các công cụ dirbuster sẽ không giúp gì ở đây.\n",
        encoding="utf-8",
    )
    print(FLAG)


if __name__ == "__main__":
    main()
