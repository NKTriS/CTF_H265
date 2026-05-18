# Giải trình hoạt động checker

Checker nằm tại `checker/checker.py` và dùng Python standard library, không cần
cài thêm package ngoài.

## Các mode

### `check`

```bash
python checker.py check 127.0.0.1 8000
```

Checker gọi `/health`, sau đó tạo một secret tạm, gọi `/api/store`, rồi gọi
`/api/read` với đúng token. Nếu secret đọc ra trùng với secret đã đặt thì service
được xem là còn hoạt động.

### `put`

```bash
python checker.py put 127.0.0.1 8000 'blockChainPTIT{example_flag}'
```

Checker tạo `id` và `token` ngẫu nhiên, gửi flag vào `/api/store`, sau đó in ra
`flag_id` dạng JSON:

```json
{"id": "flag_...", "token": "..."}
```

Hệ thống chấm có thể lưu JSON này để gọi lại mode `get`.

### `get`

```bash
python checker.py get 127.0.0.1 8000 '{"id":"flag_x","token":"token_x"}' 'blockChainPTIT{example_flag}'
```

Checker gửi `id` và `token` vào `/api/read`, so sánh secret trả về với flag gốc.
Nếu khác nhau thì báo `CORRUPT`.

### `exploit`

```bash
python checker.py exploit 127.0.0.1 8000
```

Mode này mô phỏng attacker:

1. Gọi `/api/debug/list` để lấy danh sách file `.h265`.
2. Tải từng carrier bằng `/api/debug/file/<filename>`.
3. Tách các NAL unit trong raw HEVC Annex-B.
4. Lấy các AUD NAL type 35.
5. Đọc bit thấp nhất của `primary_pic_type` trong mỗi AUD.
6. Kiểm tra packet `H5AD || length || secret || crc32`.
7. In các secret bắt đầu bằng `blockChainPTIT{`.

Mode `exploit` chỉ dùng cho writeup/kiểm thử điểm yếu, không nên dùng để chấm SLA
trong giải thật.
