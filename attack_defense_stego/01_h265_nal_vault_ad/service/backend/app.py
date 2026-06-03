import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template_string, request, session

from stego import StegoError, embed_secret, extract_secret, find_nals, nal_type


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
EVIDENCE_DIR = DATA_DIR / "evidence"
PREVIEW_DIR = DATA_DIR / "previews"
FRONT_INDEX_PATH = Path(__file__).resolve().parents[1] / "front" / "index.html"
FRONT_LOGIN_PATH = Path(__file__).resolve().parents[1] / "front" / "login.html"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
DATABASE_URL = os.environ.get("DATABASE_URL")
SQLITE_FILE = DATA_DIR / "evidence.db"
ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,48}$")
SHARE_RE = re.compile(r"^[a-f0-9]{16}$")

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET") or secrets.token_hex(32)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


_OPERATOR_ENV = {
    "triage": os.environ.get("TRIAGE_PASSWORD"),
    "archive": os.environ.get("ARCHIVE_PASSWORD"),
}
OPERATORS = {name: password for name, password in _OPERATOR_ENV.items() if password}

CAMERAS = {
    "lobby_cam_01": {
        "name": "Camera sảnh 01",
        "zone": "Sảnh chính",
        "codec": "HEVC/H.265",
        "retention": "14 ngày",
        "public_redaction": "che mặt + thẻ nhân viên",
    },
    "parking_gate_02": {
        "name": "Camera cổng xe 02",
        "zone": "Cổng bãi xe",
        "codec": "HEVC/H.265",
        "retention": "7 ngày",
        "public_redaction": "che biển số + khuôn mặt",
    },
    "evidence_upload": {
        "name": "Luồng chứng cứ tải lên",
        "zone": "Nguồn ngoài hệ thống",
        "codec": "HEVC/H.265",
        "retention": "duyệt thủ công",
        "public_redaction": "theo lựa chọn người vận hành",
    },
}

THUMBNAIL_BY_SOURCE = {
    "lobby_cam_01": ASSET_DIR / "thumb_lobby_cam_01.jpg",
    "parking_gate_02": ASSET_DIR / "thumb_parking_gate_02.jpg",
    "evidence_upload": ASSET_DIR / "thumb_evidence_upload.jpg",
}


