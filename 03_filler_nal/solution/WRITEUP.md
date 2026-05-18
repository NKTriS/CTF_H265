# Empty Crate - Writeup

## 1. Khảo sát file được cung cấp

Challenge cung cấp:

```text
warehouse-clean.hevc
warehouse-suspect.hevc
export_audit.log
HINT.txt
```

File cần lấy flag là `warehouse-suspect.hevc`. File `warehouse-clean.hevc` dùng để đối chiếu vì đây là bản sạch cùng nội dung.

Kiểm tra video suspect:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 warehouse-suspect.hevc
```

File là HEVC hợp lệ và vẫn phát bình thường.

## 2. So sánh hai file

So kích thước:

```bash
ls -lh warehouse-clean.hevc warehouse-suspect.hevc
```

File suspect lớn hơn một chút. Với một video vẫn phát bình thường, phần chênh lệch này thường gợi ý có NAL phụ, padding hoặc dữ liệu đệm được thêm vào.

Hint cũng nhắc đến "khoảng trống" và thứ được sinh ra để bỏ qua. Trong HEVC, điều này gợi đến Filler Data NAL.

## 3. Parse NAL trong Annex-B

Tách NAL bằng start code:

```text
00 00 01
00 00 00 01
```

Với mỗi NAL, tính type:

```python
nal_type = (data[header] >> 1) & 0x3f
```

Trong HEVC:

```text
NAL type 38 = Filler Data NAL
```

Solver định nghĩa:

```python
FD_NUT = 38
```

và chỉ xử lý các NAL type `38`.

## 4. Đọc payload của Filler Data NAL

Filler Data NAL thường chứa nhiều byte `0xff`. Bài này không giấu trực tiếp bằng chữ trong filler, mà giấu qua độ dài của đoạn `0xff` ở đầu payload.

Đếm số byte `0xff` liên tiếp:

```python
ff_count = 0
for byte in payload:
    if byte == 0xff:
        ff_count += 1
    else:
        break
```

Chỉ phần `0xff` liên tiếp ở đầu payload được dùng làm tín hiệu.

## 5. Trích bit từ parity của độ dài filler

Quy tắc:

```text
ff_count chẵn -> bit 0
ff_count lẻ   -> bit 1
```

Trong code:

```python
bits.append(ff_count % 2)
```

Như vậy mỗi Filler Data NAL đóng góp một bit.

## 6. Ghép bit thành chuỗi

Sau khi thu bit từ các Filler NAL, ghép mỗi 8 bit thành 1 byte theo MSB-first:

```python
value = 0
for bit in chunk:
    value = (value << 1) | bit
```

Kết quả:

```text
blockChainPTIT{filler_voids_01}
```

## 7. Đối chiếu log

File `export_audit.log` giúp hiểu bối cảnh xuất video, nhưng không chứa flag. Flag nằm trong Filler Data NAL của file suspect.

## 8. Chạy solver xác nhận

```bash
python3 solve.py ../public/warehouse-suspect.hevc
```

Output:

```text
blockChainPTIT{filler_voids_01}
```

Flag:

```text
blockChainPTIT{filler_voids_01}
```
