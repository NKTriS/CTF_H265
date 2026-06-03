# H265 Evidence Portal AD - Writeup Defense

## 1. Nhìn Tổng Quát Lỗi

Bài này có một lỗi lớn: dữ liệu dùng để giữ marker nội bộ bị đưa ra ngoài qua các tài nguyên public.

Trong kịch bản của bài, hệ thống giống một cổng lưu trữ bằng chứng CCTV. Service nhận một case, nhúng marker vào carrier H.265, rồi tạo bản preview đã che nội dung để người ngoài xem. Vấn đề nằm ở chỗ bản preview và một số route phụ vẫn mang theo dữ liệu đáng lẽ chỉ được giữ trong vùng nội bộ.

Nói ngắn gọn:

```text
Marker nằm trong carrier riêng tư.
Preview/share/debug là bề mặt public.
Service đã trộn nhầm dữ liệu riêng tư vào bề mặt public.
```

Vì vậy khi vá, không nên chỉ nhìn một hướng khai thác cụ thể như AUD. Nếu chỉ xóa AUD, attacker vẫn có thể thử SEI, parameter set, diagnostics, thumbnail header, operator debug hoặc preview cache cũ.

Các chỗ cần vá chính:

- Hàm tạo preview H.265: không được copy toàn bộ NAL từ carrier gốc.
- Cache preview: không được trả lại file preview cũ đã sinh bằng code lỗi.
- Route diagnostics: không được public dữ liệu gợi ý marker.
- Route thumbnail: không được nhét dữ liệu nội bộ vào HTTP header.
- Route operator debug: không được deploy endpoint trả marker.

## 2. Vá Hàm Tạo Preview H.265

### Vị trí cần xem

File:

```text
service/backend/app.py
```

Hàm cần vá:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)
```

### Lỗi ở đâu?

Hàm này đọc toàn bộ NAL trong carrier gốc rồi ghi thẳng sang preview public.

Trong H.265, một file bitstream không chỉ có frame hình ảnh. Nó còn có nhiều loại NAL khác:

- VCL NAL: dữ liệu frame hình ảnh.
- AUD NAL type `35`: đánh dấu đơn vị truy cập.
- SEI NAL type `39/40`: dữ liệu phụ.
- VPS/SPS/PPS type `32/33/34`: thông tin cấu hình luồng.
- Các NAL khác có thể chứa metadata, trace hoặc dữ liệu phụ.

Ở bài này, marker có thể bị giấu trong những NAL không phải frame hình ảnh. Khi backend copy tất cả NAL, bản preview vẫn xem được, nhưng đồng thời cũng kéo theo marker.

Đây là lỗi quan trọng nhất của bài.

### Cần vá cái gì?

Không được coi “preview đã che hình ảnh” là an toàn. Preview chỉ an toàn khi dữ liệu phụ cũng đã bị lọc.

Cách vá:

1. Tạo danh sách NAL được phép giữ lại.
2. Chỉ giữ VCL NAL, tức các NAL type từ `0` đến `31`.
3. Không lấy VPS/SPS/PPS từ carrier gốc vì parameter set gốc cũng có thể bị nhét trace.
4. Lấy parameter set sạch từ template public đã biết trước.
5. Bỏ toàn bộ AUD, SEI, metadata, debug NAL và NAL lạ.

Bản vá thêm các hằng số:

```python
PREVIEW_SANITIZER_VERSION = "strip-metadata-v4"
SAFE_PREVIEW_VCL_TYPES = set(range(0, 32))
TRUSTED_PARAMETER_SET_TYPES = {32, 33, 34}
```

Ý nghĩa:

- `SAFE_PREVIEW_VCL_TYPES`: chỉ cho phép frame hình ảnh đi ra preview.
- `TRUSTED_PARAMETER_SET_TYPES`: chỉ dùng để lấy VPS/SPS/PPS sạch từ template.
- `PREVIEW_SANITIZER_VERSION`: dùng để nhận biết preview đã được sinh bằng bản vá mới.

### Vá như nào?

Thêm import `TEMPLATE_PATH` từ `stego.py`:

```python
from stego import StegoError, TEMPLATE_PATH, embed_secret, extract_secret, find_nals, nal_type
```

Sau đó thêm hàm lấy parameter set sạch:

```python
def _trusted_parameter_nals() -> tuple[bytes, ...]:
    return tuple(
        nal for nal in find_nals(TEMPLATE_PATH.read_bytes())
        if nal_type(nal) in TRUSTED_PARAMETER_SET_TYPES
    )
