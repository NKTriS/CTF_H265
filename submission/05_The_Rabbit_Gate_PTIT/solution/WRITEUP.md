# The Rabbit Gate - Writeup

## 1. Xác định file chính của challenge

Challenge cung cấp:

```text
bunny_aud_suspect.hevc
bunny_aud_suspect.mp4
HINT.txt
```

File `.mp4` dùng để xem nhanh nội dung video. File cần phân tích chính là `bunny_aud_suspect.hevc`, vì đây là raw HEVC Annex-B bitstream, dễ tách NAL unit hơn.

## 2. Kiểm tra video và loại hướng tìm flag trực tiếp

Kiểm tra codec:

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

Video là HEVC hợp lệ. Tiếp theo thử tìm flag plaintext:

```bash
strings bunny_aud_suspect.hevc | grep -i blockChainPTIT
```

Không có kết quả, nên flag không nằm trực tiếp dưới dạng chuỗi ASCII trong file.

## 3. Đọc hint để chọn hướng phân tích

Hint:

```text
Đừng soi từng khung hình; hãy đứng ở cửa ra vào của mỗi nhịp video.
Người gác cửa thì thầm rất khẽ; cái bóng của bức tranh phía sau chỉ rõ lời thì thầm ấy nên lật hay giữ.
Con đường không đi từng viên gạch liền nhau; có vài viên chỉ được đặt để đánh lạc hướng.
Nếu nghe đúng nhịp, lá thư mở đầu bằng hai chữ `AU`, sau đó là độ dài và một dấu kiểm ở cuối.
```

Từ hint có thể suy ra:

- Không nên tập trung vào pixel, OCR hoặc frame ảnh.
- "Cửa ra vào" gợi tới Access Unit Delimiter, tức AUD NAL trong HEVC.
- "Bức tranh phía sau" gợi tới VCL NAL, tức phần dữ liệu ảnh đi kèm.
- "Không đi từng viên gạch liền nhau" gợi ý cần đọc bit theo bước nhảy.
- Packet đúng có magic `AU`, có length và checksum.

Vì vậy hướng giải là phân tích cấu trúc NAL của HEVC.

## 4. Tách các NAL unit trong file HEVC

HEVC Annex-B dùng start code để phân tách NAL:

```text
00 00 01
00 00 00 01
```

Code tách NAL:

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

Sau bước này, mỗi phần tử trả về là một NAL unit không còn start code.

## 5. Phân loại NAL unit

Trong HEVC, `nal_unit_type` nằm trong byte đầu của NAL header:

```python
def nal_type(nal: bytes) -> int:
    if len(nal) < 2:
        return -1
    return (nal[0] >> 1) & 0x3f
```

Các type cần chú ý:

- `0..31`: VCL NAL, chứa dữ liệu ảnh.
- `35`: AUD, Access Unit Delimiter.

Khi thống kê NAL type, type `35` xuất hiện đều theo nhịp video. Điều này khớp với hình ảnh "người gác cửa" trong hint.

## 6. Lấy bit ứng viên từ AUD

AUD trong file này thường có dạng:

```text
46 01 xx
```

Byte `xx` chứa trường `primary_pic_type` ở 3 bit cao:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
aud_bit = primary_pic_type & 1
```

Ở bước này chưa lấy được flag ngay. Nếu chỉ ghép tuần tự `aud_bit`, dữ liệu vẫn nhiễu. Điều đó cho thấy AUD chỉ giữ một phần của kênh ẩn.

## 7. Lấy bit điều chỉnh từ VCL NAL

Hint nói "cái bóng của bức tranh phía sau", nên cần dùng dữ liệu ảnh VCL đi kèm để quyết định giữ hay lật bit từ AUD.

Ta lưu kích thước của các VCL NAL:

```python
vcl_sizes = []
for nal in find_nals(data):
    ntype = nal_type(nal)
    if 0 <= ntype <= 31:
        vcl_sizes.append(len(nal))
```

Sau đó so kích thước VCL hiện tại với VCL trước đó:

```python
vcl_bit = 1 if vcl_sizes[i] > vcl_sizes[(i - 1) % len(vcl_sizes)] else 0
```

`vcl_bit = 1` nếu kích thước tăng, ngược lại là `0`.

## 8. Khôi phục chuỗi bit ẩn

Bit ẩn được tạo từ quan hệ giữa AUD và biến động kích thước VCL:

```python
hidden_bit = aud_bit ^ vcl_bit
```

Ý nghĩa:

- AUD cho bit gốc rất nhỏ.
- VCL trend cho biết bit đó cần giữ nguyên hay đảo.
- Nếu chỉ đọc một trong hai phần thì không đủ để ra dữ liệu đúng.

Sau bước này ta có một chuỗi bit ứng viên dài bằng số AUD NAL.

## 9. Tìm bước nhảy đọc bit

Đọc chuỗi bit tuần tự vẫn không ra packet hợp lệ. Theo hint, đường đi không lấy từng bit liền nhau mà đi theo bước nhảy cố định:

```text
pos = (start + k * step) mod AUD_COUNT
```

Ta brute force `start` và `step`. Với mỗi `step`, chỉ giữ các giá trị thỏa:

```python
gcd(step, AUD_COUNT) == 1
```

Điều kiện này giúp đường đi có thể quét qua toàn bộ chuỗi thay vì mắc trong một vòng lặp nhỏ.

## 10. Kiểm tra packet bằng magic, length và CRC32

Mỗi chuỗi bit sau khi đi theo `start/step` được ghép MSB-first thành byte. Packet đúng có cấu trúc:

```text
magic   = "AU"
length  = 2 byte big-endian
payload = dữ liệu flag
crc32   = crc32(payload)
```

Đoạn kiểm tra:

```python
raw = bits_to_bytes(walked)
if len(raw) < 8 or raw[:2] != b"AU":
    return b""

size = struct.unpack(">H", raw[2:4])[0]
plain = raw[4:4 + size]
crc_expected = struct.unpack(">I", raw[4 + size:8 + size])[0]

if zlib.crc32(plain) != crc_expected:
    return b""
```

Magic `AU` giúp nhận ra đúng packet. CRC32 giúp loại các trường hợp brute force sai nhưng tình cờ có byte giống ASCII.

## 11. Chạy solver và lấy flag

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

Flag:

```text
blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```
