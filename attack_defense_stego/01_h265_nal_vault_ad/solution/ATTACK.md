# H265 NAL Vault AD - Writeup Attack

## 1. Tóm tắt lỗi

Service lưu flag vào raw HEVC Annex-B bitstream. Luồng hợp lệ `/api/read` và
`/api/carrier` đều cần `token`, nhưng service có tính năng public preview:

```text
/api/share/<id>/preview.h265
```

Preview được quảng bá là metadata-only vì đã bỏ VCL slice chứa dữ liệu ảnh. Lỗi
là preview vẫn giữ AUD NAL type 35. Trong bài này, AUD không vô hại: bit thấp
nhất của `primary_pic_type` đang chứa kênh ẩn.

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

Dashboard cho thấy service có luồng store/read hợp lệ và có public preview.

## 3. Tìm target public

Liệt kê các vault public:

```bash
curl http://127.0.0.1:8000/api/vaults
```

Ví dụ output:

```json
{
  "items": [
    {
      "id": "flag_1710000000_abcd1234",
      "preview_url": "/api/share/flag_1710000000_abcd1234/preview.h265",
      "share_url": "/share/flag_1710000000_abcd1234"
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
curl -o preview.h265 http://127.0.0.1:8000/api/share/flag_1710000000_abcd1234/preview.h265
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

- `attack-01-dashboard.png`: dashboard `/` có form store/read và public preview.
- `attack-02-vaults.png`: `/api/vaults` làm lộ target id và preview URL.
- `attack-03-preview-download.png`: tải được public preview `.h265`.
- `attack-04-exploit-flag.png`: exploit in ra flag.
