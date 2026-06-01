# H265 Evidence Portal AD - Writeup Attack

## 1. Ý Chính Của Lỗi

Bài này không phải lỗi quên kiểm tra mật khẩu ở `/api/read`. Route đó vẫn yêu cầu đúng
`case id` và `operator token`.

Lỗi lớn nằm ở cách hệ thống tạo file xem trước công khai:

```text
File gốc riêng tư -> tạo bản xem trước công khai -> copy nhầm dữ liệu phụ
```

File H.265 không chỉ có hình ảnh. Nó gồm nhiều khối nhỏ gọi là NAL. Có NAL chứa khung
hình, nhưng cũng có NAL chứa dữ liệu phụ như thời gian, ghi chú kiểm tra, thông tin debug
hoặc dấu vết nội bộ.

Service muốn tạo `redacted-preview.h265` để người ngoài xem CCTV đã che thông tin nhạy
cảm. Nhưng khi tạo file này, backend copy quá nhiều NAL từ file gốc sang file công khai.
Vì vậy flag/custody marker bị lộ trong file preview dù người tấn công không có token.

## 2. Những Gì Người Tấn Công Nhìn Thấy

Người tấn công chỉ có địa chỉ web, ví dụ:

```text
http://127.0.0.1:8000/
```

Các đường dẫn nên kiểm tra:

```text
GET /
GET /api/cases
GET /case/<id>
GET /share/<share_id>
GET /api/share/<share_id>/manifest.json
GET /api/cases/<id>/redacted-preview.h265
GET /api/audit
GET /api/preview-jobs
```

Đường dẫn quan trọng nhất:

```bash
curl http://127.0.0.1:8000/api/cases
```

Nó trả về `case id` và đường dẫn tải preview. `case id` không chỉ là tên vụ việc. Trong
bài này nó còn được dùng làm hạt giống để tạo mặt nạ và nhịp chèn bit.

Tải preview:

```bash
curl -L -o preview.h265 http://127.0.0.1:8000/api/cases/<case_id>/redacted-preview.h265
```

Kiểm tra file:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview.h265
```

Nếu thấy `codec_name=hevc`, đây là file H.265 thật. Ta cần phân tích cấu trúc H.265,
không phải chỉ dùng `strings`.

## 3. Hướng Tấn Công Qua AUD

AUD là một loại NAL trong H.265, có mã loại `35`. Bình thường AUD dùng để đánh dấu ranh
giới hoặc nhịp của hình ảnh. Trong bài này service lợi dụng AUD để giấu bit.

Cách lấy loại NAL:

```python
nal_type = (nal[0] >> 1) & 0x3f
```

Với AUD, dữ liệu cần lấy nằm ở bit thấp của `primary_pic_type`:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
bit = primary_pic_type & 1
```

Flag không được ghi thẳng. Service đóng gói flag như sau:

```text
H5AD || độ dài 2 byte || flag || crc32(flag)
```

Sau đó service làm khó thêm:

```text
đổi packet thành bit
-> XOR theo case id
-> mã Manchester
-> chèn AUD giả
-> ghi bit thật vào AUD
```

Người tấn công làm ngược lại:

```text
tải preview
-> tách các NAL
-> lấy AUD type 35
-> lấy bit từ primary_pic_type
-> bỏ AUD giả theo case id
-> giải Manchester
-> XOR ngược
-> đọc packet H5AD
```

Chạy:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector aud
```

## 4. Hướng Tấn Công Qua SEI

Nếu đội phòng thủ chỉ thấy AUD leak rồi xóa AUD khỏi preview, vẫn chưa đủ.

H.265 còn có SEI, mã loại thường gặp là `39` hoặc `40`. SEI hay được dùng để chứa thông
tin phụ. Trong bài này, service có một dấu vết gỡ lỗi trong SEI với dạng:

```text
H5DBG || độ dài 2 byte || packet đã được XOR
```

Packet bên trong vẫn là packet chứa flag, chỉ bị XOR bằng khóa sinh từ `case id`.

Vì preview copy cả dữ liệu phụ từ file gốc, SEI cũng có thể xuất hiện trong file công
khai. Khi đó người tấn công làm như sau:

```text
tải preview
-> tìm NAL type 39/40
-> tìm chuỗi H5DBG
-> lấy dữ liệu đã XOR
-> XOR ngược bằng case id
-> đọc packet H5AD
```

Chạy:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector sei
```

