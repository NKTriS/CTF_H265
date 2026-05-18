# CCTV Motion Leak - Writeup

## 1. Xác định file cần phân tích

Challenge cung cấp:

```text
cctv.hevc
cctv_export.log
HINT.txt
```

File chính là:

```text
cctv.hevc
```

File log chỉ dùng để hiểu bối cảnh điều tra.

## 2. Kiểm tra video

Chạy:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 cctv.hevc
```

Kết quả cho thấy đây là video HEVC hợp lệ.

## 3. Kiểm tra metadata dễ thấy

Thử:

```bash
strings cctv.hevc | grep -i HEVC
```

Không thấy flag. Hint cũng nói file không có SEI đáng ngờ, nên không đi theo hướng metadata.

## 4. Parse Annex-B NAL

Tách NAL bằng start code:

```text
00 00 01
00 00 00 01
```

Với mỗi NAL, tính:

```python
nal_type = (nal[0] >> 1) & 0x3f
```

## 5. Lọc VCL NAL

Motion vector thuộc phần dữ liệu ảnh, nên tập trung vào VCL NAL:

```python
0 <= nal_type <= 31
```

Solver chỉ lấy các VCL NAL đủ dài để có byte carrier:

```python
if not nal.is_vcl or len(nal.data) < 80:
    continue
```

## 6. Lấy vị trí carrier

Trong mỗi VCL NAL đủ dài, solver lấy hai byte ở vị trí:

```python
for byte_index in (23, 47):
    locations.append((nal, byte_index))
```

Lấy tối đa 200 record:

```python
MAX_RECORDS = 200
```

## 7. Dựng motion-vector sample

Từ byte carrier, solver dựng giá trị `mv_x`:

```python
raw = nal.data[byte_index]
hidden_bit = raw & 1
magnitude = (((raw >> 1) + idx) % 11 + 1) * 2
mv_x = magnitude + hidden_bit
if idx % 7 == 0:
    mv_x = -mv_x
```

Mục đích là biến bit carrier thành mẫu motion vector có vẻ tự nhiên.

## 8. Lấy bit từ parity của mv_x

Quy tắc:

```text
abs(mv_x) chẵn -> bit 0
abs(mv_x) lẻ   -> bit 1
```

Trong code:

```python
bits.append(abs(mv_x) % 2)
```

## 9. Ghép bit thành text

Ghép mỗi 8 bit thành 1 byte theo MSB-first:

```python
value = 0
for bit in bits[offset:offset + 8]:
    value = (value << 1) | bit
```

Kết quả:

```text
HEVC{motion_leak_in_cctv}
```

## 10. Đối chiếu log

Đọc log:

```bash
cat cctv_export.log
```

User đáng ngờ:

```text
intern01
```

Log không chứa flag, nhưng giúp hoàn thiện bối cảnh điều tra.

## 11. Chạy solver

```bash
python3 solve.py ../public/cctv.hevc
```

Output:

```text
HEVC{motion_leak_in_cctv}
```

## 12. Độ khó suy ra

Bài có khoảng 11 bước: kiểm tra file, loại metadata, parse NAL, lọc VCL, lấy carrier, dựng motion-vector sample, lấy parity và ghép bit.

Độ khó suy ra: **Trung bình** nếu người chơi phải tự suy ra motion-vector channel; **dễ-trung bình** nếu đã có hint mạnh về chuyển động.

## Flag

```text
HEVC{motion_leak_in_cctv}
```
