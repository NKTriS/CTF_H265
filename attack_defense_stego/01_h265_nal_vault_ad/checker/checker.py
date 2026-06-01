#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request


OK = 101
CORRUPT = 102
MUMBLE = 103
DOWN = 104
CHECK_FAILED = 110
DEFAULT_PORT = int(os.environ.get("SERVICE_PORT", "8000"))


def base_url(host: str, port: int) -> str:
    if host.startswith("http://") or host.startswith("https://"):
        tail = host.rsplit("/", 1)[-1]
        return f"{host.rstrip('/')}:{port}" if ":" not in tail else host.rstrip("/")
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


def deterministic_token(flag_id: str) -> str:
    return hashlib.sha256(f"h265-ad-checker-token:{flag_id}".encode("utf-8")).hexdigest()[:32]


def cquit(code: int, public: str, private: str = "") -> int:
    print(public)
    if private:
        print(private, file=sys.stderr)
    return code


def parse_port(value: str | None) -> int:
    return int(value) if value is not None else DEFAULT_PORT


def cmd_check(args) -> int:
    port = parse_port(args.port)
    url = base_url(args.host, port)
    item_id = f"check_{secrets.token_hex(4)}"
    token = secrets.token_hex(12)
    secret = f"service_check_{int(time.time())}"

    health = http_json(f"{url}/health")
    if not health.get("ok"):
        return cquit(DOWN, "DOWN", "health endpoint returned ok=false")

    stored = http_json(f"{url}/api/store", "POST", {"id": item_id, "token": token, "secret": secret})
    if not stored.get("ok"):
        return cquit(MUMBLE, "MUMBLE", "store endpoint rejected a valid marker")

    read = http_json(f"{url}/api/read", "POST", {"id": item_id, "token": token})
    if read.get("secret") != secret:
        return cquit(MUMBLE, "MUMBLE", "read endpoint returned a different marker")

    return cquit(OK, "OK")


def cmd_put(args) -> int:
    rest = args.rest
    port = parse_port(args.port)
    flag_id = None

    if rest and rest[0].isdigit():
        port = int(rest.pop(0))

    if len(rest) == 1:
        flag = rest[0]
    elif len(rest) >= 2:
        flag_id = rest[0]
        flag = rest[1]
    else:
        raise ValueError("put expects FLAG or FLAG_ID FLAG [VULN]")

    url = base_url(args.host, port)
    item_id = flag_id or f"flag_{int(time.time())}_{secrets.token_hex(4)}"
    token = deterministic_token(item_id) if flag_id else secrets.token_hex(16)
    stored = http_json(f"{url}/api/store", "POST", {"id": item_id, "token": token, "secret": flag})
    if not stored.get("ok"):
        return cquit(MUMBLE, "MUMBLE", "store endpoint rejected the flag marker")

    print(json.dumps({"id": item_id, "token": token}, sort_keys=True))
    return OK


def cmd_get(args) -> int:
    rest = args.rest
    port = parse_port(args.port)

    if rest and rest[0].isdigit():
        port = int(rest.pop(0))

    if len(rest) < 2:
        raise ValueError("get expects FLAG_ID FLAG [VULN]")

    flag_id_arg = rest[0]
    flag = rest[1]
    url = base_url(args.host, port)
    try:
        flag_id = json.loads(flag_id_arg)
    except json.JSONDecodeError:
        flag_id = {"id": flag_id_arg, "token": deterministic_token(flag_id_arg)}
    read = http_json(f"{url}/api/read", "POST", flag_id)
    if read.get("secret") != flag:
        return cquit(CORRUPT, "CORRUPT", "stored marker does not match the expected flag")
    return cquit(OK, "OK")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="H265 Evidence Portal Hackerdom-style checker")
    sub = parser.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("check")
    p.add_argument("host")
    p.add_argument("port", nargs="?")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("put")
    p.add_argument("host")
    p.add_argument("--port")
    p.add_argument("rest", nargs="+", help="[PORT] FLAG or FLAG_ID FLAG [VULN]")
    p.set_defaults(func=cmd_put)

    p = sub.add_parser("get")
    p.add_argument("host")
    p.add_argument("--port")
    p.add_argument("rest", nargs="+", help="[PORT] FLAG_ID FLAG [VULN]")
    p.set_defaults(func=cmd_get)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except urllib.error.HTTPError as exc:
        if 500 <= exc.code <= 599:
            return cquit(DOWN, "DOWN", f"http {exc.code}")
        return cquit(MUMBLE, "MUMBLE", f"http {exc.code}")
    except (urllib.error.URLError, TimeoutError) as exc:
        return cquit(DOWN, "DOWN", str(exc))
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return cquit(MUMBLE, "MUMBLE", str(exc))
    except Exception as exc:
        return cquit(CHECK_FAILED, "CHECK FAILED", repr(exc))


if __name__ == "__main__":
    sys.exit(main())
