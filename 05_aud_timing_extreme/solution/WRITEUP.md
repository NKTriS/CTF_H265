# AUD Timing - Writeup

## 1. Thông tin bài

File public chính:

```text
bunny_aud_suspect.hevc
```

File `bunny_aud_suspect.mp4` chỉ dùng để xem nhanh video. Khi phân tích nên dùng file `.hevc`, vì đây là bitstream Annex-B dễ parse hơn.

Nguồn video gốc:

```text
https://mirror.umd.edu/xbmc/demo-files/BBB/bbb_sunflower_1080p_30fps_normal.mp4
```

Video gốc là Big Buck Bunny Sunflower, metadata ghi Creative Commons Attribution 3.0.

## 2. Kiểm tra ban đầu

Dùng `ffprobe` để xác nhận file là H.265/HEVC hợp lệ:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,duration \
  -of default=noprint_wrappers=1 bunny_aud_suspect.mp4
```

Kết quả mong đợi:

```text
codec_name=hevc
width=1920
height=1080
r_frame_rate=30/1
duration=18.000000
```

Thử tìm flag trực tiếp:

```bash
strings bunny_aud_suspect.hevc | grep -i HEVC
```

Không có flag ASCII rõ ràng. Điều này cho thấy payload không được nhét thẳng dưới dạng chuỗi.

## 3. Hướng phân tích

Hint nói không nên tìm chữ trong ảnh và không phải mọi NAL đều là hình ảnh. Vì vậy hướng hợp lý là parse cấu trúc H.265.

H.265 Annex-B gồm nhiều NAL unit, mỗi NAL thường bắt đầu bằng start code:

```text
00 00 01
00 00 00 01
```

Trong mỗi NAL, byte header đầu tiên chứa `nal_unit_type`:

```python
nal_unit_type = (nal[0] >> 1) & 0x3f
```

Các NAL type từ `0` đến `31` là VCL, tức dữ liệu ảnh thật. Một số type khác là metadata/control NAL.

## 4. Đếm loại NAL

Đoạn script nhỏ để thống kê:

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

Điểm cần chú ý là NAL type `35` xuất hiện nhiều và đều theo số frame. Trong HEVC, type `35` là Access Unit Delimiter, viết tắt là AUD.

AUD không phải dữ liệu ảnh. Nó là một NAL nhỏ dùng để đánh dấu access unit, nên nếu thay đổi cẩn thận thì video vẫn xem bình thường.

## 5. Lấy bit từ AUD

AUD có header NAL 2 byte. Byte RBSP đầu tiên sau header chứa trường `primary_pic_type` ở 3 bit cao:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
```

Nếu chỉ nhìn riêng AUD, ứng viên dễ thấy nhất là bit thấp nhất của `primary_pic_type`:

```python
aud_lsb = primary_pic_type & 1
```

Nhưng đây chưa phải bit thật. Nếu lấy tuần tự tất cả `aud_lsb` rồi ghép byte, ta không thấy flag. Đây là bẫy của bài: đúng vùng nghi vấn nhưng chưa đúng cách đọc.

## 6. Vì sao đọc tuần tự không ra

Challenge có 542 AUD. Nhiều AUD chỉ chứa nhiễu. Stream thật được rải theo một vòng bước nhảy:

```text
pos = (start + k * step) mod AUD_COUNT
```

Vì không biết `start` và `step`, ta brute force. Điều kiện `gcd(step, AUD_COUNT) = 1` giúp bước nhảy đi qua toàn bộ vòng thay vì lặp trong một chu kỳ ngắn.

Khi thử đúng lịch, byte đầu của stream là magic:

```text
AU
```

Đây là dấu hiệu đã đi đúng đường.

## 7. Lớp che giấu chính

Điểm khó của bài không phải là crypto. Bài cố tình làm cho AUD nhìn như nhiễu bằng cách không lưu bit trực tiếp trong AUD.

Bit thật được tạo từ quan hệ giữa AUD và kích thước VCL NAL cùng nhịp:

```text
hidden_bit = aud_lsb XOR (vcl_size & 1)
```

Trong đó:

- `aud_lsb` là bit thấp nhất của `primary_pic_type`.
- `vcl_size` là kích thước NAL ảnh tương ứng.

Vì vậy nếu chỉ lấy `aud_lsb` theo thứ tự thì ta chỉ thấy nhiễu. Nhưng khi XOR với parity của VCL size, stream thật hiện ra.

Sau khi khôi phục đúng bit, cấu trúc gói là:

```text
magic       2 byte  "AU"
length      2 byte  big-endian
payload     n byte  flag ASCII
crc32       4 byte  crc32(flag)
```

CRC32 chỉ dùng để xác nhận đã đọc đúng, không phải một lớp crypto.

## 8. Solve script hoàn chỉnh

Script giải nằm trong:

```text
solution/solve.py
```

Cách chạy:

```bash
python3 solve.py ../public/bunny_aud_suspect.hevc
```

Ý nghĩa các phần quan trọng:

```python
def find_nals(data: bytes):
```

Hàm này tách bitstream theo start code `00 00 01` hoặc `00 00 00 01`.

```python
def nal_type(nal: bytes) -> int:
    return (nal[0] >> 1) & 0x3F
```

Hàm này lấy loại NAL theo chuẩn HEVC.

```python
primary_pic_type = (nal[2] >> 5) & 0x07
bits.append(primary_pic_type & 1)
```

Đoạn này lấy bit ẩn từ AUD.

```python
vcl_bits = [size & 1 for size in vcl_sizes[:len(bits)]]
```

Đoạn này lấy parity của kích thước VCL NAL tương ứng. Đây là “cái bóng” của dữ liệu ảnh dùng để bỏ nhiễu khỏi AUD.

```python
for start in range(len(bits)):
    for step in range(1, len(bits)):
        if gcd(step, len(bits)) != 1:
            continue
```

Đoạn này brute force lịch lấy mẫu.

```python
walked.append(aud_bits[pos] ^ vcl_bits[pos])
```

Đoạn này khôi phục bit thật bằng quan hệ giữa AUD và VCL size.

## 9. Kết quả

Chạy solve:

```bash
python3 solve.py ../public/bunny_aud_suspect.hevc
```

Output:

```text
AUD_NAL_COUNT=542
WALK_START=19
WALK_STEP=73
HEVC{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```

## 10. Flag

```text
HEVC{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```
