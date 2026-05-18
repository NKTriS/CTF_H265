# Borrowed Shortcut - Writeup

## 1. Khảo sát file được cung cấp

Challenge cung cấp:

```text
warehouse-source.mp4
merge_trace.csv
incident_note.txt
HINT.txt
```

File video giúp xác nhận bối cảnh, nhưng flag không nằm trực tiếp trong video. File quan trọng nhất là `merge_trace.csv`, đây là trace codec đã được trích xuất sẵn.

Kiểm tra video:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 warehouse-source.mp4
```

Video là HEVC hợp lệ trong container MP4.

## 2. Đọc bối cảnh và xác định dữ liệu cần phân tích

Đọc ghi chú:

```bash
cat incident_note.txt
```

Ghi chú cho thấy bài này không đi theo hướng `strings` hay metadata trong video, mà tập trung vào trace merge mode.

Xem các cột trong CSV:

```bash
head merge_trace.csv
```

Các cột quan trọng:

```text
merge_flag
candidate_count
usable
merge_idx
```

## 3. Lọc record có thể mang dữ liệu

Không phải mọi dòng trong trace đều hợp lệ để lấy bit. Solver chỉ giữ những dòng thỏa:

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

Điều kiện này loại các block không dùng merge mode, không đủ candidate hoặc được đánh dấu không dùng cho kênh ẩn.

## 4. Trích bit từ merge_idx

Với mỗi record hợp lệ, lấy parity của `merge_idx`:

```text
merge_idx chẵn -> bit 0
merge_idx lẻ   -> bit 1
```

Trong code:

```python
bits.append(int(row["merge_idx"]) % 2)
```

Đây là kênh ẩn của bài: không thay đổi nội dung video trực tiếp, mà dùng lựa chọn merge candidate trong trace.

## 5. Xác định số bit cần đọc

Flag của bài có 29 ký tự, tương ứng:

```text
29 * 8 = 232 bit
```

Solver lấy 232 bit đầu tiên từ các record hợp lệ:

```python
bits[:29 * 8]
```

## 6. Ghép bit thành text

Ghép mỗi 8 bit thành 1 byte theo MSB-first:

```python
value = 0
for bit in chunk:
    value = (value << 1) | bit
```

Kết quả:

```text
blockChainPTIT{merge_path_01}
```

## 7. Đối chiếu thông tin điều tra

Trong `incident_note.txt`, tài khoản đáng ngờ là:

```text
cam-admin
```

Thông tin này phục vụ câu chuyện điều tra, còn flag được khôi phục từ parity của `merge_idx`.

## 8. Chạy solver xác nhận

```bash
python3 solve.py ../public/merge_trace.csv
```

Output:

```text
blockChainPTIT{merge_path_01}
```

Flag:

```text
blockChainPTIT{merge_path_01}
```
