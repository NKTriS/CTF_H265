# Giải trình hoạt động checker

Checker nằm tại `checker/checker.py` và dùng Python standard library, không cần
cài thêm package ngoài.

## Các mode

### `check`

```bash
python checker.py check 127.0.0.1 8000
```

Checker gọi `/health`, tạo một marker tạm, gọi `/api/store`, rồi gọi `/api/read`
với đúng token. Nếu marker đọc ra trùng với marker đã đặt thì service được xem
là còn hoạt động.

Checker không bắt buộc phải kiểm tra dashboard `/`, nhưng dashboard vẫn có trong
service để người chơi tương tác bằng trình duyệt.

### `put`

```bash
python checker.py put 127.0.0.1 8000 'blockChainPTIT{example_flag}'
```

Checker tạo `id` và `token` ngẫu nhiên, gửi flag/custody marker vào `/api/store`,
sau đó in ra `flag_id` dạng JSON:

```json
{"id": "flag_...", "token": "..."}
```

Hệ thống chấm có thể lưu JSON này để gọi lại mode `get`. Trong bối cảnh
attack/defense, attacker chỉ cần biết `id` hoặc lấy `id` qua `/api/cases`.

### `get`

```bash
python checker.py get 127.0.0.1 8000 '{"id":"flag_x","token":"token_x"}' 'blockChainPTIT{example_flag}'
```

Checker gửi `id` và `token` vào `/api/read`, so sánh marker trả về với flag gốc.
Nếu khác nhau thì báo `CORRUPT`.

### `exploit`

```bash
python checker.py exploit 127.0.0.1 8000
```

Mode này mô phỏng attacker:

1. Gọi `/api/cases` để lấy danh sách public case id.
2. Tải từng redacted preview bằng `/api/cases/<id>/redacted-preview.h265`.
3. Tách các NAL unit trong raw HEVC Annex-B.
4. Lấy các AUD NAL type 35 còn sót trong preview.
5. Sinh lại cadence từ `case id` để bỏ các AUD giả.
6. Ghép bit data từ `primary_pic_type & 1`.
7. Giải Manchester và XOR mask theo `case id`.
8. Kiểm tra packet `H5AD || length || marker || crc32`.
9. In các marker bắt đầu bằng `blockChainPTIT{`.

Nếu đã biết target id, có thể truyền:

```bash
python checker.py exploit 127.0.0.1 8000 --flag-id flag_x
```

Mode `exploit` chỉ dùng cho writeup/kiểm thử điểm yếu, không nên dùng để chấm SLA
trong giải thật.
