# Giải trình hoạt động checker

Checker nằm tại `checker/checker.py` và chỉ dùng Python standard library, không
cần cài thêm package ngoài. File này dùng để chấm trạng thái service theo hướng
Hackerdom/attack-defense: checker chỉ kiểm tra SLA và đặt/đọc flag, không chứa
logic khai thác.

## Nguyên tắc tách vai trò

- `checker/checker.py`: dành cho ban tổ chức hoặc hệ thống chấm, chỉ có
  `check`, `put`, `get`.
- `solution/exploit.py`: dành cho writeup/đội tấn công, chứa logic parse H.265
  AUD NAL và khôi phục flag từ public preview.

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

### `check`

Khi chạy trên hệ thống Hackerdom/ForcAD:

```bash
python checker.py check 10.10.0.5
```

Khi test local, có thể truyền thêm port:

```bash
python checker.py check 127.0.0.1 8000
```

Checker gọi `/health`, tạo một marker tạm, gọi `/api/store`, rồi gọi `/api/read`
với đúng token. Nếu marker đọc ra trùng với marker đã đặt thì service được xem
là còn hoạt động.

Checker không bắt buộc kiểm tra dashboard `/`, nhưng dashboard vẫn có trong
service để người chơi tương tác bằng trình duyệt.

### `put`

Khi chạy trên hệ thống Hackerdom/ForcAD:

```bash
python checker.py put 10.10.0.5 flag_seed_123 'blockChainPTIT{example_flag}' 1
```

Khi test local, có thể truyền port trước flag:

```bash
python checker.py put 127.0.0.1 8000 'blockChainPTIT{example_flag}'
```

Checker gửi flag/custody marker vào `/api/store`, sau đó in ra `flag_id` dạng
JSON:

```json
{"id": "flag_...", "token": "..."}
```

Nếu hệ thống chấm lưu stdout của `put`, JSON này sẽ được truyền lại cho mode
`get`. Nếu hệ thống chấm chỉ truyền lại `flag_id` gốc kiểu Hackerdom, checker
vẫn đọc được vì token được sinh quyết định từ `flag_id` đó.

Trong bối cảnh attack-defense, attacker chỉ cần biết `id` hoặc tự lấy `id` qua
endpoint public `/api/cases`.

### `get`

Khi chạy trên hệ thống Hackerdom/ForcAD:

```bash
python checker.py get 10.10.0.5 flag_seed_123 'blockChainPTIT{example_flag}' 1
```

Khi test local với JSON do mode `put` in ra:

```bash
python checker.py get 127.0.0.1 8000 '{"id":"flag_x","token":"token_x"}' 'blockChainPTIT{example_flag}'
```

Checker gửi `id` và `token` vào `/api/read`, so sánh marker trả về với flag gốc.
Nếu khác nhau thì trả `CORRUPT`.

## Vì sao checker không có `exploit`

Bản cũ từng có mode `exploit` trong checker để tiện test lab. Cách đó không
chuẩn khi đưa lên hệ thống attack-defense vì checker bị lẫn vai trò:

- Checker là công cụ của ban tổ chức để kiểm tra service.
- Exploit là tài liệu/solution cho người giải.
- Nếu checker chứa exploit, người đọc checker có thể thấy luôn cách lấy flag.

Vì vậy mode khai thác đã được tách sang:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_x
```
