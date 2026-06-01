# Attack Round 1 - Leak marker từ public H.265 preview

## 1. Bối cảnh attacker

Service là một cổng lưu trữ bằng chứng CCTV. Người vận hành import video H.265 vào hệ thống, backend gắn thêm custody marker nội bộ. Trong CTF, checker đặt flag vào marker này.

Attacker không có `operator token`, nên không thể đọc marker qua `/api/read` hoặc tải raw carrier qua `/api/carrier`. Attacker chỉ có URL public của service, ví dụ:

```text
http://127.0.0.1:8000/
```

Điểm cần chú ý là service có public redacted preview:

```text
GET /api/cases/<id>/redacted-preview.h265
```

Preview được quảng bá là video đã redact, nhưng vẫn giữ timing metadata để phục vụ review.

## 2. Recon dashboard

Mở dashboard:

```text
http://127.0.0.1:8000/
```

![Dashboard H265 Evidence Portal](screenshots/attack-01-dashboard.png)

Trên dashboard có ba ý quan trọng:

- Có form import CCTV evidence.
- Có form verify custody marker bằng `case id` và `operator token`.
- Có public share, manifest và redacted preview cho từng case.

Token là thứ attacker không có, nên hướng đi hợp lý là tìm endpoint public.

## 3. Lấy danh sách case public

Gọi:

```bash
curl http://127.0.0.1:8000/api/cases
```

![Public cases endpoint làm lộ case id và preview URL](screenshots/attack-02-cases.png)

Response có dạng:

```json
{
  "items": [
    {
      "id": "flag_1780132060_da66f92c",
      "preview_url": "/api/cases/flag_1780132060_da66f92c/redacted-preview.h265",
      "share_url": "/share/8a7f...",
      "manifest_url": "/api/share/8a7f.../manifest.json",
      "source": "lobby_cam_01"
    }
  ],
  "ok": true
}
```

Hai trường cần lấy là `id` và `preview_url`.

## 4. Tải preview và xác nhận đây là H.265 thật

Tải preview:

```bash
curl.exe -L -o preview.h265 http://127.0.0.1:8000/api/cases/flag_1780132060_da66f92c/redacted-preview.h265
```

Kiểm tra file:

```bash
dir preview.h265
```

Kiểm tra codec:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview.h265
```

![Preview public là HEVC bitstream hợp lệ](screenshots/attack-03-ffprobe-preview.png)

Kết quả đúng:

```text
codec_name=hevc
width=640
height=360
```

Vậy preview không phải file text giả. Nó là raw H.265/HEVC Annex-B thật.

## 5. Phân tích cấu trúc H.265

HEVC Annex-B dùng start code để tách NAL unit:

```text
00 00 01
00 00 00 01
```

Với HEVC, `nal_unit_type` nằm trong byte đầu:

```python
nal_unit_type = (nal[0] >> 1) & 0x3f
```

Bài này giấu marker trong AUD NAL:

```text
nal_unit_type = 35
```

Byte payload đầu tiên của AUD chứa `primary_pic_type` ở 3 bit cao:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
raw_bit = primary_pic_type & 1
```

## 6. Reverse thuật toán giấu tin

Service không nhét flag thẳng vào file. Nó xử lý marker theo chuỗi:

```text
H5AD || 2-byte length || marker || crc32(marker)
-> đổi sang bit MSB-first
-> XOR với keystream SHA256("h265-ad-mask:" || case_id || counter)
-> Manchester encode: 0 -> 01, 1 -> 10
-> chèn 1-3 AUD giả trước mỗi bit thật
-> ghi bit thật vào primary_pic_type & 1
```

Seed không phải token. Seed là `case id`, mà attacker đã lấy được từ `/api/cases`.

Vì vậy exploit làm ngược lại:

```text
preview.h265
-> tách NAL
-> lọc AUD type 35
-> lấy raw_bit
-> sinh cadence từ case id để bỏ AUD giả
-> Manchester decode
-> XOR lại bằng mask theo case id
-> parse H5AD, length, marker, crc32
```

## 7. Chạy exploit

Chạy tự động qua danh sách public:

```bash
python solution/exploit.py http://127.0.0.1:8000
```

Hoặc chỉ định case id:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c
```

![Exploit khôi phục được custody marker/flag](screenshots/attack-05-exploit-flag.png)

Output:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

## 8. Kết luận Round 1

Lỗi không nằm ở `/api/read`; route đó vẫn yêu cầu token. Lỗi nằm ở preview pipeline: backend public file `.h265` đã redact nhưng copy nguyên AUD NAL type 35, trong khi marker được giấu trong AUD.

Defense đầu tiên cần strip AUD khỏi preview public.