```

Hàm này không đọc parameter set từ case của người dùng. Nó đọc từ template do service kiểm soát. Nhờ vậy attacker không thể nhét marker vào VPS/SPS/PPS của case rồi chờ backend copy sang preview.

Sau đó sửa `_preview_bitstream`:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()

    for nal in _trusted_parameter_nals():
        preview += b"\x00\x00\x00\x01" + nal

    for nal in find_nals(bitstream):
        if nal_type(nal) not in SAFE_PREVIEW_VCL_TYPES:
            continue
        preview += b"\x00\x00\x00\x01" + nal

    return bytes(preview)
```

### Tại sao vá ở đúng chỗ này?

`_preview_bitstream` là cửa chuyển dữ liệu từ vùng riêng tư sang vùng public.

Nếu vá ở đây, ta chặn được cùng lúc nhiều hướng:

- Hướng AUD: AUD type `35` không còn được copy.
- Hướng SEI: SEI type `39/40` không còn được copy.
- Hướng parameter set: VPS/SPS/PPS từ carrier gốc không còn được copy.
- Hướng NAL lạ: mọi NAL ngoài frame hình ảnh đều bị bỏ.

Nếu chỉ vá ở `extract_secret`, attacker vẫn có thể tải preview và tự phân tích bằng script riêng. Vì vậy phải vá ở nơi sinh artifact public, không phải ở nơi đọc marker hợp lệ.

## 3. Vá Preview Cache Cũ

### Vị trí cần xem

File:

```text
service/backend/app.py
```

Các hàm liên quan:

```python
def _render_preview(item_id: str) -> Path:
    ...

@app.get("/api/cases/<item_id>/redacted-preview.h265")
def redacted_preview(item_id: str):
    ...
```

### Lỗi ở đâu?

Ngay cả khi code tạo preview đã được vá, file preview cũ vẫn có thể còn nằm trong thư mục cache:

```text
PREVIEW_DIR/<case_id>_redacted_preview.h265
```

Nếu backend chỉ kiểm tra:

```python
if not preview_path.exists():
    preview_path = _render_preview(item_id)
```

thì backend sẽ trả lại file cũ nếu file đã tồn tại. File cũ có thể vẫn chứa AUD, SEI hoặc trace trong parameter set.

Đây là lỗi hay gặp trong A/D: đội vá source code nhưng quên xóa dữ liệu đã sinh trước khi vá.

### Cần vá cái gì?

Cần làm cho cache có phiên bản. Preview chỉ được coi là hợp lệ nếu nó được sinh bởi đúng phiên bản sanitizer hiện tại.

Thêm hàm kiểm tra cache:

```python
def _preview_cache_fresh(item_id: str) -> bool:
    preview_path = PREVIEW_DIR / f"{item_id}_redacted_preview.h265"
    version_path = PREVIEW_DIR / f"{item_id}_redacted_preview.version"

    if not preview_path.exists():
        return False

    try:
        return version_path.read_text(encoding="utf-8").strip() == PREVIEW_SANITIZER_VERSION
    except OSError:
        return False
```

Sửa `_render_preview` để ghi file version:

