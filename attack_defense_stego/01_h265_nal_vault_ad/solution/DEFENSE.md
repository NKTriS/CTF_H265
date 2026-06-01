# H265 Evidence Portal AD - Defense Writeup

## Lỗ Hổng Tổng Quát

Lỗi của bài là **public preview được tạo từ private H.265 carrier bằng sanitizer không đủ chặt**.

Raw carrier là dữ liệu nội bộ. Nó có thể chứa:

- VCL frame.
- VPS/SPS/PPS.
- AUD timing metadata.
- SEI metadata.
- debug trace.
- custody marker side-channel.
- artifact cũ đã render.

Preview public chỉ nên chứa dữ liệu cần thiết để người ngoài xem video đã redact. Nhưng
service lại copy nhiều NAL từ carrier sang preview, làm lộ side-channel chứa flag.

Vì vậy defense không nên nghĩ theo kiểu:

```text
Leak ở AUD thì strip AUD là xong.
```

Cách nghĩ đúng là:

```text
Public artifact phải được tạo theo allowlist dữ liệu an toàn.
Mọi metadata không cần cho public playback phải bị loại bỏ.
Artifact cũ sinh bởi sanitizer lỗi phải bị invalidate.
```

## Những Chỗ Cần Vá

### 1. Preview sanitizer

Vị trí cần vá nằm ở hàm tạo preview:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        ...
    return bytes(preview)
```

Bản vulnerable copy gần như toàn bộ NAL sang preview. Đây là nguyên nhân gốc.

Không nên vá bằng denylist kiểu:

```python
if nal_type(nal) == 35:
    continue
```

Vì cách này chỉ chặn AUD. Nếu còn SEI/debug trace hoặc metadata khác, attacker vẫn có
đường khai thác.

Nên vá bằng allowlist:

```python
SAFE_PREVIEW_NAL_TYPES = set(range(0, 32)) | {32, 33, 34}
```

Ý nghĩa:

- `0..31`: VCL frame, giữ nội dung video đã redact.
- `32`: VPS.
- `33`: SPS.
- `34`: PPS.

Các loại không nằm trong allowlist bị bỏ:

- `35`: AUD.
- `39/40`: SEI prefix/suffix.
- metadata phụ khác.
- debug/custody side-channel.

Code vá:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        if nal_type(nal) not in SAFE_PREVIEW_NAL_TYPES:
            continue
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)
```

Điểm quan trọng: allowlist an toàn hơn denylist vì defender không cần đoán hết mọi loại
metadata nguy hiểm.

### 2. SEI/debug trace

Trong bài này, carrier có SEI debug trace chứa packet đã mask:

```text
H5DBG || length || masked_packet
```

Nếu chỉ strip AUD, SEI vẫn leak. Vì vậy defense phải loại cả SEI khỏi preview public.

Allowlist ở trên đã xử lý việc này vì type `39/40` không được giữ lại.

### 3. Preview cache

Ngay cả khi code sanitizer đã đúng, preview cũ có thể vẫn nằm trong cache:

```text
PREVIEW_DIR/<case_id>_redacted_preview.h265
```

Nếu backend chỉ check `preview_path.exists()`, nó sẽ trả file cũ sinh bởi sanitizer lỗi.

Cần thêm version cho sanitizer:

```python
PREVIEW_SANITIZER_VERSION = "strip-metadata-v3"
```

Khi render preview, ghi version:

```python
version_path.write_text(PREVIEW_SANITIZER_VERSION, encoding="utf-8")
```

Khi serve preview, chỉ dùng cache nếu version khớp:

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

Route preview cần đổi từ:

```python
if not preview_path.exists():
    preview_path = _render_preview(item_id)
```

sang:

```python
if not _preview_cache_fresh(item_id):
    preview_path = _render_preview(item_id)
```

Như vậy cache cũ thiếu/sai version sẽ tự bị render lại.

### 4. Public recon endpoints

Các endpoint sau có thể vẫn public:

```text
/api/cases
/share/<share_id>
/api/share/<share_id>/manifest.json
/api/audit
/api/preview-jobs
```

Không nhất thiết phải tắt hết chúng, vì đó là chức năng sản phẩm. Nhưng cần đảm bảo chúng
không trả dữ liệu nhạy cảm như:

- token
- raw carrier path
- marker
- debug packet
- internal storage path
- signed/private URL

Chúng có thể trả `case id` và preview URL, miễn là preview đã được sanitize đúng.

### 5. Auth boundary

Các route private vẫn phải yêu cầu token:

```text
POST /api/read
POST /api/carrier
```

Không nên "vá" bằng cách tắt route private hoặc làm checker không đọc được flag. Checker
cần `put/get` hoạt động để bài A/D hợp lệ.

## Patch Mẫu

Patch nộp cuối nằm ở:

```bash
solution/defense.patch
```

Patch này gồm hai ý chính:

- Allowlist NAL an toàn khi tạo preview.
- Sanitizer version để invalidate preview cache cũ.

Áp dụng:

```bash
git apply --check solution/defense.patch
git apply solution/defense.patch
```

## Tiêu Chí Kiểm Tra Sau Vá

Sau khi vá, cần kiểm tra theo các tiêu chí sau.

Service hợp lệ vẫn hoạt động:

```text
checker check -> OK
checker put   -> lưu được flag
checker get   -> đọc lại đúng flag khi có token
```

Preview public vẫn dùng được:

```text
ffprobe preview_after_patch.h265 -> codec_name=hevc
```

Preview không còn NAL nguy hiểm:

```text
AUD type 35 = 0
SEI type 39 = 0
SEI type 40 = 0
```

Exploit public thất bại:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id <case_id> --vector auto
```

Route private vẫn chặn token sai:

```text
POST /api/read với token sai -> 403/forbidden
POST /api/carrier với token sai -> 403/forbidden
```

## Vì Sao Đây Là Defense Đúng

Defense này xử lý root bug thay vì xử lý từng biểu hiện.

Nếu chỉ strip AUD:

```text
SEI vẫn leak.
```

Nếu chỉ strip AUD/SEI:

```text
cache cũ vẫn leak.
```

Nếu chỉ yêu cầu token cho preview:

```text
làm hỏng chức năng public redacted preview.
```

Allowlist NAL + cache version giải quyết đúng bản chất:

```text
Preview public chỉ giữ dữ liệu cần để decode video.
Metadata/custody/debug side-channel không được public.
Artifact cũ sinh bởi sanitizer lỗi không được tái sử dụng.
```

## Gợi Ý Defense Thực Tế Hơn

Trong sản phẩm thật, nên làm thêm:

- Tạo preview bằng transcoder sạch thay vì copy NAL từ private carrier.
- Purge CDN/object storage cache sau khi vá sanitizer.
- Log download preview bất thường.
- Rate limit endpoint preview.
- Rotate marker/flag đã lộ trước khi vá.
- Thêm regression test để đảm bảo preview không còn AUD/SEI/debug magic như `H5AD`, `H5DBG`.
