# Attack Round 2 - Khai thác preview cache sau khi vá lần 1

## 1. Bối cảnh sau Defense Round 1

Đội phòng thủ đã sửa `_preview_bitstream` để bỏ AUD NAL type 35 khi render preview mới:

```python
if nal_type(nal) == 35:
    continue
```

Nhìn qua thì exploit Round 1 bị chặn, vì preview mới không còn AUD để lấy bit. Nhưng trong hệ thống thật, file preview thường được cache trên disk để không phải render lại liên tục.

Trong service này, preview nằm trong:

```text
PREVIEW_DIR / f"{item_id}_redacted_preview.h265"
```

## 2. Ý tưởng tấn công

Backend serve preview theo logic:

```python
preview_path = PREVIEW_DIR / f"{item_id}_redacted_preview.h265"
if not preview_path.exists():
    preview_path = _render_preview(item_id)
```

Nếu trước khi vá đã có người tải preview một lần, file preview cũ đã được sinh ra và nằm trong cache. Sau khi deploy Defense 1, backend thấy file đã tồn tại nên trả luôn file cũ, không render lại bằng code mới.

Nói ngắn gọn:

```text
Vá code render mới
nhưng file preview cũ vẫn còn trên disk
=> attacker vẫn tải được artifact cũ chứa AUD leak
```

## 3. Tấn công lại bằng URL cũ

Attacker dùng lại `case id` đã lấy được ở Round 1:

```bash
curl -L -o stale_preview.h265 http://127.0.0.1:8000/api/cases/flag_1780132060_da66f92c/redacted-preview.h265
```

Kiểm tra preview cũ còn AUD hay không:

```bash
python -c "from pathlib import Path; from solution.exploit import find_nals,nal_type; data=Path('stale_preview.h265').read_bytes(); print(sum(1 for n in find_nals(data) if nal_type(n)==35))"
```

Nếu output lớn hơn `0`, cache vẫn còn leak.

Chạy lại exploit:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c
```

Nếu cache cũ chưa bị xóa hoặc chưa bị invalidate, exploit vẫn có thể trả flag:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

## 4. Vì sao đây là hướng hay trong attack-defense

Đây không phải trick vô lý. Trong thực tế, nhiều hệ thống vá code xử lý file nhưng quên dữ liệu đã sinh ra trước đó:

- Thumbnail cũ.
- Preview cũ.
- Export cũ.
- Cache CDN.
- File public đã upload lên object storage.

Vì vậy sau khi thấy đội phòng thủ vá logic render, attacker nên thử lại artifact cũ trước khi tìm bug hoàn toàn mới.

## 5. Kết luận Round 2

Defense Round 1 đúng hướng nhưng chưa đủ. Nó chỉ bảo vệ preview được render sau khi deploy. Defense tiếp theo phải xử lý stale cache:

- Xóa preview cache cũ.
- Hoặc gắn version cho sanitizer.
- Nếu cache thiếu/sai version thì render lại preview sạch.