```python
def _render_preview(item_id: str) -> Path:
    source_path = EVIDENCE_DIR / f"{item_id}.h265"
    preview_path = PREVIEW_DIR / f"{item_id}_redacted_preview.h265"
    version_path = PREVIEW_DIR / f"{item_id}_redacted_preview.version"

    bitstream = source_path.read_bytes()
    preview_path.write_bytes(_preview_bitstream(bitstream))
    version_path.write_text(PREVIEW_SANITIZER_VERSION, encoding="utf-8")

    _set_preview_job(item_id, "ready")
    return preview_path
```

Sửa route trả preview:

```python
if not _preview_cache_fresh(item_id):
    preview_path = _render_preview(item_id)
```

### Tại sao phải vá cache?

Vì defense không chỉ là sửa code cho case mới. Trong A/D, flag được checker đặt theo từng round. Nếu một preview lỗi đã được sinh trong round trước, attacker có thể quay lại tải đúng file cũ đó.

Sau khi vá cache:

- File chưa có version sẽ bị coi là cũ.
- File có version khác sẽ bị coi là cũ.
- Backend buộc phải render lại preview bằng hàm `_preview_bitstream` đã vá.

## 4. Vá Diagnostics Public

### Vị trí cần xem

Route:

```text
GET /api/cases/<case_id>/diagnostics.json
```

Trong code:

```python
@app.get("/api/cases/<item_id>/diagnostics.json")
def case_diagnostics(item_id: str):
    ...
```

### Lỗi ở đâu?

Route này public nhưng lại lấy marker nội bộ:

```python
secret = _extract_case_secret(item_id)
```

Sau đó trả `custody_hint`:

```python
custody_hint=_masked_hex(secret, item_id, b"h265-ad-diag:")
```

Dù không trả flag trực tiếp, đây vẫn là dữ liệu có thể giải ngược nếu attacker biết cách tạo keystream từ `case_id` và nhãn mask.

### Cần vá cái gì?

Không để diagnostics public trả bất kỳ dữ liệu nào được sinh từ marker.

Bản vá tắt hẳn route:

```python
@app.get("/api/cases/<item_id>/diagnostics.json")
def case_diagnostics(item_id: str):
    return jsonify(ok=False, error="diagnostics disabled"), 404
```

### Tại sao vá như vậy?

Diagnostics là dữ liệu phục vụ vận hành nội bộ, không phải một phần của public preview.

Không nên sửa kiểu:

```python
custody_hint = custody_hint[:8]
```

hoặc đổi tên field. Những cách đó vẫn giữ dữ liệu dẫn xuất từ marker trong response. Defense đúng là route public không được đụng vào marker ngay từ đầu.

## 5. Vá Header Thumbnail

### Vị trí cần xem

Route:

```text
GET /api/cases/<case_id>/thumbnail.jpg
```

Trong code:

```python
@app.get("/api/cases/<item_id>/thumbnail.jpg")
def case_thumbnail(item_id: str):
    ...
```

### Lỗi ở đâu?

Thumbnail trả body là ảnh JPEG rỗng, nhưng header lại chứa dữ liệu nội bộ:

```python
headers={
    "X-H265-Custody-Mask": "h265-ad-thumb:",
    "X-H265-Custody-Hint": _masked_hex(secret, item_id, b"h265-ad-thumb:"),
}
```

Nhiều người khi vá chỉ nhìn body response. Nhưng trong HTTP, header cũng là dữ liệu public. Attacker có thể dùng `curl -i` hoặc `curl -D -` để đọc header.

### Cần vá cái gì?

Không gọi `_extract_case_secret` trong route thumbnail.

Không trả các header liên quan đến custody/marker.

Bản vá:

```python
@app.get("/api/cases/<item_id>/thumbnail.jpg")
def case_thumbnail(item_id: str):
    if not _valid_id(item_id):
        return jsonify(ok=False, error="bad id"), 400
    if item_id not in _load_meta():
        return jsonify(ok=False, error="not found"), 404

    _audit("thumbnail_downloaded", item_id)
    body = b"\xff\xd8\xff\xd9"
    return Response(body, mimetype="image/jpeg")
```

