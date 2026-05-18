# AUD Timing - Writeup

## Tổng quan

Challenge cung cấp một video H.265/HEVC hợp lệ. Video phát bình thường, không có flag khi soi bằng `strings`, và không có file trace đi kèm. Hướng giải không phải soi từng frame ảnh, mà là phân tích cấu trúc bitstream H.265.

File cần phân tích chính là:

```text
bunny_aud_suspect.hevc
```

File `bunny_aud_suspect.mp4` chỉ dùng để xem nhanh nội dung video.

## Kiểm tra file

Trước hết kiểm tra video bằng `ffprobe`:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,duration \
  -of default=noprint_wrappers=1 bunny_aud_suspect.mp4
```

Kết quả:

```text
codec_name=hevc
width=1920
height=1080
r_frame_rate=30/1
duration=18.000000
```

Tiếp theo thử tìm flag trực tiếp:

```bash
strings bunny_aud_suspect.hevc | grep -i blockChainPTIT
```

Không có kết quả. Như vậy flag không được nhúng trực tiếp dưới dạng chuỗi ASCII.

## Parse H.265 NAL

H.265 Annex-B bitstream gồm nhiều NAL unit. Mỗi NAL thường bắt đầu bằng một trong hai start code:

```text
00 00 01
00 00 00 01
```

Ta tách file thành các NAL, sau đó lấy `nal_unit_type` bằng công thức:

```python
nal_unit_type = (nal[0] >> 1) & 0x3f
```

Đoạn code thống kê nhanh:

```python
from collections import Counter
from pathlib import Path

data = Path("bunny_aud_suspect.hevc").read_bytes()

starts = []
i = 0
while i < len(data) - 3:
    if data[i:i+3] == b"\x00\x00\x01":
        starts.append((i, 3))
        i += 3
    elif data[i:i+4] == b"\x00\x00\x00\x01":
        starts.append((i, 4))
        i += 4
    else:
        i += 1

counter = Counter()
for idx, (start, sc_len) in enumerate(starts):
    end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
    nal = data[start + sc_len:end]
    if len(nal) < 2:
        continue
    ntype = (nal[0] >> 1) & 0x3f
    counter[ntype] += 1

print(counter)
```

Khi thống kê, NAL type `35` xuất hiện đều theo nhịp video. Trong HEVC, type `35` là **Access Unit Delimiter** (AUD). AUD không chứa ảnh, mà là NAL điều khiển/đánh dấu access unit. Đây khớp với hint “cửa ra vào của mỗi nhịp video”.

## Trích bit ứng viên từ AUD

AUD có header NAL 2 byte. Byte RBSP đầu tiên sau header chứa `primary_pic_type` ở 3 bit cao:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
```

Nếu chỉ nhìn riêng AUD, bit có khả năng mang dữ liệu là bit thấp nhất:

```python
aud_lsb = primary_pic_type & 1
```

Tuy nhiên, đọc tuần tự toàn bộ `aud_lsb` không ra flag. Điều này cho thấy AUD chỉ là một nửa của kênh giấu tin.

## Kết hợp với VCL NAL

Các NAL type từ `0` đến `31` là VCL, tức NAL chứa dữ liệu ảnh. Hint nói “cái bóng tăng/giảm của bức tranh phía sau”, nên ta lấy kích thước VCL NAL theo từng nhịp và so với VCL trước đó.

Với mỗi vị trí `i`:

```python
trend_bit = 1 if vcl_size[i] > vcl_size[i - 1] else 0
hidden_bit = aud_lsb ^ trend_bit
```

Ý tưởng là: AUD tạo ra một bit ứng viên, còn biến động kích thước VCL quyết định bit đó nên giữ nguyên hay lật. Vì vậy nếu chỉ đọc AUD thì thấy nhiễu, còn khi kết hợp với VCL trend thì stream có cấu trúc.

## Không đọc tuần tự

Sau khi tính được `hidden_bit`, nếu ghép tuần tự vẫn chưa ra flag. Hint nói “con đường không đi từng viên gạch liền nhau”, nên cần thử đọc chuỗi bit theo một bước nhảy cố định:

```text
pos = (start + k * step) mod AUD_COUNT
```

Ta brute force `start` và `step`. Với `step`, nên yêu cầu:

```python
gcd(step, AUD_COUNT) == 1
```

để đường đi có thể quét qua toàn bộ chuỗi thay vì bị kẹt trong chu kỳ ngắn.

Khi đúng lịch đọc, stream bắt đầu bằng magic:

```text
AU
```

Sau đó là 2 byte độ dài, payload và CRC32:

```text
magic       2 byte  "AU"
length      2 byte  big-endian
payload     n byte  flag ASCII
crc32       4 byte  crc32(payload)
```

CRC32 không phải crypto, chỉ dùng để xác nhận rằng ta đã đọc đúng lịch và đúng bit.

## Solver

Script giải hoàn chỉnh nằm trong:

```text
solution/solve.py
```

Chạy:

```bash
python3 solve.py ../public/bunny_aud_suspect.hevc
```

Các phần chính của solver:

Tách NAL theo start code:

```python
def find_nals(data: bytes):
```

Tính loại NAL:

```python
def nal_type(nal: bytes) -> int:
    return (nal[0] >> 1) & 0x3F
```

Lấy bit ứng viên từ AUD:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
bits.append(primary_pic_type & 1)
```

Tạo bit tăng/giảm từ VCL:

```python
vcl_bits = [
    1 if vcl_sizes[i] > vcl_sizes[(i - 1) % len(vcl_sizes)] else 0
    for i in range(len(bits))
]
```

Khôi phục bit thật:

```python
walked.append(aud_bits[pos] ^ vcl_bits[pos])
```

Brute force lịch đọc:

```python
for start in range(len(bits)):
    for step in range(1, len(bits)):
        if gcd(step, len(bits)) != 1:
            continue
```

Kiểm tra packet:

```python
if raw[:2] != b"AU":
    return b""

size = struct.unpack(">H", raw[2:4])[0]
plain = raw[4:4 + size]
crc_expected = struct.unpack(">I", raw[4 + size:8 + size])[0]
```

## Kết quả

Output khi chạy solver:

```text
AUD_NAL_COUNT=542
WALK_START=19
WALK_STEP=73
blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```

## Flag

```text
blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```
