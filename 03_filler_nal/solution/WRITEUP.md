# Filler NAL Channel - Writeup

## 1. Xác định file cần phân tích

Challenge cung cấp:

```text
warehouse-clean.hevc
warehouse-suspect.hevc
export_audit.log
HINT.txt
```

File cần lấy flag là:

```text
warehouse-suspect.hevc
```

File `warehouse-clean.hevc` dùng để đối chiếu cấu trúc.

## 2. Kiểm tra video

Chạy:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 warehouse-suspect.hevc
```

File là HEVC hợp lệ và vẫn phát bình thường.

## 3. So sánh kích thước hai file

Chạy:

```bash
ls -lh warehouse-clean.hevc warehouse-suspect.hevc
```

File suspect lớn hơn một chút. Đây là dấu hiệu có NAL phụ hoặc dữ liệu đệm được thêm vào.

## 4. Parse Annex-B NAL

Tách NAL bằng start code:

```text
00 00 01
00 00 00 01
```

Với mỗi NAL, tính:

```python
nal_type = (data[header] >> 1) & 0x3f
```

## 5. Tìm Filler Data NAL

Trong HEVC:

```text
NAL type 38 = Filler Data NAL
```

Solver định nghĩa:

```python
FD_NUT = 38
```

và chỉ xử lý NAL type `38`.

## 6. Đếm byte 0xff trong Filler payload

Filler Data NAL thường chứa nhiều byte `0xff`.

Trong mỗi Filler NAL, đếm số byte `0xff` liên tiếp ở đầu payload:

```python
ff_count = 0
for byte in payload:
    if byte == 0xff:
        ff_count += 1
    else:
        break
```

## 7. Lấy bit từ parity độ dài filler

Quy tắc:

```text
ff_count chẵn -> bit 0
ff_count lẻ   -> bit 1
```

Trong code:

```python
bits.append(ff_count % 2)
```

## 8. Ghép bit thành text

Ghép mỗi 8 bit thành 1 byte theo MSB-first:

```python
value = 0
for bit in chunk:
    value = (value << 1) | bit
```

Kết quả:

```text
HEVC{filler_nal_length_channel}
```

## 9. Đối chiếu log

File `export_audit.log` giúp hiểu bối cảnh xuất video, nhưng không chứa flag. Flag nằm trong Filler NAL của file suspect.

## 10. Chạy solver

```bash
python3 solve.py ../public/warehouse-suspect.hevc
```

Output:

```text
HEVC{filler_nal_length_channel}
```

## 11. Độ khó suy ra

Bài có khoảng 10 bước: so sánh clean/suspect, parse NAL, nhận diện Filler NAL, đếm độ dài filler và ghép bit.

Độ khó suy ra: **Trung bình nhẹ** nếu không biết Filler Data NAL; **dễ** nếu người chơi đã quen cấu trúc NAL HEVC.

## Flag

```text
HEVC{filler_nal_length_channel}
```