### Tại sao vá ở route này?

Vì thumbnail là tài nguyên public. Public thumbnail chỉ nên trả ảnh đại diện. Nó không cần biết marker, không cần đọc carrier, và không cần trả metadata nhạy cảm.

Nếu route public không cần secret thì không nên gọi `_extract_case_secret`. Đây là nguyên tắc quan trọng: dữ liệu bí mật không nên đi vào nhánh xử lý public, kể cả sau đó có “mask” hoặc “encode”.

## 6. Vá Operator Debug Route

### Vị trí cần xem

Route:

```text
GET /api/operator/cases/<case_id>/debug-marker
```

Trong code:

```python
@app.get("/api/operator/cases/<item_id>/debug-marker")
def operator_debug_marker(item_id: str):
    ...
```

### Lỗi ở đâu?

Route này trả marker trực tiếp:

```python
return jsonify(ok=True, id=item_id, marker=secret)
```

Nó được đặt dưới đường dẫn operator. Nếu credential operator của instance bị lộ,
hoặc attacker lấy được session operator bằng một lỗi khác, route này trở thành
đường lấy cờ thẳng.

### Cần vá cái gì?

Không deploy route trả marker trong môi trường thi.

Bản vá:

```python
@app.get("/api/operator/cases/<item_id>/debug-marker")
def operator_debug_marker(item_id: str):
    return jsonify(ok=False, error="debug marker disabled"), 404
```

### Tại sao không chỉ đổi mật khẩu?

Đổi mật khẩu là tốt, nhưng chưa đủ.

Lý do:

- Mật khẩu có thể bị lộ qua cấu hình, log hoặc dùng lại.
- Session operator có thể bị chiếm bằng lỗi khác.
- Route debug trả marker là chức năng quá nguy hiểm để tồn tại trong môi trường thi.

Với A/D, defense đúng là loại bỏ chức năng debug trả bí mật, không chỉ che nó sau một lớp đăng nhập yếu.

## 7. Đồng Bộ Checker

### Vấn đề cần tránh

Trong hệ thống A/D thật, checker sẽ gọi:

```text
put(host, port, flag)
get(host, port, flag_id)
check(host, port)
```

Attacker thường chỉ biết `flag_id`, không được biết token bí mật mà checker dùng khi put.

Nếu checker tự tạo token từ `case_id` public, attacker có thể bỏ qua toàn bộ phần stego và gọi route đọc hợp lệ:

```text
POST /api/read
```

### Bài hiện tại xử lý như nào?

Checker hiện không dùng công thức kiểu:

```text
token = sha256("h265-ad-checker-token:" || case_id)[:32]
```

Thay vào đó, checker sinh token từ cả `case_id` và flag thật:

```text
token = sha256("h265-ad-checker-token-v2:" || case_id || ":" || flag)[:32]
```

Lý do cách này ổn trong checker: mode `get` luôn được hệ thống chấm truyền lại flag thật để so sánh, còn attacker thì không biết flag trước khi khai thác. Vì vậy attacker không thể tự tính token chỉ từ `case_id`.

Mode `put` cũng chỉ in ra:

```text
flag_x
```

Không in token ra flag id public.

### Tại sao vẫn cần ghi phần này?

Vì nếu người ra đề đổi checker rồi vô tình đưa token vào flag id public, bài sẽ biến thành lỗi checker chứ không còn là bài H.265 stego nữa. Khi đó mọi bản vá H.265 đều mất ý nghĩa.

Vì vậy sau khi sửa service, vẫn cần test `checker put/get` để chắc luồng hợp lệ hoạt động, nhưng không được để attacker suy ra token từ dữ liệu public.

## 8. Kiểm Tra Sau Khi Vá

Sau khi áp dụng bản vá, nên kiểm tra theo thứ tự từ bề mặt chính đến bề mặt phụ.

### Kiểm tra preview không còn AUD, SEI, parameter set bẩn

Tải preview:

