# Giai trinh hoat dong checker

Checker nam tai `checker/checker.py` va dung Python standard library, khong can
cai them package ngoai.

## Cac mode

### `check`

```bash
python checker.py check 127.0.0.1 8000
```

Checker goi `/health`, sau do tao mot secret tam, goi `/api/store`, roi goi
`/api/read` voi dung token. Neu secret doc ra trung voi secret da dat thi service
duoc xem la con hoat dong.

### `put`

```bash
python checker.py put 127.0.0.1 8000 'blockChainPTIT{example_flag}'
```

Checker tao `id` va `token` ngau nhien, gui flag vao `/api/store`, sau do in ra
`flag_id` dang JSON:

```json
{"id": "flag_...", "token": "..."}
```

He thong cham co the luu JSON nay de goi lai mode `get`.

### `get`

```bash
python checker.py get 127.0.0.1 8000 '{"id":"flag_x","token":"token_x"}' 'blockChainPTIT{example_flag}'
```

Checker gui `id` va `token` vao `/api/read`, so sanh secret tra ve voi flag goc.
Neu khac nhau thi bao `CORRUPT`.

### `exploit`

```bash
python checker.py exploit 127.0.0.1 8000
```

Mode nay mo phong attacker:

1. Goi `/api/debug/list` de lay danh sach file `.h265`.
2. Tai tung carrier bang `/api/debug/file/<filename>`.
3. Tach cac NAL unit trong raw HEVC Annex-B.
4. Lay cac AUD NAL type 35.
5. Doc bit thap nhat cua `primary_pic_type` trong moi AUD.
6. Kiem tra packet `H5AD || length || secret || crc32`.
7. In cac secret bat dau bang `blockChainPTIT{`.

Mode `exploit` chi dung cho writeup/kiem thu diem yeu, khong nen dung de cham SLA
trong giai that.
