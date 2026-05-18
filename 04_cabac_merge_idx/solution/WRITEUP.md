# CABAC Merge Index - Writeup

## 1. Xác định file cần phân tích

Challenge cung cấp:

```text
warehouse-source.mp4
merge_trace.csv
incident_note.txt
HINT.txt
```

Flag không nằm trực tiếp trong video. Dữ liệu cần phân tích là:

```text
merge_trace.csv
```

## 2. Kiểm tra video nguồn

Chạy:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 warehouse-source.mp4
```

Video là HEVC hợp lệ trong MP4.

## 3. Đọc ghi chú sự cố

Mở:

```bash
cat incident_note.txt
```

Ghi chú giúp xác định đây là bài phân tích trace codec, không phải tìm flag bằng `strings` trong video.

## 4. Xem cấu trúc merge_trace.csv

Chạy:

```bash
head merge_trace.csv
```

File CSV chứa các trường liên quan đến merge mode, trong đó có:

```text
merge_flag
candidate_count
usable
merge_idx
```

## 5. Lọc record usable

Không phải dòng nào cũng chứa bit hợp lệ. Chỉ lấy dòng thỏa:

```text
merge_flag == 1
candidate_count >= 2
usable == 1
```

Trong code:

```python
if int(row["merge_flag"]) == 1 and int(row["candidate_count"]) >= 2 and int(row["usable"]) == 1:
    ...
```

## 6. Lấy bit từ merge_idx

Với mỗi record hợp lệ, lấy parity của `merge_idx`:

```text
merge_idx chẵn -> bit 0
merge_idx lẻ   -> bit 1
```

Trong code:

```python
bits.append(int(row["merge_idx"]) % 2)
```

## 7. Xác định số bit cần đọc

Flag có 29 ký tự, tương ứng:

```text
29 * 8 = 232 bit
```

Solver lấy:

```python
bits[:29 * 8]
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
HEVC{cabac_merge_idx_channel}
```

## 9. Xác định tài khoản đáng ngờ

Từ `incident_note.txt`, tài khoản đáng ngờ là:

```text
cam-admin
```

Thông tin này phục vụ bối cảnh điều tra, không phải flag.

## 10. Chạy solver

```bash
python3 solve.py ../public/merge_trace.csv
```

Output:

```text
HEVC{cabac_merge_idx_channel}
```

## Flag

```text
HEVC{cabac_merge_idx_channel}
```