INDEX_HTML = r"""
<!doctype html>
<html lang="vi">
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
    .feed {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 14px;
    }
    .feed pre { min-height: 160px; margin-top: 0; }
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
        <div class="muted">Tiếp nhận vụ việc CCTV, xác minh chuỗi lưu giữ, duyệt bản che thông tin và đánh dấu chứng cứ HEVC.</div>
      </div>
      <div class="status"><span class="dot"></span> Dịch vụ đang hoạt động</div>
    </div>
  </header>
  <main class="wrap">
    <section class="wide" style="margin-top:0;margin-bottom:18px">
      <h2>Bảng điều khiển vận hành</h2>
      <p class="muted">Nhân sự vận hành rà soát nguồn camera và xuất bản liên kết chứng cứ đã che thông tin. Checker vẫn có thể kiểm tra dịch vụ qua API trực tiếp.</p>
      <form id="loginForm">
        <div class="row">
          <div>
            <label for="loginUser">Tài khoản vận hành</label>
            <input id="loginUser" autocomplete="off" placeholder="triage">
          </div>
          <div>
            <label for="loginPass">Mật khẩu</label>
            <input id="loginPass" autocomplete="off" type="password" placeholder="Mật khẩu operator">
          </div>
        </div>
        <button type="submit">Mở phiên vận hành</button>
      </form>
      <div class="feed">
        <pre id="operatorOut">Chưa có phiên vận hành.</pre>
        <pre id="cameraOut">Đang tải danh sách camera...</pre>
      </div>
    </section>

    <div class="grid">
      <section>
        <h2>Nhập chứng cứ CCTV</h2>
        <p class="muted">Nhập luồng camera vào kho chứng cứ. Cổng sẽ gắn dấu chuỗi lưu giữ nội bộ và chuẩn bị bản chia sẻ công khai đã che thông tin.</p>
        <form id="storeForm">
          <div class="row">
            <div>
              <label for="storeId">Case ID</label>
              <input id="storeId" autocomplete="off" placeholder="case_2026_001" required>
            </div>
            <div>
              <label for="storeToken">Operator Token</label>
              <input id="storeToken" autocomplete="off" placeholder="ít nhất 8 ký tự" required>
            </div>
          </div>
        <label for="storeSource">CCTV Source</label>
          <select id="storeSource"></select>
          <button type="submit">Nhập chứng cứ</button>
        </form>
        <pre id="storeOut">Chưa có yêu cầu.</pre>
      </section>

      <section>
        <h2>Xác minh dấu chuỗi lưu giữ</h2>
        <p class="muted">Luồng xác minh hợp lệ cần đúng <code>Case ID</code> và <code>Operator Token</code>.</p>
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
          <button type="submit">Xác minh dấu</button>
        </form>
        <pre id="readOut">Chưa có yêu cầu.</pre>
      </section>
    </div>

    <section class="wide">
      <h2>Bản xem trước công khai đã che thông tin</h2>
      <p class="muted">Bản xem trước công khai là luồng CCTV đã che thông tin và vẫn phát được. Backend giữ metadata thời gian trong khi thay nội dung gốc bằng luồng camera đã xử lý.</p>
      <div class="routes">
        <div class="route"><strong>Health</strong><code>GET /health</code></div>
        <div class="route"><strong>Store</strong><code>POST /api/store</code></div>
        <div class="route"><strong>Read</strong><code>POST /api/read</code></div>
        <div class="route"><strong>Recent cases</strong><code>GET /api/cases</code></div>
        <div class="route"><strong>Case page</strong><code>GET /case/&lt;id&gt;</code></div>
        <div class="route"><strong>Share page</strong><code>GET /share/&lt;share&gt;</code></div>
        <div class="route"><strong>Preview</strong><code>GET /api/cases/&lt;id&gt;/redacted-preview.h265</code></div>
      </div>
      <p class="muted" style="margin-top:14px">Backend giả định bản xem trước là an toàn vì chi tiết CCTV nhìn thấy đã được che.</p>
      <div class="feed">
        <pre id="caseOut">Đang tải vụ việc công khai...</pre>
        <pre id="auditOut">Đang tải nhật ký kiểm toán...</pre>
      </div>
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
      const data = await res.json().catch(() => ({ok: false, error: "json không hợp lệ"}));
      return {status: res.status, data};
    }

    async function getJson(path) {
      const res = await fetch(path);
      const data = await res.json().catch(() => ({ok: false, error: "json không hợp lệ"}));
      return {status: res.status, data};
    }

    async function refreshPortal() {
      const me = await getJson("/api/operator/me");
      document.getElementById("operatorOut").textContent = json(me);

      const cameras = await getJson("/api/cameras");
      document.getElementById("cameraOut").textContent = json(cameras);
      const select = document.getElementById("storeSource");
      select.innerHTML = "";
      for (const camera of cameras.data.cameras || []) {
        const option = document.createElement("option");
        option.value = camera.id;
        option.textContent = `${camera.name} (${camera.zone})`;
        select.appendChild(option);
      }

      document.getElementById("caseOut").textContent = json(await getJson("/api/cases"));
      document.getElementById("auditOut").textContent = json(await getJson("/api/audit"));
    }

    document.getElementById("loginForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const result = await postJson("/api/operator/login", {
        username: document.getElementById("loginUser").value,
        password: document.getElementById("loginPass").value,
      });
      document.getElementById("operatorOut").textContent = json(result);
      await refreshPortal();
    });

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
        await refreshPortal();
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

    refreshPortal();
  </script>
</body>
</html>
"""


CASE_HTML = r"""
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hồ sơ chứng cứ {{ item_id }}</title>
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
    .preview-thumb {
      width: 100%;
      max-height: 360px;
      margin: 12px 0 4px;
      border: 1px solid #d8dfeb;
      border-radius: 8px;
      object-fit: cover;
      background: #e5e7eb;
    }
  </style>
</head>
<body>
  <main>
    <h1>Hồ sơ chứng cứ: {{ item_id }}</h1>
    <img class="preview-thumb" src="{{ public_case.thumbnail_url }}" alt="">
    <p>Nguồn: <code>{{ public_case.camera }}</code> tại <code>{{ public_case.zone }}</code></p>
    <p>Trạng thái: <code>{{ public_case.status }}</code> · Kiểu che: <code>{{ public_case.redaction_profile }}</code></p>
    <p>Bản xem trước công khai dùng luồng CCTV HEVC đã xử lý. Tệp này dùng để rà soát cấu trúc mà không công khai luồng chứng cứ gốc.</p>
    <p>Endpoint bản xem trước: <code>/api/cases/{{ item_id }}/redacted-preview.h265</code></p>
    <a href="/api/cases/{{ item_id }}/redacted-preview.h265">Tải bản xem trước đã che</a>
    <a href="{{ public_case.manifest_url }}" style="margin-left:8px;background:#334155">Mở manifest</a>
  </main>
</body>
</html>
"""


