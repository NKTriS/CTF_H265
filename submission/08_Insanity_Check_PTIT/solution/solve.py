from pathlib import Path
import argparse
import re


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

MORSE_TO_TEXT = {
    ".-": "a",
    "-...": "b",
    "-.-.": "c",
    "-..": "d",
    ".": "e",
    "..-.": "f",
    "--.": "g",
    "....": "h",
    "..": "i",
    ".---": "j",
    "-.-": "k",
    ".-..": "l",
    "--": "m",
    "-.": "n",
    "---": "o",
    ".--.": "p",
    "--.-": "q",
    ".-.": "r",
    "...": "s",
    "-": "t",
    "..-": "u",
    "...-": "v",
    ".--": "w",
    "-..-": "x",
    "-.--": "y",
    "--..": "z",
    "-----": "0",
    ".----": "1",
    "..---": "2",
    "...--": "3",
    "....-": "4",
    ".....": "5",
    "-....": "6",
    "--...": "7",
    "---..": "8",
    "----.": "9",
}


def extract_blink_keyframes(svg: str) -> str:
    match = re.search(r"@keyframes\s+blink\s*\{(?P<body>.*?)\n\}", svg, re.S)
    if not match:
        raise ValueError("could not find blink keyframes")
    return match.group("body")


def parse_events(keyframes: str) -> list[tuple[float, str]]:
    events = []
    for percent, fill in re.findall(r"([0-9.]+)%\s*\{\s*fill:\s*(#[0-9A-Fa-f]{4})", keyframes):
        events.append((float(percent), fill.upper()))
    events.sort()

    compressed = []
    for percent, fill in events:
        if compressed and compressed[-1][1] == fill:
            continue
        compressed.append((percent, fill))
    return compressed


def durations_to_morse(events: list[tuple[float, str]]) -> str:
    if len(events) < 2:
        raise ValueError("not enough animation events")

    diffs = [events[i + 1][0] - events[i][0] for i in range(len(events) - 1) if events[i + 1][0] > events[i][0]]
    unit = min(diffs)
    symbols = []

    for (start, fill), (end, _) in zip(events, events[1:]):
        duration = end - start
        if duration <= 0:
            continue
        units = max(1, round(duration / unit))
        if fill == "#FFFF":
            symbols.append("-" if units >= 3 else ".")
        else:
            if units >= 7:
                symbols.append(" / ")
            elif units >= 3:
                symbols.append(" ")

    return "".join(symbols).strip()


def decode_morse(morse: str) -> str:
    words = []
    for word in morse.split("/"):
        letters = []
        for code in word.split():
            letters.append(MORSE_TO_TEXT.get(code, "?"))
        if letters:
            words.append("".join(letters))
    return " ".join(words)


def text_to_flag(text: str) -> str:
    words = text.split()
    if not words or words[0] != "blockchainptit":
        raise ValueError(f"unexpected decoded text: {text!r}")
    return "blockChainPTIT{" + "_".join(words[1:]) + "}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Decode the hidden Morse message from the SVG animation.")
    parser.add_argument("svg", nargs="?", default=PUBLIC / "favicon.svg")
    args = parser.parse_args()

    svg = Path(args.svg).read_text(encoding="utf-8")
    keyframes = extract_blink_keyframes(svg)
    events = parse_events(keyframes)
    morse = durations_to_morse(events)
    text = decode_morse(morse)
    print(text_to_flag(text))


if __name__ == "__main__":
    main()
