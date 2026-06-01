# H265 Evidence Portal AD - Writeup Defense

## 1. Lỗ Hổng Tổng Quát

Lỗi nằm ở cách tạo file preview công khai.

File gốc H.265 là dữ liệu riêng tư. Nó không chỉ chứa hình ảnh, mà còn có nhiều NAL chứa
dữ liệu phụ:

- VCL frame: khung hình video.
- VPS/SPS/PPS: thông tin cần để giải mã video.
- AUD: dữ liệu nhịp/ranh giới ảnh.
- SEI: dữ liệu phụ.
- dấu vết gỡ lỗi: thông tin kiểm tra nội bộ.
- custody marker: dữ liệu dùng để kiểm tra chuỗi bằng chứng.

Preview công khai chỉ nên giữ phần đủ để xem video đã che thông tin nhạy cảm. Nhưng bản
lỗi copy cả dữ liệu phụ từ file gốc sang preview. Vì vậy flag có thể bị lộ qua AUD, SEI
hoặc file preview cũ trong cache.

Mục tiêu vá:

```text
Preview công khai chỉ chứa dữ liệu cần để phát video.
Mọi dữ liệu nội bộ hoặc dữ liệu phụ không cần thiết phải bị loại bỏ.
Preview cũ tạo bởi code lỗi không được dùng lại.
```

## 2. Vá Hàm Tạo Preview

### Vá cái gì?

Cần vá hàm tạo preview:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        ...
    return bytes(preview)
```

Bản lỗi copy gần như toàn bộ NAL sang preview:

```python
preview += b"\x00\x00\x00\x01" + nal
```

Điều này nguy hiểm vì nó đưa cả AUD, SEI và dấu vết gỡ lỗi ra file công khai.

### Vá như nào?

Không dùng kiểu vá "thấy loại nào nguy hiểm thì chặn loại đó". Ví dụ chỉ chặn AUD:

```python
if nal_type(nal) == 35:
    continue
```

Cách này chưa đủ vì SEI type `39/40` vẫn có thể leak.

Nên dùng danh sách cho phép:

```python
SAFE_PREVIEW_NAL_TYPES = set(range(0, 32)) | {32, 33, 34}
```

Sau đó chỉ copy các NAL nằm trong danh sách này:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        if nal_type(nal) not in SAFE_PREVIEW_NAL_TYPES:
            continue
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)
```

### Tại sao vá ở đây?

Vì đây là nơi dữ liệu từ file gốc riêng tư đi ra file preview công khai. Nếu chặn ở đây,
mọi đường tải preview đều nhận file đã được làm sạch.

### Tại sao chỉ giữ các loại đó?

- `0..31`: các NAL chứa khung hình.
- `32`: VPS.
- `33`: SPS.
- `34`: PPS.

Các loại này đủ để preview vẫn là H.265 hợp lệ. Những loại khác không cần cho mục tiêu
public preview của bài, nên không nên copy ra ngoài.

## 3. Vá Đường Lộ Qua SEI Và Dấu Vết Gỡ Lỗi

### Vá cái gì?

Carrier có thể chứa SEI type `39/40`. Trong bài này SEI có dấu vết gỡ lỗi dạng:

```text
H5DBG || length || masked_packet
```

Nếu SEI bị copy sang preview, attacker có thể dùng `case id` để giải lại packet và lấy
flag.

### Vá như nào?

Không copy SEI sang preview. Với allowlist ở trên, SEI tự động bị loại vì type `39/40`
không nằm trong danh sách cho phép.

### Tại sao vá ở đây?

SEI là dữ liệu phụ. Người xem preview không cần SEI để xem nội dung CCTV đã redact. Nếu
giữ SEI, defender phải đảm bảo mọi SEI đều sạch, rất dễ sót. Loại bỏ toàn bộ SEI khỏi
preview công khai là cách an toàn hơn.

## 4. Vá Bộ Nhớ Đệm Preview

### Vá cái gì?

Sau khi sửa code tạo preview, file preview cũ vẫn có thể tồn tại:

```text
PREVIEW_DIR/<case_id>_redacted_preview.h265
```

Nếu backend chỉ kiểm tra file có tồn tại hay không, nó sẽ trả lại file cũ sinh bởi code
lỗi.

### Vá như nào?

Thêm phiên bản cho bộ làm sạch preview:

```python
PREVIEW_SANITIZER_VERSION = "strip-metadata-v3"
```

Khi render preview, ghi thêm file version:

```python
version_path = PREVIEW_DIR / f"{item_id}_redacted_preview.version"
version_path.write_text(PREVIEW_SANITIZER_VERSION, encoding="utf-8")
```

Tạo hàm kiểm tra cache còn dùng được không:

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

Trong route tải preview, đổi từ:

```python
if not preview_path.exists():
    preview_path = _render_preview(item_id)
```

sang:

```python
if not _preview_cache_fresh(item_id):
    preview_path = _render_preview(item_id)
```

### Tại sao vá ở đây?

Vì attacker không quan tâm code mới đã đúng hay chưa nếu file cũ vẫn được trả về. Bộ nhớ
đệm cũ chính là một bản sao của lỗi. Gắn phiên bản giúp backend tự biết file nào được tạo
bởi bộ làm sạch mới, file nào cần render lại.

## 5. Giữ Route Private Đúng Chức Năng

### Vá cái gì?

Hai route này là luồng hợp lệ:

```text
POST /api/read
POST /api/carrier
```

Chúng phải tiếp tục yêu cầu `case id` và `operator token`.

### Vá như nào?

Không tắt hai route này. Chỉ đảm bảo token sai bị từ chối:

```text
token sai -> 403/forbidden
token đúng -> checker đọc lại được flag
```

### Tại sao vá ở đây?

Attack-defense cần checker đặt flag và đọc lại flag. Nếu vá bằng cách tắt `/api/read`
hoặc làm `/api/carrier` hỏng, service sẽ chết dưới checker. Defense đúng là chặn đường
public leak, không phá luồng hợp lệ.

## 6. Kiểm Soát Các Endpoint Public

### Vá cái gì?

Các endpoint public có thể vẫn tồn tại:

```text
/api/cases
/share/<share_id>
/api/share/<share_id>/manifest.json
/api/audit
/api/preview-jobs
```

Nhưng chúng không được trả dữ liệu nhạy cảm.

### Vá như nào?

Các endpoint này có thể trả:

- `case id`
- camera/source
- trạng thái preview
- đường dẫn preview công khai

Không được trả:

- token
- flag/marker
- raw carrier path
- debug packet
- đường dẫn nội bộ trong server
- URL riêng tư có quyền tải file gốc

### Tại sao vá ở đây?

Trong sản phẩm thật, public share và manifest là chức năng hợp lý. Không cần tắt hết.
Nhưng nếu các endpoint này làm lộ dữ liệu nội bộ, attacker sẽ dùng chúng để tìm đúng
case hoặc lấy thẳng dữ liệu nhạy cảm.

## 7. Bản Vá Cuối Cần Có Gì?

Bản vá cuối cần đủ ba phần:

1. Tạo preview bằng danh sách NAL được phép.
2. Loại bỏ SEI/AUD/debug metadata khỏi preview.
3. Không dùng lại bộ nhớ đệm preview cũ nếu file đó chưa có đúng phiên bản bộ làm sạch.

Patch mẫu trong bài nằm ở:

```text
solution/defense.patch
```

Patch này sửa đúng các vị trí trên.
