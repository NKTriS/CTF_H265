# Giải trình hoạt động checker

Checker nằm tại `checker/checker.py` và chỉ dùng Python standard library, không
cần cài thêm package ngoài. File này dùng để chấm trạng thái service theo hướng
Hackerdom/attack-defense: checker chỉ kiểm tra SLA và đặt/đọc flag, không chứa
logic khai thác.

Checker đã được viết để hợp với kiểu ADArena demo đang dùng: hệ thống có
`max_round = 20`, `round_time = 300`, `flag_lifetime = 5`, flag prefix
`blockChainPTIT`, và checker tương thích Hackerdom/ForcAD.

Thông số tích hợp nằm ở:

```text
checker/adarena_task.yml
checker/ADARENA.md
```

## Nguyên tắc tách vai trò

- `checker/checker.py`: dành cho ban tổ chức hoặc hệ thống chấm, chỉ có
  `check`, `put`, `get`.
- `solution/exploit.py`: dành cho writeup/đội tấn công, chứa logic parse H.265
  và khôi phục flag từ các bề mặt public bị lỗi.

Việc tách này quan trọng vì checker không nên tiết lộ cách khai thác cho đội
phòng thủ hoặc bị bundle nhầm vào môi trường chấm.

## Mã trạng thái

Checker trả exit code theo kiểu Hackerdom:

| Exit code | Ý nghĩa |
| --- | --- |
| `101` | `OK` - service hoạt động đúng |
| `102` | `CORRUPT` - flag đã đặt nhưng đọc lại sai |
| `103` | `MUMBLE` - service trả dữ liệu sai định dạng hoặc sai logic |
| `104` | `DOWN` - service không truy cập được hoặc lỗi hệ thống |
| `110` | `CHECK FAILED` - bản thân checker gặp lỗi ngoài dự kiến |

## Các mode

Checker hỗ trợ cả hai kiểu truyền tham số để dễ chạy trên nhiều checksystem:

```bash
python checker.py check 10.10.0.5
python checker.py 10.10.0.5 check
```

Với local port:

```bash
python checker.py check 127.0.0.1 8000
python checker.py 127.0.0.1 8000 check
```

Nếu checksystem không truyền port, checker dùng `SERVICE_PORT`, mặc định là
`8000`.

### `check`

Khi chạy trên hệ thống Hackerdom/ForcAD:

```bash
python checker.py check 10.10.0.5
# hoặc:
python checker.py 10.10.0.5 check
```

Khi test local, có thể truyền thêm port:

```bash
python checker.py check 127.0.0.1 8000
```

Checker gọi `/health`, tạo một marker tạm, gọi `/api/store`, rồi gọi `/api/read`
với đúng token. Nếu marker đọc ra trùng với marker đã đặt thì luồng lưu/đọc hợp lệ
vẫn hoạt động.

Sau đó checker kiểm tra thêm các chức năng public mà service phải giữ:

- `/api/cases` phải trả danh sách case hợp lệ và có case vừa tạo.
- `preview_url` của case vừa tạo phải tải được.
- Preview tải về phải giống một HEVC Annex-B stream hợp lệ, tức có NAL chứa frame
  và NAL parameter set như VPS/SPS/PPS.
- `/api/read` và `/api/carrier` phải từ chối token sai bằng HTTP `403`.
- `share_url`, `manifest_url`, `thumbnail_url` phải đúng định dạng.
- Manifest public phải mô tả đúng case vừa tạo.
- Thumbnail public phải trả một JPEG envelope hợp lệ.
- `/api/preview-jobs` phải trả danh sách job đúng định dạng.

Checker không giải mã AUD/SEI và không tìm flag trong preview. Việc khai thác nằm
ở `solution/exploit.py`, không nằm trong checker.

### `put`

Khi chạy trên hệ thống Hackerdom/ForcAD:

```bash
python checker.py put 10.10.0.5 flag_seed_123 'blockChainPTIT{example_flag}' 1
# hoặc:
python checker.py 10.10.0.5 put flag_seed_123 'blockChainPTIT{example_flag}' 1
```

Khi test local, có thể truyền port trước flag:

```bash
python checker.py put 127.0.0.1 8000 'blockChainPTIT{example_flag}'
```

Checker gửi flag/custody marker vào `/api/store`, sau đó in ra `flag_id` một
dòng dạng plain text:

```text
flag_seed_123
```

Checker không in token ra stdout/stderr.

Token dùng để gọi `/api/read` được checker sinh từ cả `id` và flag thật:

```text
sha256("h265-ad-checker-token-v2:" || id || ":" || flag)[:32]
```

Mode `get` luôn được hệ thống chấm truyền lại flag thật để so sánh, nên checker
có thể tự tính lại token. Attacker chỉ biết `id` public nên không tự tính được
token hợp lệ.

Trong bối cảnh attack-defense, attacker chỉ cần biết `id` hoặc tự lấy `id` qua
endpoint public `/api/cases`.

Tham số cuối `VULN`/`place` được dùng để chọn camera source:

| Place | Source |
| --- | --- |
| `1` | `lobby_cam_01` |
| `2` | `parking_gate_02` |
| `3` | `evidence_upload` |

Nếu hệ thống không truyền place, checker tự chọn ngẫu nhiên một source hợp lệ.

### `get`

Khi chạy trên hệ thống Hackerdom/ForcAD:

```bash
python checker.py get 10.10.0.5 flag_seed_123 'blockChainPTIT{example_flag}' 1
# hoặc:
python checker.py 10.10.0.5 get flag_seed_123 'blockChainPTIT{example_flag}' 1
```

Khi test local với `flag_id` do mode `put` in ra:

```bash
python checker.py get 127.0.0.1 8000 flag_x 'blockChainPTIT{example_flag}'
```

Checker tự tính token từ `id` và flag, gửi `id` + `token` vào `/api/read`, rồi
so sánh marker trả về với flag gốc. Nếu khác nhau thì trả `CORRUPT`.
