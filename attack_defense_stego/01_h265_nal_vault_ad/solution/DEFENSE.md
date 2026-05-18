# H265 NAL Vault AD - Defense Writeup

## 1. Muc tieu defense

Muc tieu cua defense khong phai la xoa co che giau tin. Checker van can
`/api/store` de dat flag va `/api/read` de doc lai flag bang token. Diem can va
la hai endpoint debug vi chung cho tai carrier `.h265` ma khong can token.

## 2. Anh chup 1 - chung minh truoc khi va la bi leak

Truoc khi sua, chay service va dat mot flag mau:

```bash
cd attack_defense_stego/01_h265_nal_vault_ad
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Lenh nay se tra ve JSON co `id` va `token`. Sau do chay exploit:

```bash
python checker/checker.py exploit 127.0.0.1 8000
```

Neu service chua va, output se co flag:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Anh can chup:

```text
solution/screenshots/defense-01-before-exploit-leaks-flag.png
```

Noi dung anh nen thay ro:

- Lenh `python checker/checker.py exploit 127.0.0.1 8000`.
- Output co flag.
- Neu co the, chup kem ket qua `/api/debug/list` tra ve file `.h265`.

## 3. Xac dinh dung diem can sua

Mo file:

```text
service/app.py
```

Doan code nguy hiem:

```python
@app.get("/api/debug/list")
def debug_list():
    files = sorted(path.name for path in VAULT_DIR.glob("*.h265"))
    return jsonify(ok=True, files=files)


@app.get("/api/debug/file/<path:filename>")
def debug_file(filename: str):
    return send_from_directory(VAULT_DIR, filename, mimetype="video/H265")
```

Ly do nguy hiem:

- `/api/debug/list` lam lo ten carrier cua cac flag dang luu.
- `/api/debug/file/<filename>` cho tai raw HEVC carrier ma khong can token.
- Token trong `/api/read` bi vo nghia, vi attacker doc truc tiep kenh AUD tu file
  `.h265`.

Anh can chup:

```text
solution/screenshots/defense-02-vulnerable-code.png
```

Anh nen chup man hinh editor dang mo dung hai route debug tren.

## 4. Cach va nhanh nhat

Xoa import `send_from_directory` vi sau khi xoa debug route se khong dung nua:

```python
from flask import Flask, jsonify, request
```

Sau do xoa hoan toan hai route:

```python
@app.get("/api/debug/list")
def debug_list():
    ...

@app.get("/api/debug/file/<path:filename>")
def debug_file(filename: str):
    ...
```

Patch mau da co san:

```bash
git apply solution/defense.patch
```

Neu khong dung git, co the sua tay theo noi dung trong `solution/defense.patch`.

Anh can chup:

```text
solution/screenshots/defense-03-patched-code.png
```

Anh nen thay ro file `service/app.py` sau khi khong con route `/api/debug/list`
va `/api/debug/file/<filename>`.

## 5. Rebuild va restart service

Sau khi sua code, rebuild container de service chay ban moi:

```bash
cd service
docker compose down
docker compose up --build -d
```

Kiem tra container con song:

```bash
curl http://127.0.0.1:8000/health
```

Ket qua can co:

```json
{"ok":true}
```

Anh can chup:

```text
solution/screenshots/defense-04-service-health-after-patch.png
```

## 6. Kiem tra defense khong lam hong checker

Day la buoc quan trong trong attack/defense. Neu chi chan exploit nhung lam hong
`put/get` thi service van bi mat diem availability.

Chay checker tong quat:

```bash
cd attack_defense_stego/01_h265_nal_vault_ad
python checker/checker.py check 127.0.0.1 8000
```

Output mong doi:

```text
OK
```

Kiem tra ro hon bang `put` va `get`:

```bash
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Lenh tren in ra JSON, vi du:

```json
{"id":"flag_1710000000_abcd1234","token":"0123456789abcdef"}
```

Dung lai JSON do de doc flag:

```bash
python checker/checker.py get 127.0.0.1 8000 '{"id":"flag_1710000000_abcd1234","token":"0123456789abcdef"}' 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Output mong doi:

```text
OK
```

Anh can chup:

```text
solution/screenshots/defense-05-checker-still-ok.png
```

Anh nen thay ro checker `check` hoac cap `put/get` deu tra ve `OK`.

## 7. Chung minh exploit da bi chan

Thu goi debug list:

```bash
curl -i http://127.0.0.1:8000/api/debug/list
```

Sau khi va dung, ket qua phai la HTTP 404:

```text
HTTP/1.1 404 NOT FOUND
```

Thu lai exploit:

```bash
python checker/checker.py exploit 127.0.0.1 8000
```

Sau khi route debug bi xoa, exploit khong con lay duoc carrier. Tuy cach hien thi
co the khac tuy runner, nhung ket qua hop le la khong in ra flag nua.

Anh can chup:

```text
solution/screenshots/defense-06-exploit-blocked.png
```

Anh nen thay ro:

- `/api/debug/list` tra ve `404 NOT FOUND`, hoac
- `checker.py exploit` khong in flag.

## 8. Giai thich ngan gon de dua vao bai nop

Doan giai thich co the dua thang vao form/writeup:

```text
Defense xoa hai debug endpoint /api/debug/list va /api/debug/file/<filename>.
Hai endpoint nay khong can token nen attacker co the tai raw carrier .h265 va
doc bit an trong AUD NAL type 35. Sau khi xoa endpoint debug, checker van dung
/api/store va /api/read binh thuong, nhung attacker khong con lay duoc carrier
de giai kenh H.265.
```

## 9. Defense tot hon

Ngoai viec xoa debug endpoint, co the harden them:

- Khong public raw carrier `.h265`.
- Neu can cho tai video preview, tao ban render/preview khong chua kenh AUD goc.
- Ma hoa payload truoc khi nhung vao AUD bang key chi service biet.
- Them log va rate limit cho cac endpoint doc file.
- Rotate flag da bi lo sau khi deploy ban va.
