# Defense Round 2 - Invalidate stale preview cache

## 1. Vấn đề sau Defense Round 1

Defense Round 1 strip AUD trong `_preview_bitstream`, nhưng backend chỉ render lại preview khi file chưa tồn tại:

```python
preview_path = PREVIEW_DIR / f"{item_id}_redacted_preview.h265"
if not preview_path.exists():
    preview_path = _render_preview(item_id)
```

Nếu preview cũ đã tồn tại trước khi vá, service vẫn có thể trả lại file cũ chứa AUD leak. Vì vậy attacker ở Round 2 có thể khai thác stale preview cache.

## 2. Mục tiêu Defense Round 2

Round 2 cần đảm bảo:

- Preview cũ sinh bởi sanitizer lỗi không được dùng lại.
- Preview mới vẫn là HEVC hợp lệ.
- Checker `check/put/get` vẫn chạy bình thường.
- Public endpoint vẫn tồn tại, nhưng không còn đủ dữ liệu để reverse marker.

## 3. Bản vá bền hơn: version preview sanitizer

Thêm version cho sanitizer:

```python
PREVIEW_SANITIZER_VERSION = "strip-aud-v2"
```

Khi render preview, ghi kèm file version:

```python
version_path = PREVIEW_DIR / f"{item_id}_redacted_preview.version"
preview_path.write_bytes(_preview_bitstream(bitstream))
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

Route preview đổi từ:

```python
if not preview_path.exists():
    preview_path = _render_preview(item_id)
```

sang:

```python
if not _preview_cache_fresh(item_id):
    preview_path = _render_preview(item_id)
```

Như vậy preview cũ thiếu version hoặc sai version sẽ bị render lại bằng code đã strip AUD.

## 4. Áp dụng patch cuối

Patch mẫu đã bao gồm Defense Round 1 và Round 2:

```bash
git apply solution/defense.patch
```

Kiểm tra trước khi apply:

```bash
git apply --check solution/defense.patch
```

Sau đó rebuild:

```bash
cd service
docker compose down
docker compose up --build -d
```

## 5. Attacker thử lại sau Defense Round 2

Gọi lại các endpoint public:

```bash
curl http://127.0.0.1:8000/api/cases
curl http://127.0.0.1:8000/share/<share_id>
curl http://127.0.0.1:8000/api/share/<share_id>/manifest.json
```

Các endpoint này vẫn có thể lộ `case id`, `share id`, camera/source và preview URL. Đây là dữ liệu public hợp lệ. Điểm cần kiểm tra là preview không còn AUD leak.

Tải preview:

```bash
curl -L -o preview_after_defense2.h265 http://127.0.0.1:8000/api/cases/flag_1710000000_abcd1234/redacted-preview.h265
```

Kiểm tra codec:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview_after_defense2.h265
```

Đếm AUD:

```bash
python -c "from pathlib import Path; from solution.exploit import find_nals,nal_type; data=Path('preview_after_defense2.h265').read_bytes(); print(sum(1 for n in find_nals(data) if nal_type(n)==35))"
```

Kết quả đúng:

```text
0
```

Chạy lại exploit:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --id flag_1710000000_abcd1234
echo $LASTEXITCODE
```

Kết quả đúng là exploit không in flag và exit code khác `0`, thường là `2`.

## 6. Thử bypass `/api/read`

Attacker không có token nên request này phải thất bại:

```bash
curl -X POST http://127.0.0.1:8000/api/read ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"flag_1710000000_abcd1234\",\"token\":\"wrong-token\"}"
```

Kết quả đúng là `403` hoặc JSON báo `forbidden`.

## 7. Kết luận Defense Round 2

Bản defense cuối đạt yêu cầu khi:

- Service vẫn sống: `checker check` trả `OK`.
- Luồng hợp lệ vẫn sống: `checker put/get` đọc lại đúng flag khi có token.
- Preview public vẫn tải được và vẫn là HEVC.
- Preview public không còn AUD NAL type 35.
- Preview cache cũ không còn được dùng lại nếu thiếu/sai sanitizer version.
- Exploit Round 1 và Round 2 đều không lấy được flag.

Trong thực tế, có thể làm thêm:

- Xóa hoặc rotate toàn bộ artifact public đã sinh bởi sanitizer lỗi.
- Purge CDN/object storage cache nếu có.
- Log và rate limit endpoint preview.
- Rotate marker/flag đã lộ trước khi vá.
