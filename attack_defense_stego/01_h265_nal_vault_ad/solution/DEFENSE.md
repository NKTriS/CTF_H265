# H265 NAL Vault AD - Writeup Defense

## 1. Mục tiêu defense

Mục tiêu của defense không phải là xóa cơ chế giấu tin. Checker vẫn cần
`/api/store` để đặt flag và `/api/read` để đọc lại flag bằng token. Điểm cần vá
là hai endpoint debug vì chúng cho tải carrier `.h265` mà không cần token.

## 2. Ảnh chụp 1 - chứng minh trước khi vá là bị leak

Trước khi sửa, chạy service và đặt một flag mẫu:

```bash
cd attack_defense_stego/01_h265_nal_vault_ad
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Lệnh này sẽ trả về JSON có `id` và `token`. Sau đó chạy exploit:

```bash
python checker/checker.py exploit 127.0.0.1 8000
```

Nếu service chưa vá, output sẽ có flag:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Ảnh cần chụp:

```text
solution/screenshots/defense-01-before-exploit-leaks-flag.png
```

Nội dung ảnh nên thấy rõ:

- Lệnh `python checker/checker.py exploit 127.0.0.1 8000`.
- Output có flag.
- Nếu có thể, chụp kèm kết quả `/api/debug/list` trả về file `.h265`.

## 3. Xác định đúng điểm cần sửa

Mở file:

```text
service/app.py
```

Đoạn code nguy hiểm:

```python
@app.get("/api/debug/list")
def debug_list():
    files = sorted(path.name for path in VAULT_DIR.glob("*.h265"))
    return jsonify(ok=True, files=files)


@app.get("/api/debug/file/<path:filename>")
def debug_file(filename: str):
    return send_from_directory(VAULT_DIR, filename, mimetype="video/H265")
```

Lý do nguy hiểm:

- `/api/debug/list` làm lộ tên carrier của các flag đang lưu.
- `/api/debug/file/<filename>` cho tải raw HEVC carrier mà không cần token.
- Token trong `/api/read` bị vô nghĩa, vì attacker đọc trực tiếp kênh AUD từ file
  `.h265`.

Ảnh cần chụp:

```text
solution/screenshots/defense-02-vulnerable-code.png
```

Ảnh nên chụp màn hình editor đang mở đúng hai route debug trên.

## 4. Cách vá nhanh nhất

Xóa import `send_from_directory` vì sau khi xóa debug route sẽ không dùng nữa:

```python
from flask import Flask, jsonify, request
```

Sau đó xóa hoàn toàn hai route:

```python
@app.get("/api/debug/list")
def debug_list():
    ...

@app.get("/api/debug/file/<path:filename>")
def debug_file(filename: str):
    ...
```

Patch mẫu đã có sẵn:

```bash
git apply solution/defense.patch
```

Nếu không dùng git, có thể sửa tay theo nội dung trong `solution/defense.patch`.

Ảnh cần chụp:

```text
solution/screenshots/defense-03-patched-code.png
```

Ảnh nên thấy rõ file `service/app.py` sau khi không còn route `/api/debug/list`
và `/api/debug/file/<filename>`.

## 5. Rebuild và restart service

Sau khi sửa code, rebuild container để service chạy bản mới:

```bash
cd service
docker compose down
docker compose up --build -d
```

Kiểm tra container còn sống:

```bash
curl http://127.0.0.1:8000/health
```

Kết quả cần có:

```json
{"ok":true}
```

Ảnh cần chụp:

```text
solution/screenshots/defense-04-service-health-after-patch.png
```

## 6. Kiểm tra defense không làm hỏng checker

Đây là bước quan trọng trong attack/defense. Nếu chỉ chặn exploit nhưng làm hỏng
`put/get` thì service vẫn bị mất điểm availability.

Chạy checker tổng quát:

```bash
cd attack_defense_stego/01_h265_nal_vault_ad
python checker/checker.py check 127.0.0.1 8000
```

Output mong đợi:

```text
OK
```

Kiểm tra rõ hơn bằng `put` và `get`:

```bash
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Lệnh trên in ra JSON, ví dụ:

```json
{"id":"flag_1710000000_abcd1234","token":"0123456789abcdef"}
```

Dùng lại JSON đó để đọc flag:

```bash
python checker/checker.py get 127.0.0.1 8000 '{"id":"flag_1710000000_abcd1234","token":"0123456789abcdef"}' 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Output mong đợi:

```text
OK
```

Ảnh cần chụp:

```text
solution/screenshots/defense-05-checker-still-ok.png
```

Ảnh nên thấy rõ checker `check` hoặc cặp `put/get` đều trả về `OK`.

## 7. Chứng minh exploit đã bị chặn

Thử gọi debug list:

```bash
curl -i http://127.0.0.1:8000/api/debug/list
```

Sau khi vá đúng, kết quả phải là HTTP 404:

```text
HTTP/1.1 404 NOT FOUND
```

Thử lại exploit:

```bash
python checker/checker.py exploit 127.0.0.1 8000
```

Sau khi route debug bị xóa, exploit không còn lấy được carrier. Tùy runner mà
cách hiển thị có thể khác nhau, nhưng kết quả hợp lệ là không in ra flag nữa.

Ảnh cần chụp:

```text
solution/screenshots/defense-06-exploit-blocked.png
```

Ảnh nên thấy rõ:

- `/api/debug/list` trả về `404 NOT FOUND`, hoặc
- `checker.py exploit` không in flag.

## 8. Giải thích ngắn gọn để đưa vào bài nộp

Đoạn giải thích có thể đưa thẳng vào form/writeup:

```text
Defense xóa hai debug endpoint /api/debug/list và /api/debug/file/<filename>.
Hai endpoint này không cần token nên attacker có thể tải raw carrier .h265 và
đọc bit ẩn trong AUD NAL type 35. Sau khi xóa endpoint debug, checker vẫn dùng
/api/store và /api/read bình thường, nhưng attacker không còn lấy được carrier
để giải kênh H.265.
```

## 9. Defense tốt hơn

Ngoài việc xóa debug endpoint, có thể harden thêm:

- Không public raw carrier `.h265`.
- Nếu cần cho tải video preview, tạo bản render/preview không chứa kênh AUD gốc.
- Mã hóa payload trước khi nhúng vào AUD bằng key chỉ service biết.
- Thêm log và rate limit cho các endpoint đọc file.
- Rotate flag đã bị lộ sau khi deploy bản vá.
