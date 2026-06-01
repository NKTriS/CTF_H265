# H265 Evidence Portal AD - Writeup Attack

## 1. Hiểu Lỗi Chính

Bài này không phải lỗi quên kiểm tra mật khẩu ở `/api/read`. Route đó vẫn yêu cầu đúng
`case id` và `operator token`.

Lỗi chính nằm ở cách hệ thống tạo file preview công khai:

```text
file H.265 gốc riêng tư
-> tạo file xem trước công khai
-> copy nhầm dữ liệu phụ từ file gốc sang file công khai
```

File H.265 không chỉ có hình ảnh. Nó gồm nhiều khối nhỏ gọi là NAL. Một số NAL chứa
khung hình, một số NAL khác chứa dữ liệu phụ như nhịp video, thông tin kiểm tra, dấu vết
gỡ lỗi hoặc dữ liệu nội bộ.

Service muốn tạo `redacted-preview.h265` để người ngoài xem CCTV đã che thông tin nhạy
cảm. Nhưng backend copy quá nhiều NAL từ file gốc sang preview. Vì vậy flag/custody
marker bị lộ trong preview dù attacker không có token.

## 2. Bước 1 - Mở Web Và Xác Định Chức Năng

Mục tiêu của bước này là hiểu service đang làm gì.

Mở:

```text
http://127.0.0.1:8000/
```

Nhìn trên giao diện sẽ thấy đây là cổng lưu trữ bằng chứng CCTV. Có các chức năng:

- Import CCTV evidence.
- Verify custody marker bằng `case id` và `operator token`.
- Xem case public.
- Tải redacted preview.

Điểm quan trọng: attacker không có `operator token`, nên chưa thể dùng luồng hợp lệ
`/api/read` để đọc marker. Ta phải tìm dữ liệu public.

## 3. Bước 2 - Liệt Kê Case Công Khai

Mục tiêu của bước này là lấy `case id` và đường dẫn preview.

Chạy:

```bash
curl http://127.0.0.1:8000/api/cases
```

Kết quả trả về có dạng:

```json
{
  "ok": true,
  "items": [
    {
      "id": "flag_1780132060_da66f92c",
      "preview_url": "/api/cases/flag_1780132060_da66f92c/redacted-preview.h265",
      "share_url": "/share/...",
      "manifest_url": "/api/share/.../manifest.json"
    }
  ]
}
```

Cần ghi lại hai trường:

- `id`: mã case, ví dụ `flag_1780132060_da66f92c`.
- `preview_url`: đường dẫn tải file preview.

`case id` rất quan trọng. Trong bài này service dùng `case id` làm hạt giống để tạo mặt
nạ và nhịp chèn bit. Vì vậy chỉ cần có preview và `case id`, attacker đã có đủ dữ liệu
để thử giải.

## 4. Bước 3 - Tải File Preview

Mục tiêu của bước này là lấy file H.265 công khai về máy để phân tích.

Chạy:

```bash
curl -L -o preview.h265 http://127.0.0.1:8000/api/cases/<case_id>/redacted-preview.h265
```

Ví dụ:

```bash
curl -L -o preview.h265 http://127.0.0.1:8000/api/cases/flag_1780132060_da66f92c/redacted-preview.h265
```

Kiểm tra file có được tải về không:

```bash
dir preview.h265
```

Nếu file có kích thước khác 0, tiếp tục kiểm tra đây có phải H.265 thật không.

## 5. Bước 4 - Kiểm Tra Preview Là H.265

Mục tiêu của bước này là xác nhận đây là file video H.265 thật, không phải file text hoặc
file giả.

