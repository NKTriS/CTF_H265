import hashlib
import json
import os
import re
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template_string, request

from stego import StegoError, embed_secret, extract_secret, find_nals, nal_type


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
EVIDENCE_DIR = DATA_DIR / "evidence"
META_FILE = DATA_DIR / "metadata.json"
ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,48}$")

app = Flask(__name__)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


INDEX_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>H265 Evidence Portal</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #5d6b82;
      --line: #d8dfeb;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --code: #111827;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      background: #ffffff;
      border-bottom: 1px solid var(--line);
    }
    .wrap {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
    }
    .topbar {
      min-height: 76px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
    }
    h1 { margin: 0; font-size: 24px; letter-spacing: 0; }
    h2 { margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }
    main { padding: 28px 0 42px; }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }
    .wide { margin-top: 18px; }
    .muted { color: var(--muted); margin: 0 0 14px; }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--accent-dark);
      font-weight: 700;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: #10b981;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      margin: 14px 0 6px;
    }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      color: var(--ink);
      background: #ffffff;
      font: inherit;
      outline: none;
    }
    textarea {
      min-height: 118px;
      resize: vertical;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    input:focus, textarea:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
    }
    button {
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #ffffff;
      padding: 10px 14px;
      margin-top: 16px;
      font-weight: 800;
      cursor: pointer;
      min-height: 40px;
    }
    button:hover { background: var(--accent-dark); }
    pre {
      margin: 16px 0 0;
      min-height: 84px;
      padding: 14px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #f8fafc;
      color: var(--code);
      white-space: pre-wrap;
      word-break: break-word;
    }
    .routes {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    code {
      background: #eef2f7;
      border: 1px solid #dce3ee;
      border-radius: 5px;
      padding: 2px 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
    }
    .route {
      min-height: 58px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfdff;
    }
    .route strong { display: block; margin-bottom: 2px; }
    @media (max-width: 760px) {
      .grid, .row, .routes { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; padding: 18px 0; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div>
        <h1>H265 Evidence Portal</h1>
        <div class="muted">Redacted CCTV evidence previews with HEVC custody markers.</div>
      </div>
      <div class="status"><span class="dot"></span> Service online</div>
    </div>
  </header>
  <main class="wrap">
    <div class="grid">
      <section>
        <h2>Import CCTV Evidence</h2>
        <p class="muted">Import a camera stream into evidence storage. The portal attaches an internal custody marker automatically.</p>
        <form id="storeForm">
          <div class="row">
            <div>
              <label for="storeId">Case ID</label>
              <input id="storeId" autocomplete="off" placeholder="case_2026_001" required>
            </div>
            <div>
              <label for="storeToken">Operator Token</label>
              <input id="storeToken" autocomplete="off" placeholder="at least 8 characters" required>
            </div>
          </div>
          <label for="storeSource">CCTV Source</label>
          <select id="storeSource">
            <option value="lobby_cam_01">Lobby camera 01</option>
            <option value="parking_gate_02">Parking gate 02</option>
            <option value="evidence_upload">Uploaded evidence stream</option>
          </select>
          <button type="submit">Import evidence</button>
        </form>
        <pre id="storeOut">No request yet.</pre>
      </section>

      <section>
        <h2>Verify Custody Marker</h2>
        <p class="muted">The authorized flow requires the correct <code>case id</code> and <code>operator token</code>.</p>
        <form id="readForm">
          <div class="row">
            <div>
              <label for="readId">Case ID</label>
              <input id="readId" autocomplete="off" required>
            </div>
            <div>
              <label for="readToken">Operator Token</label>
              <input id="readToken" autocomplete="off" required>
            </div>
          </div>
          <button type="submit">Verify marker</button>
        </form>
        <pre id="readOut">No request yet.</pre>
      </section>
    </div>

    <section class="wide">
      <h2>Redacted Public Preview</h2>
      <p class="muted">Public previews are playable redacted CCTV exports. The backend keeps timing metadata while replacing the raw evidence with a sanitized camera stream.</p>
      <div class="routes">
        <div class="route"><strong>Health</strong><code>GET /health</code></div>
        <div class="route"><strong>Store</strong><code>POST /api/store</code></div>
        <div class="route"><strong>Read</strong><code>POST /api/read</code></div>
        <div class="route"><strong>Recent</strong><code>GET /api/cases</code></div>
        <div class="route"><strong>Case</strong><code>GET /case/&lt;id&gt;</code></div>
        <div class="route"><strong>Preview</strong><code>GET /api/cases/&lt;id&gt;/redacted-preview.h265</code></div>
      </div>
      <p class="muted" style="margin-top:14px">The backend assumes the preview is safe because visible CCTV detail has been redacted.</p>
    </section>
  </main>
  <script>
    const json = (value) => JSON.stringify(value, null, 2);

    async function postJson(path, body) {
      const res = await fetch(path, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({ok: false, error: "bad json"}));
      return {status: res.status, data};
    }

    document.getElementById("storeForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const body = {
        id: document.getElementById("storeId").value,
        token: document.getElementById("storeToken").value,
        source: document.getElementById("storeSource").value,
      };
      const result = await postJson("/api/store", body);
      document.getElementById("storeOut").textContent = json(result);
      if (result.data.ok) {
        document.getElementById("readId").value = body.id;
        document.getElementById("readToken").value = body.token;
      }
    });

    document.getElementById("readForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const body = {
        id: document.getElementById("readId").value,
        token: document.getElementById("readToken").value,
      };
      const result = await postJson("/api/read", body);
      document.getElementById("readOut").textContent = json(result);
    });
  </script>
