# H265 Evidence Portal AD - Writeup Defense

## 1. Mục tiêu defense

Mục tiêu của defense không phải là tắt dashboard hay bỏ tính năng redacted
preview. Checker vẫn cần `/api/store` để import case và đặt flag/custody marker
nội bộ, còn `/api/read` dùng để đọc lại bằng token. Service cũng nên tiếp tục có
`/api/cases` và `/case/<id>` để giống một evidence portal thật.

Điểm cần vá là logic tạo preview. Bản lỗi tạo preview CCTV đã redact, vẫn phát
được, nhưng copy AUD NAL type 35 từ evidence carrier. Dù marker đã được làm khó
bằng AUD giả, Manchester encoding và XOR mask theo `case id`, mọi dữ liệu cần
để giải vẫn nằm trong public preview nên preview public vẫn làm lộ marker.

## 2. Chứng minh trước khi vá là bị leak

Trước khi sửa, chạy service và đặt một flag mẫu:

```bash
cd attack_defense_stego/01_h265_nal_vault_ad
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Lệnh này sẽ trả về JSON có `id` và `token`. Attacker chỉ cần `id`, không cần
token.

Liệt kê case public:

```bash
curl http://127.0.0.1:8000/api/cases
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
        # Vulnerability: the preview is playable because it keeps redacted VCL
        # frames, but it also preserves AUD timing metadata carrying the marker.
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)
```

Lý do nguy hiểm:

- Preview giữ lại VCL frame đã redact để người nhận vẫn xem được video.
- `35` là AUD NAL, cũng bị copy sang preview.
- Bit mã hóa nằm ở `primary_pic_type & 1` trong AUD data.
- AUD giả, cadence và XOR mask chỉ làm tăng độ khó attack, không phải defense.
- Vì vậy redacted preview vừa xem được, vừa vẫn đủ dữ liệu để giải flag.

Ảnh cần chụp:

```text
solution/screenshots/defense-02-vulnerable-preview-code.png
```

## 4. Cách vá nhanh nhất

Giữ các frame preview nhưng strip AUD NAL khỏi preview:

```python
if nal_type(nal) == 35:
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

Kết quả cần có HTML của trang `H265 Evidence Portal`.

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
curl -I http://127.0.0.1:8000/api/cases/flag_1710000000_abcd1234/redacted-preview.h265
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
Defense sửa hàm tạo redacted preview để strip AUD NAL type 35 trong khi vẫn giữ
các VCL frame preview. Lỗi cũ copy AUD vì xem đó là metadata/timing vô hại,
nhưng marker vẫn nằm trong chuỗi AUD sau lớp decoy, Manchester và XOR theo case
id. Sau khi bỏ AUD khỏi preview, checker vẫn dùng /api/store và /api/read bình
thường, dashboard và case page vẫn hoạt động, preview vẫn xem được, còn attacker
không thể khôi phục flag từ public preview.
```

## 9. Defense tốt hơn

Ngoài việc strip AUD, có thể harden thêm:

- Tạo preview bằng encoder/transcoder sạch thay vì lọc NAL thủ công.
- Mã hóa payload trước khi nhúng vào AUD bằng key chỉ service biết.
- Không publish preview cho case chứa marker đang active.
- Thêm log và rate limit cho các endpoint case/preview.
- Rotate flag đã bị lộ sau khi deploy bản vá.