Ý nghĩa: nếu chỉ vá AUD, người tấn công chuyển sang SEI và vẫn có thể lấy flag.

## 5. Hướng Tấn Công Qua File Preview Cũ

Kể cả khi đội phòng thủ đã sửa code để xóa AUD và SEI, vẫn còn một hướng thực tế:
file preview cũ.

Service lưu preview đã render ở thư mục cache:

```text
PREVIEW_DIR/<case_id>_redacted_preview.h265
```

Nếu file preview lỗi đã được tạo trước khi vá, backend có thể thấy file đã tồn tại và trả
luôn file cũ, không render lại bằng code mới.

Luồng tấn công:

```text
trước khi vá: preview lỗi đã được tạo
-> sau khi vá: cache cũ vẫn còn
-> người tấn công tải lại preview public
-> exploit chạy trên file cũ
```

Chạy:

```bash
curl -L -o stale_preview.h265 http://127.0.0.1:8000/api/cases/<case_id>/redacted-preview.h265
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector auto
```

Đây là lỗi rất hay gặp ngoài thực tế: vá code nhưng quên xóa cache, CDN hoặc file đã
export trước đó.

## 6. Hướng Thu Thập Thông Tin Qua Share Và Manifest

Nếu `/api/cases` bị ẩn, chưa chắc bài đã hết đường.

Người tấn công nên thử:

```text
/share/<share_id>
/api/share/<share_id>/manifest.json
```

Những nơi này có thể lộ:

- `case id`
- đường dẫn preview
- loại codec
- camera/source
- trạng thái file preview

Các thông tin này không phải flag, nhưng giúp tìm đúng file cần khai thác.

## 7. Hướng Thu Thập Thông Tin Qua Nhật Ký Và Hàng Đợi Preview

Audit và hàng đợi render preview thường bị xem nhẹ. Nhưng trong A/D, chúng giúp chọn mục
tiêu tốt hơn.

Thử:

```bash
curl http://127.0.0.1:8000/api/audit
curl http://127.0.0.1:8000/api/preview-jobs
```

Nếu public, chúng có thể cho biết:

- case nào mới được tạo
- preview nào đã render xong
- file nào vừa được tải
- cache có khả năng đã tồn tại hay chưa

Đây là thông tin hỗ trợ tấn công, không nhất thiết là nơi lấy flag trực tiếp.

## 8. Kiểm Tra Đường Private

Hai route private là:

```text
POST /api/read
POST /api/carrier
```

Chúng cần `case id` và `operator token`. Người tấn công có thể thử token sai để kiểm tra
có lỗi phân quyền không. Nếu token sai mà vẫn đọc được marker hoặc raw carrier thì đó là
một lỗi khác rất nặng.

Trong bài này, hai route này làm đúng. Hướng tấn công chính vẫn là file preview công khai.

## 9. Chạy Exploit Tổng Hợp

Exploit có thể thử từng hướng:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector aud
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector sei
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector auto
```

Nếu chưa biết `case id`:

```bash
python solution/exploit.py http://127.0.0.1:8000 --vector auto
```

Khi thành công, exploit in ra flag động do checker đặt.

## 10. Kết Luận

Câu hỏi chính của bài là:

```text
File preview công khai còn giữ lại dữ liệu gì từ file gốc riêng tư?
```

Nếu preview còn AUD, SEI, dấu vết gỡ lỗi, bộ nhớ đệm cũ hoặc thông tin giúp khôi phục marker,
người tấn công vẫn còn đường lấy flag.