</body>
</html>
"""


CASE_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Evidence case {{ item_id }}</title>
  <style>
    body {
      margin: 0;
      background: #f5f7fb;
      color: #172033;
      font: 15px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      width: min(760px, calc(100% - 32px));
      margin: 36px auto;
      background: #ffffff;
      border: 1px solid #d8dfeb;
      border-radius: 8px;
      padding: 24px;
    }
    h1 { margin: 0 0 10px; font-size: 24px; letter-spacing: 0; }
    p { color: #5d6b82; }
    code {
      background: #eef2f7;
      border: 1px solid #dce3ee;
      border-radius: 5px;
      padding: 2px 6px;
    }
    a {
      display: inline-flex;
      margin-top: 12px;
      background: #0f766e;
      color: #ffffff;
      padding: 10px 14px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 800;
    }
  </style>
</head>
<body>
  <main>
    <h1>Evidence case: {{ item_id }}</h1>
    <p>This public redacted preview uses a sanitized HEVC CCTV stream. It is intended for structure review without exposing the raw evidence stream.</p>
    <p>Preview endpoint: <code>/api/cases/{{ item_id }}/redacted-preview.h265</code></p>
    <a href="/api/cases/{{ item_id }}/redacted-preview.h265">Download redacted preview</a>
  </main>
</body>
</html>
"""


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


def _generated_marker(item_id: str, token: str, source: str) -> str:
    seed = f"{item_id}:{token}:{source}".encode("utf-8")
    return "CUSTODY-" + hashlib.sha256(seed).hexdigest()[:24]


def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        # Vulnerability: the preview is playable because it keeps redacted VCL
        # frames, but it also preserves AUD timing metadata carrying the marker.
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)


@app.get("/")
def index():
    return render_template_string(INDEX_HTML)


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.post("/api/store")
def store_secret():
    body = request.get_json(silent=True) or {}
    item_id = body.get("id", "")
    token = body.get("token", "")
    source = body.get("source", "lobby_cam_01")
    secret = body.get("secret")

    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    if not isinstance(token, str) or len(token) < 8:
        return jsonify(ok=False, error="bad token"), 400
    if not isinstance(source, str) or len(source) > 64:
        return jsonify(ok=False, error="bad source"), 400
    if secret is None:
        secret = _generated_marker(item_id, token, source)
    if not isinstance(secret, str) or len(secret.encode("utf-8")) > 2048:
        return jsonify(ok=False, error="bad secret"), 400

    try:
        bitstream = embed_secret(secret, seed=item_id)
    except StegoError as exc:
        return jsonify(ok=False, error=str(exc)), 400

    (EVIDENCE_DIR / f"{item_id}.h265").write_bytes(bitstream)
    meta = _load_meta()
    meta[item_id] = {
        "token_hash": _hash_token(token),
        "created_at": int(time.time()),
        "source": source,
    }
    _save_meta(meta)
    return jsonify(
        ok=True,
        id=item_id,
        source=source,
        filename=f"{item_id}.h265",
        case_url=f"/case/{item_id}",
        preview_url=f"/api/cases/{item_id}/redacted-preview.h265",
    )


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
        secret = extract_secret((EVIDENCE_DIR / f"{item_id}.h265").read_bytes(), seed=item_id)
    except (OSError, StegoError) as exc:
        return jsonify(ok=False, error=str(exc)), 500

    return jsonify(ok=True, secret=secret)


@app.post("/api/carrier")
def download_carrier():
    body = request.get_json(silent=True) or {}
    item_id = body.get("id", "")
    token = body.get("token", "")

    if not _valid_id(item_id) or not isinstance(token, str):
        return jsonify(ok=False, error="bad request"), 400

    meta = _load_meta()
    if item_id not in meta or meta[item_id].get("token_hash") != _hash_token(token):
        return jsonify(ok=False, error="forbidden"), 403

    path = EVIDENCE_DIR / f"{item_id}.h265"
    try:
        data = path.read_bytes()
    except OSError:
        return jsonify(ok=False, error="missing carrier"), 404

    return Response(
        data,
        mimetype="video/H265",
        headers={"Content-Disposition": f'attachment; filename="{item_id}.h265"'},
    )


@app.get("/api/cases")
def public_cases():
    meta = _load_meta()
    items = [
        {
            "id": item_id,
            "source": data.get("source", "unknown"),
            "case_url": f"/case/{item_id}",
            "preview_url": f"/api/cases/{item_id}/redacted-preview.h265",
            "created_at": data.get("created_at", 0),
        }
        for item_id, data in sorted(meta.items())
    ]
    return jsonify(ok=True, items=items)


@app.get("/case/<item_id>")
def case_page(item_id: str):
    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    if item_id not in _load_meta():
        return jsonify(ok=False, error="not found"), 404
    return render_template_string(CASE_HTML, item_id=item_id)


@app.get("/api/cases/<item_id>/redacted-preview.h265")
def redacted_preview(item_id: str):
    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    if item_id not in _load_meta():
        return jsonify(ok=False, error="not found"), 404

    try:
        bitstream = (EVIDENCE_DIR / f"{item_id}.h265").read_bytes()
    except OSError:
        return jsonify(ok=False, error="missing carrier"), 404

    preview = _preview_bitstream(bitstream)
    return Response(
        preview,
        mimetype="video/H265",
        headers={"Content-Disposition": f'attachment; filename="{item_id}_redacted_preview.h265"'},
    )