Chạy:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview.h265
```

Kết quả mong đợi:

```text
codec_name=hevc
width=640
height=360
```

Nếu thấy `codec_name=hevc`, ta biết file này là HEVC/H.265. Hướng khai thác đúng là phân
tích các NAL bên trong file.

## 6. Bước 5 - Hiểu Cách Tách NAL

Mục tiêu của bước này là hiểu cách đọc cấu trúc H.265.

H.265 Annex-B dùng start code để ngăn cách các NAL:

```text
00 00 01
00 00 00 01
```

Sau mỗi start code là một NAL. Loại NAL được tính từ byte đầu tiên:

```python
nal_type = (nal[0] >> 1) & 0x3f
```

Trong bài này có hai loại NAL cần chú ý:

- `35`: AUD, dùng để giấu bit theo nhịp video.
- `39/40`: SEI, có thể chứa dấu vết gỡ lỗi.

## 7. Hướng 1 - Khai Thác Qua AUD

Mục tiêu của hướng này là lấy flag từ AUD NAL type `35`.

Điều kiện để dùng hướng AUD:

- Preview public vẫn còn AUD NAL type `35`.
- Attacker biết `case id`.
- Service chưa vá hoặc chỉ vá những phần không liên quan tới AUD.

Kiểm tra nhanh preview có AUD hay không:

```bash
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('preview.h265').read_bytes(); print(sum(1 for n in find_nals(data) if nal_type(n)==35))"
```

Nếu kết quả lớn hơn `0`, file preview vẫn còn AUD để phân tích.

Với AUD, bit bị giấu nằm trong `primary_pic_type`:

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

Quá trình khai thác chi tiết:

1. Tách toàn bộ NAL trong `preview.h265`.
2. Giữ lại NAL có `nal_type == 35`.
3. Với mỗi AUD, lấy `primary_pic_type & 1` để thu được chuỗi bit thô.
4. Dùng `case id` để sinh lại nhịp chèn AUD giả.
5. Bỏ các bit nằm trong AUD giả, giữ lại bit thật.
6. Giải mã Manchester: cặp `01` là bit `0`, cặp `10` là bit `1`.
7. Dùng `case id` để sinh lại dòng XOR, rồi XOR ngược.
8. Kiểm tra packet có magic `H5AD`.
9. Đọc độ dài flag và kiểm tra `crc32`.

Chạy exploit theo hướng AUD:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector aud
```

Ví dụ:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector aud
```

Nếu thành công, kết quả là flag:

```text
blockChainPTIT{...}
```

Nếu thất bại, thường có vài khả năng:

- Không còn AUD trong preview: defender đã strip AUD.
- Có AUD nhưng nhịp bit sai: `case id` không đúng.
- Packet không có `H5AD`: bit thu được không phải marker thật hoặc đã bị sửa.
- CRC sai: dữ liệu bị thiếu hoặc preview đã bị làm sạch một phần.

## 8. Hướng 2 - Khai Thác Qua SEI

Mục tiêu của hướng này là lấy flag nếu đội phòng thủ chỉ xóa AUD nhưng vẫn để SEI.

Điều kiện để dùng hướng SEI:

- Preview public còn SEI NAL type `39` hoặc `40`.
- Trong SEI còn dấu `H5DBG`.
- Attacker biết `case id`.
- Defender mới chỉ vá AUD hoặc chưa lọc dữ liệu phụ.

Kiểm tra nhanh preview có SEI hay không:

```bash
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('preview.h265').read_bytes(); print({t:sum(1 for n in find_nals(data) if nal_type(n)==t) for t in (39,40)})"
```

Nếu type `39` hoặc `40` lớn hơn `0`, tiếp tục tìm dấu `H5DBG`.

SEI trong bài này có dấu vết gỡ lỗi dạng:

```text
H5DBG || độ dài 2 byte || packet đã XOR
```

Packet bên trong vẫn là packet chứa flag. Nó chỉ bị XOR bằng khóa sinh từ `case id`.

Quá trình khai thác chi tiết:

1. Tách toàn bộ NAL trong preview.
2. Giữ NAL type `39` hoặc `40`.
3. Bỏ 2 byte header NAL, đọc phần payload.
4. Tìm chuỗi `H5DBG`.
5. Sau `H5DBG` là 2 byte độ dài.
6. Lấy đúng số byte dữ liệu đã bị XOR.
7. Sinh dòng byte bằng SHA256 với nhãn `h265-ad-sei-trace:` và `case id`.
8. XOR ngược để lấy packet thật.
9. Parse packet `H5AD || length || flag || crc32`.

Chạy exploit theo hướng SEI:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector sei
```

Khi hướng SEI thành công mà hướng AUD thất bại, đó là dấu hiệu đội phòng thủ đã vá một
dấu hiệu cụ thể nhưng chưa vá đúng lỗi tổng quát của preview.

## 9. Hướng 3 - Khai Thác File Preview Cũ

Mục tiêu của hướng này là kiểm tra xem service có còn trả file preview cũ sau khi vá
không.

Điều kiện để dùng hướng này:

- File preview lỗi đã từng được render trước khi vá.
- Sau khi vá, backend vẫn ưu tiên trả file cache nếu file tồn tại.
- Đội phòng thủ chưa xóa cache hoặc chưa gắn phiên bản cho bộ làm sạch preview.

Service lưu preview đã render trong bộ nhớ đệm:

```text
PREVIEW_DIR/<case_id>_redacted_preview.h265
```

