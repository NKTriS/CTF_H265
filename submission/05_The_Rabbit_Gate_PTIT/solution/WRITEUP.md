# The Rabbit Gate - Writeup

## 1. Khảo sát file được cung cấp

Challenge cung cấp 3 file:

```text
bunny_aud_suspect.hevc
bunny_aud_suspect.mp4
HINT.txt
```

File `.mp4` dùng để xem nhanh nội dung video, còn file `.hevc` là raw HEVC Annex-B bitstream, phù hợp hơn để phân tích NAL unit.

Kiểm tra nhanh bằng `ffprobe`:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate,duration \
  -of default=noprint_wrappers=1 bunny_aud_suspect.mp4
```

Kết quả cho thấy đây là video HEVC hợp lệ:

```text
codec_name=hevc
width=1920
height=1080
r_frame_rate=30/1
duration=18.000000
```

Thử tìm flag trực tiếp bằng `strings` không có kết quả:

```bash
strings bunny_aud_suspect.hevc | grep -i blockChainPTIT
```

Vì vậy flag không nằm thẳng dưới dạng ASCII trong file.

## 2. Suy luận hướng phân tích từ hint

Hint của bài:

```text
Đừng soi từng khung hình; hãy đứng ở cửa ra vào của mỗi nhịp video.
Người gác cửa thì thầm rất khẽ; cái bóng của bức tranh phía sau chỉ rõ lời thì thầm ấy nên lật hay giữ.
Con đường không đi từng viên gạch liền nhau; có vài viên chỉ được đặt để đánh lạc hướng.
Nếu nghe đúng nhịp, lá thư mở đầu bằng hai chữ `AU`, sau đó là độ dài và một dấu kiểm ở cuối.
```

Các ý quan trọng:

- Không nên bắt đầu bằng OCR, LSB pixel hay trích frame ảnh.
- "Cửa ra vào" của mỗi nhịp video gợi đến Access Unit Delimiter, tức AUD NAL trong HEVC.
- "Cái bóng của bức tranh phía sau" gợi đến dữ liệu ảnh VCL đi kèm sau AUD.
- "Không đi từng viên gạch liền nhau" nghĩa là bit không được đọc tuần tự.
- Packet đúng bắt đầu bằng `AU`, có độ dài và checksum.

Do đó hướng giải là parse HEVC bitstream, tìm AUD NAL, kết hợp nó với biến động của VCL NAL, rồi thử thứ tự đọc phù hợp.

## 3. Tách NAL unit trong HEVC Annex-B

HEVC Annex-B phân tách NAL bằng start code:

```text
00 00 01
00 00 00 01
```

Đoạn code dùng để tách NAL:

```python
def find_nals(data: bytes):
    starts = []
    i = 0
    while i < len(data) - 3:
        if data[i:i + 3] == b"\x00\x00\x01":
            starts.append((i, 3))
            i += 3
        elif data[i:i + 4] == b"\x00\x00\x00\x01":
            starts.append((i, 4))
            i += 4
        else:
            i += 1

    for idx, (start, sc_len) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(data)
        yield data[start + sc_len:end]
```

Sau khi có từng NAL, lấy `nal_unit_type` bằng công thức:

```python
nal_type = (nal[0] >> 1) & 0x3f
```

Trong HEVC:

- NAL type `0..31` là VCL, tức dữ liệu ảnh.
- NAL type `35` là AUD, tức Access Unit Delimiter.

Thống kê NAL cho thấy type `35` xuất hiện đều theo nhịp video. Đây là vị trí cần phân tích.

## 4. Trích bit thô từ AUD và VCL

AUD trong file này thường có dạng:

```text
46 01 xx
```

Byte `xx` chứa `primary_pic_type` ở 3 bit cao:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
aud_bit = primary_pic_type & 1
```

Nếu chỉ lấy `aud_bit` tuần tự thì dữ liệu vẫn nhiễu. Hint nói cần đọc cùng "cái bóng của bức tranh phía sau", nên ta lấy thêm xu hướng kích thước VCL.

Với mỗi VCL NAL, so kích thước của nó với VCL trước đó:

```python
vcl_bit = 1 if vcl_sizes[i] > vcl_sizes[(i - 1) % len(vcl_sizes)] else 0
```

Bit ứng viên được tạo bằng XOR:

```python
hidden_bit = aud_bit ^ vcl_bit
```

Ý nghĩa: AUD giữ một phần tín hiệu, còn biến động kích thước VCL quyết định bit đó được giữ hay lật.

## 5. Tìm thứ tự đọc đúng

Sau khi tạo được danh sách `hidden_bit`, đọc tuần tự vẫn chưa ra plaintext. Theo hint, dữ liệu phải được đọc bằng bước nhảy cố định:

```text
pos = (start + k * step) mod AUD_COUNT
```

Ta brute force `start` và `step`. Điều kiện:

```python
gcd(step, AUD_COUNT) == 1
```

Điều kiện này giúp đường đi quét được toàn bộ chuỗi bit thay vì lặp lại trong một vòng nhỏ.

Sau mỗi lần dựng lại bitstream, ghép bit MSB-first thành byte và kiểm tra packet có format:

```text
magic   = "AU"
length  = 2 byte big-endian
payload = dữ liệu cần lấy
crc32   = crc32(payload)
```

Nếu packet không bắt đầu bằng `AU`, length không hợp lệ hoặc CRC32 sai thì bỏ qua.

Đoạn kiểm tra chính:

```python
raw = bits_to_bytes(walked)
if raw[:2] != b"AU":
    return b""

size = struct.unpack(">H", raw[2:4])[0]
plain = raw[4:4 + size]
crc_expected = struct.unpack(">I", raw[4 + size:8 + size])[0]

if zlib.crc32(plain) != crc_expected:
    return b""
```

## 6. Chạy solver

Script giải nằm trong:

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

Trong đó:

- `AUD_NAL_COUNT=542`: số AUD NAL tìm được.
- `WALK_START=19`: vị trí bắt đầu đúng.
- `WALK_STEP=73`: bước nhảy đúng để đọc lại chuỗi bit.

## 7. Flag

```text
blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```