```powershell
curl.exe -L -o preview_after_patch.h265 http://127.0.0.1:8000/api/cases/<case_id>/redacted-preview.h265
```

Đếm các NAL nghi ngờ:

```powershell
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('preview_after_patch.h265').read_bytes(); print({t:sum(1 for n in find_nals(data) if nal_type(n)==t) for t in (35,39,40)})"
```

Kết quả mong muốn:

```text
{35: 0, 39: 0, 40: 0}
```

Kiểm tra parameter set không còn trace `H5PSET`:

```powershell
Select-String -Path preview_after_patch.h265 -Pattern "H5PSET"
```

Không có output là đúng.

### Kiểm tra cache đã được render lại

Sau khi tải preview, trong thư mục preview phải có file version:

```text
<case_id>_redacted_preview.version
```

Nội dung file phải là:

```text
strip-metadata-v4
```

Nếu không có file version, nghĩa là service có thể vẫn đang trả cache cũ.

### Kiểm tra diagnostics đã tắt

```powershell
curl.exe -i http://127.0.0.1:8000/api/cases/<case_id>/diagnostics.json
```

Kết quả mong muốn:

```text
HTTP/1.1 404
```

Response không được có `custody_hint`.

### Kiểm tra thumbnail không còn header nhạy cảm

```powershell
curl.exe -i http://127.0.0.1:8000/api/cases/<case_id>/thumbnail.jpg
```

Kết quả không được có:

```text
X-H265-Custody-Mask
X-H265-Custody-Hint
```

### Kiểm tra operator debug đã tắt

```powershell
curl.exe -i http://127.0.0.1:8000/api/operator/cases/<case_id>/debug-marker
```

Kết quả mong muốn:

```text
HTTP/1.1 404
```

Không được trả `marker`.

### Kiểm tra exploit không còn lấy được flag

Sau khi vá, chạy lại exploit trên cùng `case_id`:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --id <case_id>
```

Kết quả mong muốn là không in ra flag.

Nếu exploit vẫn lấy được flag, xem nó lấy qua hướng nào rồi vá tiếp đúng bề mặt đó:

- Nếu lấy qua preview: kiểm tra `_preview_bitstream` và cache.
- Nếu lấy qua diagnostics: kiểm tra route diagnostics.
- Nếu lấy qua thumbnail: kiểm tra header.
- Nếu lấy qua operator: kiểm tra debug route, session operator và nguồn lộ credential.

## 9. Cách Áp Dụng Bản Vá

Bản vá nằm ở:

```text
solution/defense.patch
```

Áp dụng từ thư mục bài:

```powershell
cd H:\Lab_giau_tin\CTF_H265\attack_defense_stego\01_h265_nal_vault_ad
git apply --ignore-space-change solution\defense.patch
```

Nếu muốn quay về bản vulnerable để test lại:

```powershell
git apply -R --ignore-space-change solution\defense.patch
```

Lưu ý PowerShell có biến `$PID` mặc định là read-only. Nếu cần đọc file `.lab_service.pid`, không dùng:

```powershell
$pid = Get-Content .lab_service.pid
```

Dùng tên biến khác:

```powershell
$servicePid = Get-Content .lab_service.pid
Stop-Process -Id $servicePid -Force
```

## 10. Kết Luận Defense

Defense của bài này cần theo nguyên tắc:

```text
Public artifact không được chứa dữ liệu sinh từ marker.
Public route không được đọc marker.
Cache cũ phải bị vô hiệu hóa sau khi đổi sanitizer.
Debug route không được tồn tại trong môi trường thi.
Checker không được công khai token hoặc sinh token từ flag id public.
```

Nếu chỉ vá một điểm, bài vẫn có thể bị khai thác qua điểm khác. Cách vá đúng là đóng toàn bộ đường đưa dữ liệu nội bộ ra ngoài, đặc biệt là các đường tưởng như vô hại như metadata video, HTTP header, diagnostics và cache.
