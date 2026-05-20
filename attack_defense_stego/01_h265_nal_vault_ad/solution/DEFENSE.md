# H265 NAL Vault AD - Writeup Defense

## 1. Mục tiêu defense

Mục tiêu của defense không phải là tắt dashboard hay bỏ tính năng public preview.
Checker vẫn cần `/api/store` để đặt flag và `/api/read` để đọc lại flag bằng
token. Service cũng nên tiếp tục có `/api/vaults` và `/share/<id>` để giống một
web service thật.

Điểm cần vá là logic tạo preview. Bản lỗi chỉ strip VCL slice nhưng vẫn giữ AUD
NAL type 35. Vì flag nằm trong `primary_pic_type` của AUD, preview public vẫn
làm lộ flag.

## 2. Chứng minh trước khi vá là bị leak

Trước khi sửa, chay service và đặt một flag mẫu:

```bash
cd attack_defense_stego/01_h265_nal_vault_ad
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Lệnh này sẽ trả về JSON có `id` và `token`. Attacker chỉ cần `id`, không cần
token.

Liệt kê vault public:

```bash
curl http://127.0.0.1:8000/api/vaults
```

Chạy exploit:

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

## 3. Xác định đúng điểm cần sửa

Mở file:

```text
service/app.py
```

Đoạn code nguy hiểm:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        ntype = nal_type(nal)
        if 0 <= ntype <= 31:
            continue
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)
```

Lý do nguy hiểm:

- `0..31` là VCL NAL, đã bị strip khỏi preview.
- `35` là AUD NAL, vẫn được giữ lại.
- Hidden bit nằm ở `primary_pic_type & 1` trong AUD.
- Vì vậy preview “metadata-only” vẫn đủ dữ liệu để giải flag.

Ảnh cần chụp:

```text
solution/screenshots/defense-02-vulnerable-preview-code.png
```

## 4. Cách vá nhanh nhất

Strip luôn AUD NAL khỏi preview:

```python
if 0 <= ntype <= 31 or ntype == 35:
    continue
```

Patch mẫu đã có sẵn:

```bash
git apply solution/defense.patch
```

Ảnh cần chụp:

```text
solution/screenshots/defense-03-patched-preview-code.png
```

## 5. Rebuild và restart service

Sau khi sửa code, rebuild container:

```bash
cd service
docker compose down
docker compose up --build -d
```

Kiểm tra service còn sống:

```bash
curl http://127.0.0.1:8000/health
```

Kết quả cần có:

```json
{"ok":true}
```

Kiểm tra dashboard vẫn mở được:

```bash
curl http://127.0.0.1:8000/
```

Kết quả cần có HTML của trang `H265 NAL Vault`.

## 6. Kiểm tra defense không làm hỏng checker

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

## 7. Chứng minh exploit đã bị chặn

Public preview vẫn có thể tồn tại:

```bash
curl -I http://127.0.0.1:8000/api/share/flag_1710000000_abcd1234/preview.h265
```

Nhưng exploit không còn giải được flag:

```bash
python checker/checker.py exploit 127.0.0.1 8000
```

Kết quả hợp lệ là không in ra flag nữa.

Ảnh cần chụp:

```text
solution/screenshots/defense-06-exploit-blocked.png
```

## 8. Giải thích ngắn gọn để đưa vào bài nộp

```text
Defense sửa hàm tạo public preview để strip cả AUD NAL type 35, không chỉ strip
VCL NAL. Lỗi cũ giữ lại AUD vì xem đó là metadata vô hại, nhưng flag nằm trong
primary_pic_type của AUD. Sau khi bỏ AUD khỏi preview, checker vẫn dùng
/api/store và /api/read bình thường, dashboard và share page vẫn hoạt động, còn
attacker không thể khôi phục flag từ preview public.
```

## 9. Defense tốt hơn

Ngoài việc strip AUD, có thể harden thêm:

- Tạo preview bằng encoder/transcoder sạch thay vì lọc NAL thủ công.
- Mã hóa payload trước khi nhúng vào AUD bằng key chỉ service biết.
- Không publish preview cho carrier chứa secret đang active.
- Thêm log và rate limit cho các endpoint share/preview.
- Rotate flag đã bị lộ sau khi deploy bản vá.
