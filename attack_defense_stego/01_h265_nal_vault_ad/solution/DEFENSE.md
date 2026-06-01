# H265 Evidence Portal AD - Writeup Defense

## 1. Lỗ Hổng Tổng Quát

Bài này không chỉ có một endpoint hở. Lỗi lõi là:

```text
Dữ liệu nội bộ của carrier gốc hoặc luồng vận hành nội bộ bị đưa ra bề mặt public/debug.
```

Các đường lấy cờ có thể xuất hiện ở nhiều lớp:

- preview H.265 giữ AUD type `35`
- preview H.265 giữ SEI type `39/40`
- preview H.265 giữ parameter set type `32/33/34` bị nhét trace `H5PSET`
- preview cache cũ sinh bởi code lỗi
- diagnostics public trả `custody_hint`
- thumbnail public trả custody hint trong HTTP header
- operator debug route trả marker
- token checker yếu nếu token suy ra được từ `case_id`

Vì vậy defense đúng không phải là “xóa mỗi AUD” hoặc “xóa mỗi SEI”. Defense đúng là chặn mọi đường đưa marker/custody data ra ngoài public.

## 2. Vá Preview H.265

### Vá cái gì?

Hàm nguy hiểm là:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)
```

Đoạn này copy toàn bộ NAL từ carrier gốc sang preview. Như vậy AUD, SEI, parameter set giả và metadata nội bộ đều đi ra file công khai.

### Vá như nào?

Không lấy VPS/SPS/PPS từ carrier gốc. Chỉ lấy parameter set sạch từ template public, rồi chỉ copy VCL frame đã sanitize từ carrier:

```python
PREVIEW_SANITIZER_VERSION = "strip-metadata-v4"
SAFE_PREVIEW_VCL_TYPES = set(range(0, 32))
TRUSTED_PARAMETER_SET_TYPES = {32, 33, 34}

def _trusted_parameter_nals() -> tuple[bytes, ...]:
    return tuple(
        nal for nal in find_nals(TEMPLATE_PATH.read_bytes())
        if nal_type(nal) in TRUSTED_PARAMETER_SET_TYPES
    )

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

### Tại sao vá ở đây?

Đây là điểm chuyển dữ liệu từ vùng riêng tư sang vùng public. Vá ở đây sẽ chặn cùng lúc:

- AUD leak
- SEI leak
- parameter set leak
- debug NAL lạ
- metadata phụ không cần thiết

## 3. Vá Cache Preview Cũ

### Vá cái gì?

Nếu preview lỗi đã render trước khi vá, file cũ vẫn có thể nằm trong:

```text
PREVIEW_DIR/<case_id>_redacted_preview.h265
```

Nếu backend thấy file tồn tại rồi trả luôn, attacker vẫn tải được bản cũ.

### Vá như nào?

Gắn version cho bộ sanitize:

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

Khi render preview:

```python
version_path.write_text(PREVIEW_SANITIZER_VERSION, encoding="utf-8")
```

Khi trả preview:

```python
if not _preview_cache_fresh(item_id):
    preview_path = _render_preview(item_id)
```

### Tại sao vá ở đây?

Vì code mới đúng không có nghĩa file cũ đã sạch. Cache cũ là bản sao của lỗi cũ.

## 4. Vá Diagnostics Public

### Vá cái gì?

Route này không được public:

```text
/api/cases/<case_id>/diagnostics.json
```

Nó trả `custody_hint` có thể XOR ngược bằng `case_id`.

### Vá như nào?

Tắt route trong môi trường thi:

```python
def case_diagnostics(item_id: str):
    return jsonify(ok=False, error="diagnostics disabled"), 404
```

### Tại sao vá ở đây?

Diagnostics là dữ liệu vận hành nội bộ. Public preview không cần nó.

## 5. Vá Header Thumbnail

### Vá cái gì?

Thumbnail không được trả header nội bộ:

```text
X-H265-Custody-Mask
X-H265-Custody-Hint
```

### Vá như nào?

Chỉ trả ảnh, không trả custody header:

```python
return Response(body, mimetype="image/jpeg")
```

### Tại sao vá ở đây?

Header HTTP cũng là dữ liệu public. Đừng chỉ kiểm body response mà quên header.

## 6. Vá Operator Debug

### Vá cái gì?

Route debug này không được bật trong bài thi:

```text
/api/operator/cases/<case_id>/debug-marker
```

### Vá như nào?

Tắt route:

```python
def operator_debug_marker(item_id: str):
    return jsonify(ok=False, error="debug marker disabled"), 404
```

Đồng thời đổi mật khẩu mặc định nếu vẫn giữ operator console.

### Tại sao vá ở đây?

Debug route là đường tắt đọc marker. Dù H.265 đã sạch, route debug còn bật thì attacker vẫn lấy cờ.

## 7. Về Token Checker Yếu

Nếu token có thể suy ra từ `case_id`, attacker có thể gọi `/api/read` như người hợp lệ. Với bài thi thật, không nên để:

```text
token = sha256("h265-ad-checker-token:" || case_id)[:32]
```

Cách đúng là token phải là dữ liệu bí mật do checker lưu, không suy ra được từ flag id public. Nếu nền tảng bắt buộc flag id public, token không được là hàm của flag id.

## 8. Patch Mẫu

Patch mẫu nằm ở:

```text
solution/defense.patch
```

Patch này vá các điểm chính trong service:

- lọc preview theo VCL sạch
- dùng parameter set sạch từ template
- version cache preview
- tắt diagnostics leak
- xóa custody header ở thumbnail
- tắt operator debug marker
