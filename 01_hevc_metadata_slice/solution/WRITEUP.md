# HEVC Metadata Slice - Writeup

## 1. Xác định file cần phân tích

Challenge cung cấp:

```text
suspicious.hevc
clean.hevc
HINT.txt
```

File cần lấy flag là:

```text
suspicious.hevc
```

File `clean.hevc` dùng để đối chiếu khi cần.

## 2. Kiểm tra nhanh bằng strings

Chạy:

```bash
strings suspicious.hevc | grep -i HEVC
```

Không thấy flag đầy đủ. Điều này cho thấy flag không nằm thẳng trong file theo dạng ASCII rõ ràng.

## 3. Parse start code Annex-B

File `.hevc` là bitstream Annex-B. Ta tách NAL bằng start code:

```text
00 00 01
00 00 00 01
```

Đoạn code:

```python
def find_start_codes(data):
    out = []
    i = 0
    while i < len(data) - 3:
        if data[i:i+4] == b"\x00\x00\x00\x01":
            out.append((i, 4))
            i += 4
        elif data[i:i+3] == b"\x00\x00\x01":
            out.append((i, 3))
            i += 3
        else:
            i += 1
    return out
```

## 4. Tách từng NAL unit

Sau khi có danh sách start code, cắt từng NAL:

```python
def iter_nals(data):
    starts = find_start_codes(data)
    for idx, (start, size) in enumerate(starts):
        off = start + size
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
        payload = data[off:end]
        nal_type = (payload[0] >> 1) & 0x3f
        yield nal_type, payload
```

## 5. Tìm SEI NAL

Trong HEVC:

```text
NAL type 39 = prefix SEI
NAL type 40 = suffix SEI
```

Ta lọc hai loại này:

```python
if nal_type not in (39, 40):
    continue
```

## 6. Chuyển EBSP sang RBSP

Trước khi parse SEI payload, cần bỏ emulation-prevention byte `0x03` sau hai byte `0x00`.

```python
def ebsp_to_rbsp(data):
    out = bytearray()
    zeros = 0
    i = 0
    while i < len(data):
        b = data[i]
        if zeros >= 2 and b == 0x03:
            zeros = 0
            i += 1
            continue
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
        i += 1
    return bytes(out)
```

## 7. Parse SEI payload

SEI dùng cấu trúc:

```text
payload_type
payload_size
payload
```

Trong bài này cần tìm `user_data_unregistered`, có:

```text
payload_type = 5
```

## 8. Bỏ UUID trong user_data_unregistered

Payload `user_data_unregistered` bắt đầu bằng 16 byte UUID. Phần sau UUID mới là dữ liệu giấu:

```python
encrypted = payload[16:]
```

## 9. Brute force XOR key

Dữ liệu sau UUID bị XOR 1 byte. Thử tất cả key từ `0` đến `255`:

```python
for key in range(256):
    text = bytes(b ^ key for b in encrypted)
    if text.startswith(b"HEVC-LAB{"):
        print(text.decode())
```

Kết quả:

```text
HEVC-LAB{metadata_is_not_pixels}
```

## 10. Kiểm tra token phụ

Ngoài flag chính trong SEI, file còn có token phụ trong VCL trailing bytes:

```text
SLICE:qpel_path
```

Token này dùng để xác nhận rằng file có nhiều hơn một vị trí bất thường, nhưng flag chính vẫn là SEI payload.

## 11. Chạy solver

```bash
python3 solve.py ../public/suspicious.hevc
```

Output:

```text
HEVC-LAB{metadata_is_not_pixels}
```

## 12. Độ khó suy ra

Bài có khoảng 11 bước kỹ thuật: parse NAL, nhận diện SEI, chuyển EBSP sang RBSP, parse `user_data_unregistered`, bỏ UUID và brute force XOR 1 byte.

Độ khó suy ra: **Trung bình** nếu tính theo số bước thao tác; **dễ-trung bình** nếu người chơi đã quen SEI trong H.265.

## Flag

```text
HEVC-LAB{metadata_is_not_pixels}
```
