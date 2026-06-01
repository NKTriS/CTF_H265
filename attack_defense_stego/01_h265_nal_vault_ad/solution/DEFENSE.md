# H265 Evidence Portal AD - Writeup Defense

## 1. Mục tiêu defense

Defense phải giữ service hoạt động:

- `checker check` vẫn OK.
- `checker put/get` vẫn lưu và đọc đúng flag khi có token.
- Dashboard, `/api/cases`, share link và preview public vẫn tồn tại.
- Attacker không thể lấy marker từ public preview.

Vì bug là lỗi thiết kế preview sanitizer, không nên vá từng dấu hiệu như chỉ strip AUD.
Defense đúng phải xử lý toàn bộ class lỗi:

```text
Public preview không được copy metadata/custody side-channel từ private carrier.
```

## 2. Vì sao vá hời hợt không đủ

### Chỉ strip AUD

Strip AUD type 35 chặn được exploit đầu tiên, nhưng SEI debug trace type 39 vẫn có thể
chứa packet marker đã mask. Attacker chuyển từ:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_x --vector aud
```

sang:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_x --vector sei
```

### Chỉ strip AUD và SEI trong code mới

Nếu preview cũ đã render trước khi vá, backend có thể vẫn trả file cũ trong cache. Lúc
đó attacker dùng mode `auto` và vẫn lấy được flag từ artifact cũ.

### Chỉ yêu cầu token cho preview

Cách này có thể chặn attacker, nhưng làm hỏng kịch bản sản phẩm: redacted preview là
public artifact để chia sẻ. Trong bài này defense đẹp hơn là giữ preview public nhưng
làm nó sạch.

## 3. Bản vá đúng bản chất

Thay vì denylist từng NAL nguy hiểm, dùng allowlist NAL an toàn cho preview:

```python
SAFE_PREVIEW_NAL_TYPES = set(range(0, 32)) | {32, 33, 34}
```

Ý nghĩa:

- Giữ VCL frame `0..31`.
- Giữ VPS/SPS/PPS `32, 33, 34` để bitstream vẫn decode được.
- Loại bỏ AUD `35`.
- Loại bỏ SEI prefix/suffix `39, 40`.
- Loại bỏ metadata phụ khác nếu có.

Hàm preview:

```python
def _preview_bitstream(bitstream: bytes) -> bytes:
    preview = bytearray()
    for nal in find_nals(bitstream):
        if nal_type(nal) not in SAFE_PREVIEW_NAL_TYPES:
            continue
        preview += b"\x00\x00\x00\x01" + nal
    return bytes(preview)
```

## 4. Chống stale preview cache

Thêm version cho sanitizer:

```python
PREVIEW_SANITIZER_VERSION = "strip-metadata-v3"
```

Khi render preview, ghi version cạnh file preview:

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

Route preview đổi thành:

```python
if not _preview_cache_fresh(item_id):
    preview_path = _render_preview(item_id)
```

Như vậy preview cũ thiếu/sai version sẽ bị render lại bằng sanitizer mới.

## 5. Áp dụng patch

Patch mẫu:

```bash
git apply --check solution/defense.patch
git apply solution/defense.patch
```

Rebuild:

```bash
cd service
docker compose down
docker compose up --build -d
```

## 6. Kiểm tra service không hỏng

Health:

```bash
curl http://127.0.0.1:8000/health
```

Checker:

```bash
python checker/checker.py check 127.0.0.1 8000
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
python checker/checker.py get 127.0.0.1 8000 '{"id":"flag_x","token":"token_x"}' 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

`check` và `get` phải trả `OK`.

## 7. Kiểm tra attacker không còn đường public

Tải preview sau vá:

```bash
curl -L -o preview_after_patch.h265 http://127.0.0.1:8000/api/cases/flag_x/redacted-preview.h265
```

Preview vẫn phải là HEVC:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview_after_patch.h265
```

Đếm NAL nguy hiểm:

```bash
python -c "from pathlib import Path; from solution.exploit import find_nals,nal_type; data=Path('preview_after_patch.h265').read_bytes(); print({t:sum(1 for n in find_nals(data) if nal_type(n)==t) for t in (35,39,40)})"
```

Kết quả mong đợi:

```text
{35: 0, 39: 0, 40: 0}
```

Thử exploit:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --id flag_x --vector auto
echo $LASTEXITCODE
```

Kết quả đúng là không in flag và exit code khác `0`.

## 8. Thử bypass `/api/read`

Token sai phải bị từ chối:

```bash
curl -X POST http://127.0.0.1:8000/api/read ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"flag_x\",\"token\":\"wrong-token\"}"
```

Kết quả đúng là `403` hoặc JSON `forbidden`.

## 9. Kết luận defense

Bản vá đạt yêu cầu khi:

- Preview public vẫn dùng được.
- Preview chỉ giữ NAL cần thiết để decode.
- AUD/SEI/debug metadata không còn xuất hiện trong public preview.
- Cache cũ bị invalidate bằng sanitizer version.
- Checker vẫn đặt và đọc flag động bình thường.

Trong sản phẩm thật, nên làm thêm:

- Tạo preview bằng transcoder sạch thay vì copy NAL từ private carrier.
- Purge CDN/object storage cache.
- Log và rate limit endpoint preview.
- Rotate marker/flag đã bị lộ trước khi vá.
