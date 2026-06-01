# H265 Evidence Portal AD - Attack Writeup

## Root Bug

Lỗi lớn của bài là **public preview sanitizer bị sai trust boundary**.

Service có raw H.265 carrier chứa custody marker nội bộ. Raw carrier là dữ liệu private,
chỉ luồng có `operator token` mới được đọc qua `/api/carrier` hoặc `/api/read`.
Nhưng public preview lại được tạo bằng cách copy NAL từ raw carrier sang
`redacted-preview.h265`.

Nói ngắn gọn:

```text
Private carrier -> sanitize hời hợt -> public preview
```

Sai lầm nằm ở chữ "hời hợt". Backend chỉ quan tâm nội dung hình ảnh đã redact, nhưng H.265
không chỉ có frame hình ảnh. Bitstream còn có AUD, SEI, parameter set, metadata, debug
trace và các side-channel khác. Nếu public preview copy những NAL này, flag có thể bị lộ
dù `/api/read` vẫn check token đúng.

## Bề Mặt Recon

Attacker không có token. Những gì attacker có là web public:

```text
http://127.0.0.1:8000/
```

Các endpoint public cần kiểm tra:

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

Endpoint quan trọng nhất là:

```bash
curl http://127.0.0.1:8000/api/cases
```

Nó cho attacker `case id` và `preview_url`. `case id` rất quan trọng vì service dùng nó
làm seed cho một số mask/cadence.

Tải preview:

```bash
curl -L -o preview.h265 http://127.0.0.1:8000/api/cases/<id>/redacted-preview.h265
```

Kiểm tra đây là H.265 thật:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview.h265
```

Nếu ra `codec_name=hevc`, hướng đúng là parse HEVC Annex-B NAL.

## Hướng 1: AUD Timing Channel

Đây là hướng rõ nhất.

Trong H.265, `nal_unit_type` được lấy như sau:

```python
nal_unit_type = (nal[0] >> 1) & 0x3f
```

AUD là NAL type `35`. Service giấu bit vào:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
bit = primary_pic_type & 1
```

Packet marker:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

Trước khi nhúng vào AUD, packet bị xử lý:

```text
packet bits
-> XOR keystream theo case id
-> Manchester encode
-> chèn AUD giả theo cadence
-> ghi bit thật vào primary_pic_type & 1
```

Vì `case id` public, attacker sinh lại được cadence và mask. Hướng khai thác:

```text
preview.h265
-> tách NAL
-> lọc type 35
-> lấy primary_pic_type & 1
-> bỏ decoy theo cadence
-> Manchester decode
-> XOR ngược
-> parse H5AD packet
```

Lệnh:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector aud
```

## Hướng 2: SEI Debug Trace

Nếu đội phòng thủ chỉ strip AUD, attacker không nên dừng lại. Root bug vẫn là preview
copy metadata từ private carrier. Metadata khác có thể vẫn leak.

Bài này có SEI prefix NAL type `39` chứa operator debug trace:

```text
H5DBG || 2-byte length || xor(packet, SHA256("h265-ad-sei-trace:" || case_id || counter))
```

SEI không được `/api/read` sử dụng. Nó mô phỏng debug/custody trace hay gặp trong pipeline
xử lý video. Nhưng nếu preview sanitizer copy SEI sang public preview, attacker vẫn lấy
được packet.

Hướng khai thác:

```text
preview.h265
-> lọc NAL type 39/40
-> tìm magic H5DBG
-> lấy blob đã mask
-> XOR ngược bằng case id
-> parse H5AD packet
```

Lệnh:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector sei
```

Ý nghĩa trong A/D: nếu defender vá kiểu "thấy AUD leak thì strip AUD", attacker chuyển
sang SEI và vẫn ăn flag.

## Hướng 3: Stale Preview Cache

Ngay cả khi defender sửa code đúng hơn, attacker vẫn nên thử artifact cũ.

Service cache preview trên disk:

```python
PREVIEW_DIR / f"{item_id}_redacted_preview.h265"
```

Nếu preview được render trước khi vá, file cũ có thể vẫn còn. Backend thấy file tồn tại
thì trả cache, không render lại bằng sanitizer mới.

Hướng khai thác:

```text
deploy cũ tạo preview lỗi
-> defender vá code
-> preview cache cũ vẫn còn
-> attacker tải lại URL public
-> exploit AUD/SEI trên artifact cũ
```

Lệnh:

```bash
curl -L -o stale_preview.h265 http://127.0.0.1:8000/api/cases/<case_id>/redacted-preview.h265
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector auto
```

Đây là hướng rất thực tế trong A/D: vá code nhưng quên cache/CDN/object storage.

## Hướng 4: Manifest Và Share Recon

`/api/cases` không phải nơi public duy nhất. Attacker cũng nên kiểm tra:

```text
/share/<share_id>
/api/share/<share_id>/manifest.json
```

Các endpoint này có thể cung cấp:

- `case id`
- `preview_url`
- codec
- loại artifact public
- camera/source
- trạng thái preview job

Trong bài hiện tại chúng không trả thẳng flag, nhưng chúng giúp attacker xác định đúng
case và đúng artifact để khai thác. Nếu defender chỉ ẩn `/api/cases` mà để share/manifest
public, attacker vẫn có đường recon.

## Hướng 5: Audit Và Preview Job Recon

Các endpoint như audit trail hoặc preview job queue thường bị xem là "không nhạy cảm".
Nhưng trong A/D, chúng có thể giúp attacker biết:

- case nào mới được checker đặt flag
- preview nào đã render xong
- source/camera nào được dùng
- artifact nào vừa được tải
- cache có thể tồn tại hay chưa

Vì vậy attacker nên kiểm tra:

```bash
curl http://127.0.0.1:8000/api/audit
curl http://127.0.0.1:8000/api/preview-jobs
```

Nếu các endpoint này public, chúng không nhất thiết là bug lấy flag trực tiếp, nhưng là
recon tốt để chọn target.

## Hướng 6: Carrier/Auth Boundary

Luồng hợp lệ:

```text
POST /api/read
POST /api/carrier
```

cần `id + token`. Attacker nên thử token sai để xác nhận có bug auth không. Nếu token sai
mà vẫn đọc được marker hoặc carrier thì đó là bug nghiêm trọng khác.

Trong bài này, auth boundary đúng. Vì vậy hướng chính vẫn là public preview artifact.

## Exploit Tổng Hợp

Exploit hỗ trợ nhiều vector:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector aud
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector sei
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector auto
```

Nếu chưa biết case id:

```bash
python solution/exploit.py http://127.0.0.1:8000 --vector auto
```

`auto` sẽ lấy danh sách public case rồi thử các vector đã biết.

## Kết Luận

Đây là một bài về **artifact sanitization bug**, không phải một bug endpoint đơn lẻ.

Các hướng khai thác đều xoay quanh một câu hỏi:

```text
Public preview còn giữ lại dữ liệu gì từ private carrier?
```

Miễn là câu trả lời còn là "AUD", "SEI", "debug trace", "cache cũ", hoặc "metadata giúp
khôi phục marker", attacker vẫn còn đường khai thác.