def _is_postgres() -> bool:
    return bool(DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")))


def _connect():
    if _is_postgres():
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    conn = sqlite3.connect(SQLITE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _execute(conn, query: str, params: tuple = ()):
    if _is_postgres():
        query = query.replace("?", "%s")
    return conn.execute(query, params)


def _init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    last_error = None
    for _ in range(30):
        try:
            with _connect() as conn:
                id_type = "SERIAL PRIMARY KEY" if _is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cases (
                        id TEXT PRIMARY KEY,
                        token_hash TEXT NOT NULL,
                        share_id TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        source TEXT NOT NULL,
                        operator TEXT NOT NULL,
                        status TEXT NOT NULL,
                        redaction_profile TEXT NOT NULL,
                        evidence_size INTEGER NOT NULL
                    )
                    """
                )
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS audit (
                        id {id_type},
                        ts INTEGER NOT NULL,
                        event TEXT NOT NULL,
                        case_id TEXT NOT NULL,
                        operator TEXT NOT NULL,
                        remote TEXT NOT NULL,
                        fields TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS preview_jobs (
                        id {id_type},
                        case_id TEXT NOT NULL UNIQUE,
                        status TEXT NOT NULL,
                        attempts INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL,
                        error TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
                return
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"database did not become ready: {last_error!r}")


def _load_meta() -> dict:
    with _connect() as conn:
        rows = _execute(conn, "SELECT * FROM cases").fetchall()
    return {row["id"]: dict(row) for row in rows}


def _save_meta(meta: dict) -> None:
    with _connect() as conn:
        for item_id, data in meta.items():
            _execute(
                conn,
                """
                INSERT INTO cases (
                    id, token_hash, share_id, created_at, source, operator,
                    status, redaction_profile, evidence_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    token_hash=excluded.token_hash,
                    share_id=excluded.share_id,
                    created_at=excluded.created_at,
                    source=excluded.source,
                    operator=excluded.operator,
                    status=excluded.status,
                    redaction_profile=excluded.redaction_profile,
                    evidence_size=excluded.evidence_size
                """,
                (
                    item_id,
                    data["token_hash"],
                    data["share_id"],
                    int(data["created_at"]),
                    data["source"],
                    data.get("operator", "api-client"),
                    data.get("status", "redacted"),
                    data.get("redaction_profile", "standard-public"),
                    int(data.get("evidence_size", 0)),
                ),
            )
        conn.commit()


def _enqueue_preview_job(item_id: str) -> None:
    now = int(time.time())
    with _connect() as conn:
        _execute(
            conn,
            """
            INSERT INTO preview_jobs (case_id, status, attempts, updated_at, error)
            VALUES (?, 'queued', 0, ?, '')
            ON CONFLICT(case_id) DO UPDATE SET
                status='queued',
                updated_at=excluded.updated_at,
                error=''
            """,
            (item_id, now),
        )
        conn.commit()


def _set_preview_job(item_id: str, status: str, error: str = "") -> None:
    now = int(time.time())
    with _connect() as conn:
        _execute(
            conn,
            """
            INSERT INTO preview_jobs (case_id, status, attempts, updated_at, error)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                status=excluded.status,
                attempts=preview_jobs.attempts + 1,
                updated_at=excluded.updated_at,
                error=excluded.error
            """,
            (item_id, status, now, error[:240]),
        )
        conn.commit()


def _preview_job(item_id: str) -> dict:
    with _connect() as conn:
        row = _execute(
            conn,
            "SELECT case_id, status, attempts, updated_at, error FROM preview_jobs WHERE case_id = ?",
            (item_id,),
        ).fetchone()
    return dict(row) if row else {"case_id": item_id, "status": "missing", "attempts": 0, "updated_at": 0, "error": ""}


def _audit(event: str, item_id: str = "-", **fields) -> None:
    record = {
        "ts": int(time.time()),
        "event": event,
        "case_id": item_id,
        "operator": session.get("operator", "api-client"),
        "remote": request.headers.get("X-Forwarded-For", request.remote_addr or "-"),
    }
    with _connect() as conn:
        _execute(
            conn,
            "INSERT INTO audit (ts, event, case_id, operator, remote, fields) VALUES (?, ?, ?, ?, ?, ?)",
            (
                record["ts"],
                record["event"],
                record["case_id"],
                record["operator"],
                record["remote"],
                json.dumps(fields, sort_keys=True),
            ),
        )
        conn.commit()


def _recent_audit(limit: int = 30) -> list[dict]:
    with _connect() as conn:
        rows = _execute(conn, "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    events = []
    for row in reversed(rows):
        event = dict(row)
        fields = json.loads(event.pop("fields") or "{}")
        event.update(fields)
        events.append(event)
    return events


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _byte_stream(seed: str, label: bytes):
    counter = 0
    seed_bytes = seed.encode("utf-8")
    while True:
        block = hashlib.sha256(label + seed_bytes + counter.to_bytes(4, "big")).digest()
        counter += 1
        for value in block:
            yield value


def _masked_hex(value: str, seed: str, label: bytes) -> str:
    stream = _byte_stream(seed, label)
    return bytes(byte ^ next(stream) for byte in value.encode("utf-8")).hex()


def _extract_case_secret(item_id: str) -> str:
    return extract_secret((EVIDENCE_DIR / f"{item_id}.h265").read_bytes(), seed=item_id)


def _thumbnail_body(source: str) -> bytes:
    path = THUMBNAIL_BY_SOURCE.get(source) or THUMBNAIL_BY_SOURCE["lobby_cam_01"]
    try:
        return path.read_bytes()
    except OSError:
        return b"\xff\xd8\xff\xd9"


def _valid_id(value: str) -> bool:
    return isinstance(value, str) and bool(ID_RE.fullmatch(value))


def _generated_marker(item_id: str, token: str, source: str) -> str:
    seed = f"{item_id}:{token}:{source}".encode("utf-8")
    return "CUSTODY-" + hashlib.sha256(seed).hexdigest()[:24]


def _share_id(item_id: str, token_hash: str) -> str:
    return hashlib.sha256(f"share:{item_id}:{token_hash}".encode("utf-8")).hexdigest()[:16]


def _case_digest(item_id: str) -> bytes:
    return hashlib.sha256(f"public-case-profile:{item_id}".encode("utf-8")).digest()


def _evidence_reference(item_id: str) -> str:
    digest = _case_digest(item_id)
    year = 2026
    sequence = int.from_bytes(digest[:2], "big") % 9000 + 1000
    suffix = digest[2:4].hex().upper()
    return f"EV-{year}-{sequence}-{suffix}"


def _display_operator(operator: str) -> str:
    names = {
        "checker_bot": "Tự động tiếp nhận",
        "api-client": "Tiếp nhận qua API",
        "triage": "Điều phối viên",
        "archive": "Kho chứng cứ",
    }
    return names.get(operator, operator)


def _incident_profile(item_id: str, source: str) -> dict:
    digest = _case_digest(item_id)
    incident_by_source = {
        "lobby_cam_01": ["Rà soát ra vào", "Sự việc tại sảnh", "Xác minh khách"],
        "parking_gate_02": ["Rà soát cổng xe", "Che biển số", "Sự việc bãi xe"],
        "evidence_upload": ["Rà soát chứng cứ ngoài", "Tiếp nhận thủ công", "Video được nộp"],
    }
    severity = ["thấp", "trung bình", "cao"][digest[4] % 3]
    offset = digest[5] % 18
    duration = 6 + (digest[6] % 19)
    base_ts = 1764579600  # 2025-12-01 09:00:00 UTC, stable synthetic timeline.
    start_ts = base_ts + offset * 3600 + (digest[7] % 45) * 60
    return {
        "evidence_ref": _evidence_reference(item_id),
        "incident_type": incident_by_source.get(source, ["Evidence review"])[digest[3] % 3],
        "severity": severity,
        "capture_start": start_ts,
        "capture_end": start_ts + duration * 60,
    }


def _public_case(item_id: str, data: dict) -> dict:
    share_id = data.get("share_id") or _share_id(item_id, data.get("token_hash", ""))
    source = data.get("source", "unknown")
    camera = CAMERAS.get(source, {"name": source, "zone": "unknown", "codec": "HEVC/H.265"})
    job = _preview_job(item_id)
    profile = _incident_profile(item_id, source)
    return {
        "id": item_id,
        **profile,
        "source": source,
        "camera": camera.get("name", source),
        "zone": camera.get("zone", "unknown"),
        "status": data.get("status", "redacted"),
        "redaction_profile": data.get("redaction_profile", "standard-public"),
        "case_url": f"/case/{item_id}",
        "share_url": f"/share/{share_id}",
        "manifest_url": f"/api/share/{share_id}/manifest.json",
        "preview_url": f"/api/cases/{item_id}/redacted-preview.h265",
        "thumbnail_url": f"/api/cases/{item_id}/thumbnail.jpg",
        "preview_job": job["status"],
        "created_at": data.get("created_at", 0),
        "reviewed_by": _display_operator(data.get("operator", "api-client")),
    }


def _case_by_share(share_id: str) -> tuple[str, dict] | tuple[None, None]:
    for item_id, data in _load_meta().items():
        current = data.get("share_id") or _share_id(item_id, data.get("token_hash", ""))
        if current == share_id:
            return item_id, data
    return None, None


def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        # Vulnerability: the preview is playable because it keeps redacted VCL
        # frames, but it also preserves AUD timing metadata carrying the marker.
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)


def _render_preview(item_id: str) -> Path:
    source_path = EVIDENCE_DIR / f"{item_id}.h265"
    preview_path = PREVIEW_DIR / f"{item_id}_redacted_preview.h265"
    bitstream = source_path.read_bytes()
    preview_path.write_bytes(_preview_bitstream(bitstream))
    _set_preview_job(item_id, "ready")
    return preview_path


def _portal_index_html() -> str:
    try:
        return FRONT_INDEX_PATH.read_text(encoding="utf-8")
    except OSError:
        return INDEX_HTML


def _front_html(path: Path, fallback: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return fallback


_init_db()


@app.get("/")
def index():
    return render_template_string(_portal_index_html())


@app.get("/login")
def login_page():
    return render_template_string(_front_html(FRONT_LOGIN_PATH, _portal_index_html()))


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.post("/api/operator/login")
def operator_login():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "")
    password = body.get("password", "")
    if not isinstance(username, str) or OPERATORS.get(username) != password:
        _audit("operator_login_failed", username=str(username)[:48])
        return jsonify(ok=False, error="invalid operator credentials"), 403
    session["operator"] = username
    _audit("operator_login", username=username)
    return jsonify(ok=True, operator=username)


@app.post("/api/operator/logout")
def operator_logout():
    operator = session.pop("operator", None)
    _audit("operator_logout", operator=operator or "-")
    return jsonify(ok=True)


@app.get("/api/operator/me")
def operator_me():
    operator = session.get("operator")
    return jsonify(ok=True, authenticated=operator is not None, operator=operator)


@app.get("/api/cameras")
def cameras():
    return jsonify(
        ok=True,
        cameras=[
            {"id": camera_id, **data}
            for camera_id, data in CAMERAS.items()
        ],
    )


@app.get("/api/audit")
def audit():
    return jsonify(ok=True, events=_recent_audit())


@app.get("/api/preview-jobs")
def preview_jobs():
    with _connect() as conn:
        rows = _execute(
            conn,
            "SELECT case_id, status, attempts, updated_at, error FROM preview_jobs ORDER BY updated_at DESC LIMIT 50",
        ).fetchall()
    return jsonify(ok=True, jobs=[dict(row) for row in rows])


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
    if not isinstance(source, str) or source not in CAMERAS:
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
    token_hash = _hash_token(token)
    share_id = _share_id(item_id, token_hash)
    meta[item_id] = {
        "token_hash": token_hash,
        "share_id": share_id,
        "created_at": int(time.time()),
        "source": source,
        "operator": session.get("operator", "checker_bot"),
        "status": "redacted",
        "redaction_profile": CAMERAS[source]["public_redaction"],
        "evidence_size": len(bitstream),
    }
    _save_meta(meta)
    _enqueue_preview_job(item_id)
    _audit("case_imported", item_id, source=source, share_id=share_id)
    return jsonify(
        ok=True,
        id=item_id,
        source=source,
        filename=f"{item_id}.h265",
        case_url=f"/case/{item_id}",
        share_url=f"/share/{share_id}",
        manifest_url=f"/api/share/{share_id}/manifest.json",
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
        secret = _extract_case_secret(item_id)
    except (OSError, StegoError) as exc:
        return jsonify(ok=False, error=str(exc)), 500

    _audit("marker_verified", item_id)
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

    _audit("carrier_downloaded", item_id)
    return Response(
        data,
        mimetype="video/H265",
        headers={"Content-Disposition": f'attachment; filename="{item_id}.h265"'},
    )


@app.get("/api/cases")
def public_cases():
    meta = _load_meta()
    items = [_public_case(item_id, data) for item_id, data in sorted(meta.items())]
    return jsonify(ok=True, items=items)


@app.get("/case/<item_id>")
def case_page(item_id: str):
    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    meta = _load_meta()
    if item_id not in meta:
        return jsonify(ok=False, error="not found"), 404
    return render_template_string(CASE_HTML, item_id=item_id, public_case=_public_case(item_id, meta[item_id]))


@app.get("/share/<share_id>")
def share_page(share_id: str):
    if not SHARE_RE.fullmatch(share_id):
        return jsonify(ok=False, error="bad share id"), 400
    item_id, data = _case_by_share(share_id)
    if item_id is None:
        return jsonify(ok=False, error="not found"), 404
    return render_template_string(CASE_HTML, item_id=item_id, public_case=_public_case(item_id, data))


@app.get("/api/share/<share_id>/manifest.json")
def share_manifest(share_id: str):
    if not SHARE_RE.fullmatch(share_id):
        return jsonify(ok=False, error="bad share id"), 400
    item_id, data = _case_by_share(share_id)
    if item_id is None:
        return jsonify(ok=False, error="not found"), 404
    public_case = _public_case(item_id, data)
    return jsonify(
        ok=True,
        manifest={
            "case": public_case,
            "codec": "HEVC/H.265 Annex-B",
            "public_artifact": "redacted-preview",
            "chain_of_custody": "internal marker stored in protected evidence carrier",
            "note": "Visible CCTV content is redacted; timing metadata is preserved for review.",
        },
    )


@app.get("/api/cases/<item_id>/diagnostics.json")
def case_diagnostics(item_id: str):
    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    meta = _load_meta()
    if item_id not in meta:
        return jsonify(ok=False, error="not found"), 404

    try:
        secret = _extract_case_secret(item_id)
    except (OSError, StegoError):
        return jsonify(ok=False, error="diagnostics unavailable"), 404

    _audit("diagnostics_downloaded", item_id)
    return jsonify(
        ok=True,
        case_id=item_id,
        diagnostic="redaction-worker-custody-sample",
        mask_label="h265-ad-diag:",
        custody_hint=_masked_hex(secret, item_id, b"h265-ad-diag:"),
    )


@app.get("/api/cases/<item_id>/thumbnail.jpg")
def case_thumbnail(item_id: str):
    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    meta = _load_meta()
    if item_id not in meta:
        return jsonify(ok=False, error="not found"), 404

    try:
        secret = _extract_case_secret(item_id)
    except (OSError, StegoError):
        return jsonify(ok=False, error="thumbnail unavailable"), 404

    _audit("thumbnail_downloaded", item_id)
    body = _thumbnail_body(meta[item_id].get("source", "lobby_cam_01"))
    return Response(
        body,
        mimetype="image/jpeg",
        headers={
            "Cache-Control": "no-store",
            "X-H265-Custody-Mask": "h265-ad-thumb:",
            "X-H265-Custody-Hint": _masked_hex(secret, item_id, b"h265-ad-thumb:"),
        },
    )


@app.get("/api/operator/cases/<item_id>/debug-marker")
def operator_debug_marker(item_id: str):
    if session.get("operator") is None:
        return jsonify(ok=False, error="operator login required"), 403
    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    if item_id not in _load_meta():
        return jsonify(ok=False, error="not found"), 404

    try:
        secret = _extract_case_secret(item_id)
    except (OSError, StegoError) as exc:
        return jsonify(ok=False, error=str(exc)), 500

    _audit("operator_debug_marker", item_id)
    return jsonify(ok=True, id=item_id, marker=secret)


@app.get("/api/cases/<item_id>/redacted-preview.h265")
def redacted_preview(item_id: str):
    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    if item_id not in _load_meta():
        return jsonify(ok=False, error="not found"), 404

    preview_path = PREVIEW_DIR / f"{item_id}_redacted_preview.h265"
    if not preview_path.exists():
        try:
            # Local fallback: Docker uses preview-worker, but direct Flask runs still work.
            preview_path = _render_preview(item_id)
        except OSError:
            _set_preview_job(item_id, "failed", "missing carrier")
            return jsonify(ok=False, error="missing carrier"), 404
        except Exception as exc:
            _set_preview_job(item_id, "failed", repr(exc))
            return jsonify(ok=False, error="preview render failed"), 500

    _audit("preview_downloaded", item_id)
    return Response(
        preview_path.read_bytes(),
        mimetype="video/H265",
        headers={"Content-Disposition": f'attachment; filename="{item_id}_redacted_preview.h265"'},
    )
