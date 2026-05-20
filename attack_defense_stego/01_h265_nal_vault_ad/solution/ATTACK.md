# H265 Evidence Portal AD - Writeup Attack

## 1. Tóm tắt lỗi

Service mô phỏng một cổng chia sẻ bằng chứng CCTV. Raw evidence carrier là file
HEVC/H.265 Annex-B. Custody marker của case được nhúng vào AUD NAL type 35.

Luồng hợp lệ `/api/read` và `/api/carrier` đều cần operator token. Tuy nhiên
service có public redacted preview:

```text
/api/cases/<id>/redacted-preview.h265
```

Preview được quảng bá là bản CCTV đã redact và có thể phát được. Lỗi là pipeline
tạo preview vẫn copy AUD NAL type 35 từ evidence carrier để giữ timing metadata.
Trong bài này, AUD không vô hại: chuỗi AUD chứa custody marker đã được trộn bằng
cadence theo `case id`, AUD giả, XOR mask và Manchester encoding.

## 2. Recon service

Mở dashboard:

```text
http://127.0.0.1:8000/
```

Kiểm tra service:

```bash
curl http://127.0.0.1:8000/health
```

Kết quả hợp lệ:

```json
{"ok":true}
```

Dashboard cho thấy service có luồng import CCTV evidence từ camera/source, verify
custody marker bằng token và public redacted preview. Người dùng bình thường chỉ
nhập Case ID, Operator Token và CCTV Source; custody marker là dữ liệu nội bộ do
service gắn vào evidence.

## 3. Tìm target public

Liệt kê các case public:

```bash
curl http://127.0.0.1:8000/api/cases
```

Ví dụ output:

```json
{
  "items": [
    {
      "id": "flag_1710000000_abcd1234",
      "preview_url": "/api/cases/flag_1710000000_abcd1234/redacted-preview.h265",
      "case_url": "/case/flag_1710000000_abcd1234"
    }
  ],
  "ok": true
}
```

Attacker không có token nên không gọi được `/api/read` hoặc `/api/carrier`.
Nhưng `preview_url` là public.

## 4. Tải preview và khai thác

Tải public preview:

```bash
curl -o preview.h265 http://127.0.0.1:8000/api/cases/flag_1710000000_abcd1234/redacted-preview.h265
```

Chạy script exploit:

```bash
python solution/exploit.py http://127.0.0.1:8000
```

Nếu đã biết target id:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1710000000_abcd1234
```

Output:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

## 5. Phân tích kênh H.265

Raw HEVC Annex-B được tách theo start code:

```text
00 00 01
00 00 00 01
```

Trong HEVC, `nal_unit_type` nằm trong header byte đầu:

```python
nal_unit_type = (nal[0] >> 1) & 0x3f
```

Service dùng AUD NAL:

```text
nal_unit_type = 35
```

Byte RBSP đầu của AUD chứa `primary_pic_type` ở 3 bit cao. Nếu chỉ lấy thẳng
`primary_pic_type & 1` rồi ghép bit thì sẽ không ra `H5AD`, vì trong stream có
AUD giả và bit thật đã bị mask.

```python
primary_pic_type = (nal[2] >> 5) & 0x07
raw_aud_bit = primary_pic_type & 1
```

Luồng giải đúng:

```text
1. Lấy case id từ /api/cases hoặc URL preview.
2. Sinh lại cadence SHA256("h265-ad-cadence:" || case_id || counter).
3. Bỏ 1-3 AUD giả trước mỗi AUD data.
4. Ghép bit data theo primary_pic_type & 1.
5. Giải Manchester: 01 -> 0, 10 -> 1.
6. XOR lại với keystream SHA256("h265-ad-mask:" || case_id || counter).
7. Parse packet H5AD || length || flag || crc32(flag).
```

Packet cuối cùng:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

CRC32 giúp loại bỏ bitstream sai hoặc không phải carrier của bài.

## 6. Ảnh chụp nên có cho phần attack

Đặt ảnh vào `solution/screenshots/` nếu cần nộp kèm:

- `attack-01-dashboard.png`: dashboard `/` có form import/verify và redacted preview.
- `attack-02-cases.png`: `/api/cases` làm lộ target id và preview URL.
- `attack-03-preview-download.png`: tải được public redacted preview `.h265` có thể phát như video H.265.
- `attack-04-exploit-flag.png`: exploit in ra flag.
