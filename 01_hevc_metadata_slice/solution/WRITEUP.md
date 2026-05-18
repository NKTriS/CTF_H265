# Silent Frame - Writeup

## 1. Khảo sát file được cung cấp

Challenge cung cấp:

```text
suspicious.hevc
clean.hevc
HINT.txt
```

File cần phân tích chính là `suspicious.hevc`. File `clean.hevc` dùng để đối chiếu khi cần kiểm tra phần nào bị thêm hoặc thay đổi.

Thử tìm flag trực tiếp:

```bash
strings suspicious.hevc | grep -i blockChainPTIT
```

Không có kết quả. Như vậy flag không nằm thẳng dưới dạng ASCII rõ ràng trong file.

## 2. Chọn hướng phân tích

Hint của bài nói đến thứ "không thuộc khung hình" nhưng vẫn đi cùng luồng hình, đồng thời nhắc đến một phần thừa khi so hai file gần giống nhau.

Trong H.265/HEVC, các dữ liệu không trực tiếp là ảnh thường nằm ở những NAL ngoài VCL, ví dụ SEI. Vì vậy hướng hợp lý là parse bitstream HEVC và kiểm tra các NAL metadata/control trước.

## 3. Tách NAL unit trong Annex-B

File `.hevc` dùng dạng Annex-B, các NAL được phân tách bằng start code:

```text
00 00 01
00 00 00 01
```

Code tách start code:

```python
def find_start_codes(data):
    out = []
    i = 0
    while i < len(data) - 3:
        if data[i:i + 4] == b"\x00\x00\x00\x01":
            out.append((i, 4))
            i += 4
        elif data[i:i + 3] == b"\x00\x00\x01":
            out.append((i, 3))
            i += 3
        else:
            i += 1
    return out
```

Sau đó cắt từng NAL và lấy `nal_unit_type`:

```python
nal_type = (payload[0] >> 1) & 0x3f
```

## 4. Tìm SEI NAL

Trong HEVC:

```text
NAL type 39 = prefix SEI
NAL type 40 = suffix SEI
```

Do đó solver lọc hai loại NAL này:

```python
if nal_type not in (39, 40):
    continue
```

Đây là vị trí hợp lý để giấu dữ liệu vì SEI không phải dữ liệu ảnh, nhưng vẫn là một phần hợp lệ của bitstream video.

## 5. Parse payload SEI

Trước khi đọc SEI, cần chuyển EBSP sang RBSP bằng cách bỏ emulation-prevention byte `0x03` sau hai byte `0x00`:

```python
def ebsp_to_rbsp(data):
    out = bytearray()
    zeros = 0
    for b in data:
        if zeros >= 2 and b == 0x03:
            zeros = 0
            continue
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
    return bytes(out)
```

SEI payload có cấu trúc:

```text
payload_type
payload_size
payload
```

Trong bài này cần tìm `user_data_unregistered`, có `payload_type = 5`.

## 6. Bỏ UUID và giải dữ liệu sau UUID

`user_data_unregistered` bắt đầu bằng 16 byte UUID. Phần sau UUID mới là dữ liệu được giấu:

```python
encrypted = payload[16:]
```

Dữ liệu này bị XOR bằng một key 1 byte. Brute force toàn bộ 256 key:

```python
for key in range(256):
    text = bytes(b ^ key for b in encrypted)
    if text.startswith(b"blockChainPTIT{"):
        print(text.decode())
```

Kết quả:

```text
blockChainPTIT{metadata_nopixel}
```

## 7. Kiểm tra dấu vết phụ trong VCL

Ngoài flag chính trong SEI, file còn có token phụ trong phần trailing của VCL:

```text
SLICE:qpel_path
```

Token này xác nhận file có nhiều dấu hiệu bất thường, nhưng flag chính của challenge vẫn nằm trong SEI `user_data_unregistered`.

## 8. Chạy solver xác nhận

Script giải nằm tại:

```text
solution/solve.py
```

Chạy:

```bash
python3 solve.py ../public/suspicious.hevc
```

Output:

```text
blockChainPTIT{metadata_nopixel}
```

Flag:

```text
blockChainPTIT{metadata_nopixel}
```
