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
DEFAULT_TIMEOUT = int(os.environ.get("CHECKER_TIMEOUT", "5"))
MODES = {"check", "put", "get"}
SOURCES_BY_PLACE = {
    "1": "lobby_cam_01",
    "2": "parking_gate_02",
    "3": "evidence_upload",
}


def base_url(host: str, port: int) -> str:
    if host.startswith("http://") or host.startswith("https://"):
        tail = host.rsplit("/", 1)[-1]
        return f"{host.rstrip('/')}:{port}" if ":" not in tail else host.rstrip("/")
    return f"http://{host}:{port}"


def http_json(url: str, method: str = "GET", body: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_bytes(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def http_status(url: str, method: str = "GET", body: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> int:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


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


def preview_looks_hevc(data: bytes) -> bool:
    nal_types = {nal_type(nal) for nal in find_nals(data)}
    has_vcl = any(0 <= current <= 31 for current in nal_types)
    has_parameter_set = any(current in nal_types for current in (32, 33, 34))
    return has_vcl and has_parameter_set


def checker_token(item_id: str, flag: str) -> str:
    material = f"h265-ad-checker-token-v2:{item_id}:{flag}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:32]


def source_for_place(place: str | None) -> str:
    if not place:
        return secrets.choice(tuple(SOURCES_BY_PLACE.values()))
    return SOURCES_BY_PLACE.get(str(place), "lobby_cam_01")


def cquit(code: int, public: str, private: str = "") -> int:
    print(public)
    if private:
        print(private, file=sys.stderr)
    return code


def parse_port(value: str | None) -> int:
    return int(value) if value is not None else DEFAULT_PORT


def normalize_argv(argv: list[str]) -> list[str]:
    if not argv or argv[0] in MODES:
        return argv
    if len(argv) >= 2 and argv[1] in MODES:
        return [argv[1], argv[0], *argv[2:]]
    if len(argv) >= 3 and argv[1].isdigit() and argv[2] in MODES:
        return [argv[2], argv[0], argv[1], *argv[3:]]
    return argv


def cmd_check(args) -> int:
    port = parse_port(args.port)
    url = base_url(args.host, port)
    item_id = f"check_{secrets.token_hex(4)}"
    token = secrets.token_hex(12)
    secret = f"service_check_{int(time.time())}"

    health = http_json(f"{url}/health")
    if not health.get("ok"):
        return cquit(DOWN, "DOWN", "health endpoint returned ok=false")

    source = source_for_place(None)
    stored = http_json(f"{url}/api/store", "POST", {"id": item_id, "token": token, "secret": secret, "source": source})
    if not stored.get("ok"):
        return cquit(MUMBLE, "MUMBLE", "store endpoint rejected a valid marker")

    read = http_json(f"{url}/api/read", "POST", {"id": item_id, "token": token})
    if read.get("secret") != secret:
        return cquit(MUMBLE, "MUMBLE", "read endpoint returned a different marker")

    bad_read_status = http_status(f"{url}/api/read", "POST", {"id": item_id, "token": token + "_bad"})
    if bad_read_status != 403:
        return cquit(MUMBLE, "MUMBLE", "read endpoint does not reject a wrong token")

    bad_carrier_status = http_status(f"{url}/api/carrier", "POST", {"id": item_id, "token": token + "_bad"})
    if bad_carrier_status != 403:
        return cquit(MUMBLE, "MUMBLE", "carrier endpoint does not reject a wrong token")

    cases = http_json(f"{url}/api/cases")
    items = cases.get("items")
    if not cases.get("ok") or not isinstance(items, list):
        return cquit(MUMBLE, "MUMBLE", "cases endpoint returned invalid data")

    public_case = next((item for item in items if item.get("id") == item_id), None)
    if not public_case:
        return cquit(MUMBLE, "MUMBLE", "stored case is missing from public case index")

    preview_url = public_case.get("preview_url")
    if not isinstance(preview_url, str) or not preview_url.startswith("/api/cases/"):
        return cquit(MUMBLE, "MUMBLE", "public case has invalid preview url")

    preview = http_bytes(f"{url}{preview_url}")
    if not preview_looks_hevc(preview):
        return cquit(MUMBLE, "MUMBLE", "preview endpoint did not return a valid HEVC Annex-B stream")

    share_url = public_case.get("share_url")
    manifest_url = public_case.get("manifest_url")
    thumbnail_url = public_case.get("thumbnail_url")
    if not isinstance(share_url, str) or not share_url.startswith("/share/"):
        return cquit(MUMBLE, "MUMBLE", "public case has invalid share url")
    if not isinstance(manifest_url, str) or not manifest_url.startswith("/api/share/"):
        return cquit(MUMBLE, "MUMBLE", "public case has invalid manifest url")
    if not isinstance(thumbnail_url, str) or not thumbnail_url.startswith("/api/cases/"):
        return cquit(MUMBLE, "MUMBLE", "public case has invalid thumbnail url")

    manifest = http_json(f"{url}{manifest_url}")
    if not manifest.get("ok") or manifest.get("manifest", {}).get("case", {}).get("id") != item_id:
        return cquit(MUMBLE, "MUMBLE", "share manifest does not describe the stored case")

    thumbnail = http_bytes(f"{url}{thumbnail_url}")
    if not thumbnail.startswith(b"\xff\xd8") or not thumbnail.endswith(b"\xff\xd9"):
        return cquit(MUMBLE, "MUMBLE", "thumbnail endpoint did not return a JPEG envelope")

    jobs = http_json(f"{url}/api/preview-jobs")
    if not jobs.get("ok") or not isinstance(jobs.get("jobs"), list):
        return cquit(MUMBLE, "MUMBLE", "preview job endpoint returned invalid data")

    return cquit(OK, "OK")


def cmd_put(args) -> int:
    rest = list(args.rest)
    port = parse_port(args.port)
    flag_id = None

    if rest and rest[0].isdigit():
        port = int(rest.pop(0))

    place = None
    if len(rest) >= 3:
        place = rest[2]

    if len(rest) == 1:
        flag = rest[0]
    elif len(rest) >= 2:
        flag_id = rest[0]
        flag = rest[1]
    else:
        raise ValueError("put expects FLAG or FLAG_ID FLAG [VULN]")

    url = base_url(args.host, port)
    item_id = flag_id or f"flag_{int(time.time())}_{secrets.token_hex(4)}"
    token = checker_token(item_id, flag)
    source = source_for_place(place)
    stored = http_json(f"{url}/api/store", "POST", {"id": item_id, "token": token, "secret": flag, "source": source})
    if not stored.get("ok"):
        return cquit(MUMBLE, "MUMBLE", "store endpoint rejected the flag marker")

    print(item_id)
    return OK


def cmd_get(args) -> int:
    rest = list(args.rest)
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
        if isinstance(flag_id, dict) and "token" not in flag_id and isinstance(flag_id.get("id"), str):
            flag_id["token"] = checker_token(flag_id["id"], flag)
    except json.JSONDecodeError:
        flag_id = {"id": flag_id_arg, "token": checker_token(flag_id_arg, flag)}
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
    args = parser.parse_args(normalize_argv(sys.argv[1:]))
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
