import hashlib
import json
import os
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from stego import StegoError, embed_secret, extract_secret


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
VAULT_DIR = DATA_DIR / "vault"
META_FILE = DATA_DIR / "metadata.json"
ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,48}$")

app = Flask(__name__)
VAULT_DIR.mkdir(parents=True, exist_ok=True)


def _load_meta() -> dict:
    if not META_FILE.exists():
        return {}
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_meta(meta: dict) -> None:
    tmp = META_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, sort_keys=True), encoding="utf-8")
    tmp.replace(META_FILE)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _valid_id(value: str) -> bool:
    return isinstance(value, str) and bool(ID_RE.fullmatch(value))


@app.get("/")
def index():
    return jsonify(
        service="H265 NAL Vault",
        routes=["/health", "/api/store", "/api/read"],
    )


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.post("/api/store")
def store_secret():
    body = request.get_json(silent=True) or {}
    item_id = body.get("id", "")
    token = body.get("token", "")
    secret = body.get("secret", "")

    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    if not isinstance(token, str) or len(token) < 8:
        return jsonify(ok=False, error="bad token"), 400
    if not isinstance(secret, str) or len(secret.encode("utf-8")) > 2048:
        return jsonify(ok=False, error="bad secret"), 400

    try:
        bitstream = embed_secret(secret, seed=item_id + ":" + token)
    except StegoError as exc:
        return jsonify(ok=False, error=str(exc)), 400

    (VAULT_DIR / f"{item_id}.h265").write_bytes(bitstream)
    meta = _load_meta()
    meta[item_id] = {"token_hash": _hash_token(token)}
    _save_meta(meta)
    return jsonify(ok=True, id=item_id, filename=f"{item_id}.h265")


@app.post("/api/read")
def read_secret():
    body = request.get_json(silent=True) or {}
    item_id = body.get("id", "")
    token = body.get("token", "")

    if not _valid_id(item_id) or not isinstance(token, str):
        return jsonify(ok=False, error="bad request"), 400

    meta = _load_meta()
    if item_id not in meta or meta[item_id].get("token_hash") != _hash_token(token):
        return jsonify(ok=False, error="forbidden"), 403

    try:
        secret = extract_secret((VAULT_DIR / f"{item_id}.h265").read_bytes())
    except (OSError, StegoError) as exc:
        return jsonify(ok=False, error=str(exc)), 500

    return jsonify(ok=True, secret=secret)


@app.get("/api/debug/list")
def debug_list():
    # Vulnerability: this production route leaks every stored carrier filename.
    files = sorted(path.name for path in VAULT_DIR.glob("*.h265"))
    return jsonify(ok=True, files=files)


@app.get("/api/debug/file/<path:filename>")
def debug_file(filename: str):
    # Vulnerability: unauthenticated users can download raw stego carriers.
    return send_from_directory(VAULT_DIR, filename, mimetype="video/H265")
