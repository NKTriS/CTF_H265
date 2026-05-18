# AUD Timing - Writeup

## 1. Xác định file cần phân tích

Challenge phát cho người chơi các file:

```text
bunny_aud_suspect.hevc
bunny_aud_suspect.mp4
HINT.txt
```

File chính cần phân tích là:

```text
bunny_aud_suspect.hevc
```

File `.mp4` chỉ dùng để xem nhanh video, còn file `.hevc` là bitstream Annex-B thuận tiện hơn cho việc tách NAL unit.

## 2. Kiểm tra video bằng ffprobe

Chạy:

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

Video là H.265/HEVC hợp lệ.

## 3. Kiểm tra flag plaintext

Thử tìm flag trực tiếp:

```bash
strings bunny_aud_suspect.hevc | grep -i blockChainPTIT
```

Không có kết quả. Điều này cho thấy flag không nằm thẳng dưới dạng chuỗi ASCII trong file.

## 4. Đọc hint và chọn hướng phân tích

Hint nói:

```text
Đừng soi từng khung hình; hãy đứng ở cửa ra vào của mỗi nhịp video.
Người gác cửa thì thầm rất khẽ; cái bóng của bức tranh phía sau chỉ rõ lời thì thầm ấy nên lật hay giữ.
Con đường không đi từng viên gạch liền nhau; có vài viên chỉ được đặt để đánh lạc hướng.
Nếu nghe đúng nhịp, lá thư mở đầu bằng hai chữ `AU`, sau đó là độ dài và một dấu kiểm ở cuối.
```

Từ hint này, không nên bắt đầu bằng OCR, LSB pixel hay trích frame ảnh. Hướng hợp lý hơn là phân tích cấu trúc H.265 ở mức bitstream/NAL.

## 5. Đọc file HEVC ở dạng byte

Trong Python:

```python
from pathlib import Path

data = Path("bunny_aud_suspect.hevc").read_bytes()
```

Ta làm việc trực tiếp với byte của file vì cần tách NAL unit.

## 6. Tìm start code Annex-B

H.265 Annex-B dùng start code để phân tách NAL:

```text
00 00 01
00 00 00 01
```

Đoạn code tìm start code:

```python
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
```

Mỗi vị trí trong `starts` là điểm bắt đầu của một NAL unit.

## 7. Tách NAL unit

Từ danh sách start code, cắt từng NAL:

```python
for idx, (start, sc_len) in enumerate(starts):
    end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
    nal = data[start + sc_len:end]
```

`sc_len` là độ dài start code. Phần `nal` sau khi cắt không còn start code.

## 8. Tính nal_unit_type

Trong HEVC, loại NAL được lấy từ byte đầu tiên của NAL header:

```python
nal_unit_type = (nal[0] >> 1) & 0x3f
```

Các NAL type từ `0` đến `31` là VCL, tức dữ liệu ảnh. Các type khác là metadata/control NAL.

## 9. Thống kê NAL type

Dùng `Counter` để đếm các loại NAL:

```python
from collections import Counter

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

Điểm đáng chú ý là NAL type `35` xuất hiện nhiều và đều theo nhịp video.

## 10. Xác định NAL type 35 là AUD

Trong HEVC, NAL type `35` là **Access Unit Delimiter** (AUD).

AUD không chứa dữ liệu ảnh. Nó là NAL điều khiển dùng để đánh dấu access unit, rất khớp với hình ảnh “người gác cửa” trong hint.

Vì vậy ta tập trung vào các NAL type `35`.

## 11. Lấy primary_pic_type từ AUD

AUD có NAL header 2 byte. Byte RBSP đầu tiên sau header chứa `primary_pic_type` ở 3 bit cao:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
```

Trong file này, các AUD thường có dạng:

```text
46 01 xx
```

Trong đó `xx >> 5` cho ra `primary_pic_type`.

## 12. Lấy bit ứng viên từ AUD

Hint nói “người gác cửa thì thầm rất khẽ”, nên ta không lấy toàn bộ `primary_pic_type`, mà lấy bit nhỏ nhất:

```python
aud_lsb = primary_pic_type & 1
```

Nếu ghép tuần tự toàn bộ `aud_lsb`, dữ liệu vẫn là nhiễu. Như vậy AUD chỉ là một nửa của quan hệ giấu tin.

## 13. Thu thập kích thước VCL NAL

Các NAL type từ `0` đến `31` là VCL NAL. Đây là dữ liệu ảnh thật.

Ta lưu kích thước của từng VCL:

```python
vcl_sizes = []

for nal in nals:
    ntype = nal_type(nal)
    if 0 <= ntype <= 31:
        vcl_sizes.append(len(nal))
```

Hint gọi đây là “cái bóng của bức tranh phía sau”.

## 14. Tạo trend_bit từ biến động kích thước VCL

Ta so kích thước VCL hiện tại với VCL ngay trước đó:

```python
trend_bit = 1 if vcl_sizes[i] > vcl_sizes[i - 1] else 0
```

Nếu VCL hiện tại lớn hơn VCL trước đó, `trend_bit = 1`. Ngược lại, `trend_bit = 0`.

## 15. Khôi phục hidden_bit

Bit thật được tạo bằng quan hệ giữa AUD và biến động kích thước VCL:

```python
hidden_bit = aud_lsb ^ trend_bit
```

Vì vậy nếu chỉ đọc AUD thì thấy nhiễu. Khi kết hợp AUD với VCL trend, ta mới có chuỗi bit đúng.

## 16. Brute force lịch đọc start/step

Sau khi có `hidden_bit`, đọc tuần tự vẫn chưa ra flag. Hint nói “con đường không đi từng viên gạch liền nhau”.

Ta thử đọc theo công thức:

```text
pos = (start + k * step) mod AUD_COUNT
```

Chỉ thử các `step` có:

```python
gcd(step, AUD_COUNT) == 1
```

để đường đi có thể quét qua toàn bộ chuỗi.

Đoạn brute force:

```python
for start in range(len(bits)):
    for step in range(1, len(bits)):
        if gcd(step, len(bits)) != 1:
            continue
        stream = decode_walk(bits, vcl_bits, start, step)
```

## 17. Ghép bit và kiểm packet

Ghép bit theo MSB-first thành byte. Packet đúng có dạng:

```text
magic       2 byte  "AU"
length      2 byte  big-endian
payload     n byte  flag ASCII
crc32       4 byte  crc32(payload)
```

Khi brute force đúng, packet bắt đầu bằng:

```text
AU
```

Sau đó đọc 2 byte độ dài, lấy payload và kiểm CRC32.

## 18. Chạy solver hoàn chỉnh

Script giải nằm tại:

```text
solution/solve.py
```

Chạy:

```bash
python3 solve.py ../public/bunny_aud_suspect.hevc
```

Output:

```text
AUD_NAL_COUNT=542
WALK_START=19
WALK_STEP=73
blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```

## 19. Flag

```text
blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```
