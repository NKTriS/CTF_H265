# Night Shift Camera - Writeup

## 1. Khảo sát file được cung cấp

Challenge cung cấp:

```text
cctv.hevc
cctv_export.log
HINT.txt
```

File chính là `cctv.hevc`. File `cctv_export.log` dùng để hoàn thiện bối cảnh điều tra, không phải nơi chứa flag.

Kiểm tra video:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 cctv.hevc
```

Kết quả cho thấy đây là video HEVC hợp lệ.

## 2. Loại hướng metadata đơn giản

Thử tìm chuỗi dễ thấy:

```bash
strings cctv.hevc | grep -i blockChainPTIT
```

Không có kết quả. Hint cũng nói video không có SEI đáng ngờ, nên hướng giải không phải metadata hay chuỗi ASCII rõ ràng.

Nội dung gợi ý tập trung vào "chuyển động", vì vậy cần nhìn vào phần dữ liệu ảnh/VCL và giả lập motion-vector sample.

## 3. Parse NAL và lọc VCL NAL

File HEVC Annex-B được tách bằng start code:

```text
00 00 01
00 00 00 01
```

Với mỗi NAL, lấy type:

```python
nal_type = (nal[0] >> 1) & 0x3f
```

Motion vector thuộc phần dữ liệu ảnh, nên solver chỉ lấy VCL NAL:

```python
0 <= nal_type <= 31
```

Đồng thời bỏ qua NAL quá ngắn:

```python
if not nal.is_vcl or len(nal.data) < 80:
    continue
```

## 4. Chọn vị trí carrier trong VCL

Trong mỗi VCL NAL đủ dài, solver lấy hai byte cố định:

```python
for byte_index in (23, 47):
    locations.append((nal, byte_index))
```

Tổng cộng lấy tối đa 200 record:

```python
MAX_RECORDS = 200
```

Các byte này đóng vai trò carrier, tức nơi chứa bit ẩn.

## 5. Dựng motion-vector sample từ byte carrier

Solver không đọc motion vector thật từ encoder, mà dựng một trace motion-vector mô phỏng từ byte carrier:

```python
raw = nal.data[byte_index]
hidden_bit = raw & 1
magnitude = (((raw >> 1) + idx) % 11 + 1) * 2
mv_x = magnitude + hidden_bit
if idx % 7 == 0:
    mv_x = -mv_x
```

Điểm quan trọng là bit ẩn nằm ở parity của `mv_x`. Phần magnitude và dấu âm/dương chỉ làm dữ liệu trông giống sample chuyển động tự nhiên hơn.

## 6. Trích bit từ parity của mv_x

Quy tắc:

```text
abs(mv_x) chẵn -> bit 0
abs(mv_x) lẻ   -> bit 1
```

Trong code:

```python
bits.append(abs(mv_x) % 2)
```

Sau khi thu đủ bit, ghép mỗi 8 bit thành 1 byte theo MSB-first.

## 7. Ghép bit thành flag

Đoạn ghép byte:

```python
value = 0
for bit in bits[offset:offset + 8]:
    value = (value << 1) | bit
```

Kết quả thu được:

```text
blockChainPTIT{mvx_leaks}
```

## 8. Đối chiếu log điều tra

Đọc log:

```bash
cat cctv_export.log
```

Log cho biết user đáng ngờ:

```text
intern01
```

Thông tin này không phải flag, nhưng giúp hoàn thiện câu chuyện điều tra: video đã bị export ra ngoài bởi user này.

## 9. Chạy solver xác nhận

```bash
python3 solve.py ../public/cctv.hevc
```

Output:

```text
blockChainPTIT{mvx_leaks}
```

Flag:

```text
blockChainPTIT{mvx_leaks}
```