Luồng tấn công:

```text
trước khi vá: preview lỗi đã được tạo
-> sau khi vá: file cũ vẫn nằm trong bộ nhớ đệm
-> attacker tải lại preview public
-> exploit chạy trên file cũ
```

Chạy:

```bash
curl -L -o stale_preview.h265 http://127.0.0.1:8000/api/cases/<case_id>/redacted-preview.h265
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector auto
```

Sau khi tải `stale_preview.h265`, kiểm tra file đó còn dữ liệu nguy hiểm không:

```bash
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('stale_preview.h265').read_bytes(); print({t:sum(1 for n in find_nals(data) if nal_type(n)==t) for t in (35,39,40)})"
```

Nếu kết quả còn `35`, `39` hoặc `40`, file cache vẫn là bản lỗi.

Điểm cần nhớ: trong hướng này attacker không cần tìm lỗi mới trong code hiện tại. Attacker
đánh vào file cũ mà service vẫn đang public.

## 10. Bước 6 - Kiểm Tra Share Và Manifest

Mục tiêu của bước này là tìm thêm đường lấy `case id` hoặc `preview_url`.

Nếu `/api/cases` bị ẩn, attacker vẫn nên thử:

```text
/share/<share_id>
/api/share/<share_id>/manifest.json
```

Nếu chưa biết `share_id`, có thể lấy nó từ `/api/cases`. Nếu `/api/cases` bị ẩn, attacker
có thể thử tìm link share trong giao diện `/case/<id>`, log public hoặc dữ liệu được
người dùng chia sẻ.

Các endpoint này có thể lộ:

- `case id`
- đường dẫn preview
- loại codec
- camera/source
- trạng thái preview

Cách dùng:

1. Lấy `manifest_url`.
2. Mở manifest để xác nhận đây là file `redacted-preview`.
3. Lấy `preview_url`.
4. Tải preview.
5. Chạy lại hướng AUD/SEI.

## 11. Bước 7 - Kiểm Tra Nhật Ký Và Hàng Đợi Preview

Mục tiêu của bước này là tìm case mới hoặc preview vừa được render.

Thử:

```bash
curl http://127.0.0.1:8000/api/audit
curl http://127.0.0.1:8000/api/preview-jobs
```

Nếu public, chúng có thể cho biết:

- case nào mới được tạo
- preview nào đã render xong
- file nào vừa được tải
- bộ nhớ đệm có khả năng đã tồn tại hay chưa

Cách tận dụng:

- Nếu audit cho biết `case_imported`, ưu tiên case mới vì có khả năng chứa flag checker mới đặt.
- Nếu preview job là `ready`, có thể tải preview ngay.
- Nếu preview vừa được tải nhiều lần, có thể có đội khác cũng đang khai thác case đó.
- Nếu job chưa ready, chờ vài giây rồi tải lại preview.

## 12. Bước 8 - Kiểm Tra Route Private

Mục tiêu của bước này là xác nhận `/api/read` và `/api/carrier` có bị lỗi phân quyền
không.

Hai route private là:

```text
POST /api/read
POST /api/carrier
```

Lệnh thử token sai:

```bash
curl -X POST http://127.0.0.1:8000/api/read ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"<case_id>\",\"token\":\"wrong-token\"}"
```

Kết quả đúng là bị từ chối. Nếu server trả `secret` thì không cần phân tích H.265 nữa,
vì đó là lỗi phân quyền trực tiếp.

Trong bài này, hai route này làm đúng. Vì vậy hướng chính vẫn là preview công khai.

## 13. Bước 9 - Chạy Exploit Tổng Hợp

Nếu đã có `case id`, chạy:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector auto
```

Nếu chưa có `case id`, để exploit tự lấy danh sách public case:

```bash
python solution/exploit.py http://127.0.0.1:8000 --vector auto
```

Có thể ép từng hướng:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector aud
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector sei
```

Nếu `aud` fail nhưng `sei` thành công, preview đã bị vá AUD nhưng còn SEI. Nếu cả hai
fail nhưng preview cũ tải từ cache vẫn có AUD/SEI, vấn đề nằm ở cache.

Khi thành công, exploit in ra flag động do checker đặt.

## 14. Kết Luận

Tư duy giải bài này là luôn hỏi:

```text
File preview công khai còn giữ lại dữ liệu gì từ file gốc riêng tư?
```

Nếu preview còn AUD, SEI, dấu vết gỡ lỗi, file cache cũ hoặc thông tin giúp khôi phục
marker, attacker vẫn còn đường lấy flag.
