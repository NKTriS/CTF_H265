# Đề bài Jeopardy CTF: Empty Crate

## Thông tin chung

- Tên bài: Empty Crate
- Chủ đề: H.265/HEVC steganography
- Hình thức: Jeopardy
- Độ khó đề xuất: Dễ
- Flag format: `blockChainPTIT{}`

## Mô tả

Có hai file HEVC gồm bản clean và bản suspect. File suspect vẫn phát bình thường nhưng có phần dữ liệu đệm được dùng làm kênh giấu tin.

Nhiệm vụ của người chơi là phân tích các file public, tìm kênh giấu tin trong chuẩn H.265/HEVC và khôi phục flag theo định dạng `blockChainPTIT{...}`.

## File phát cho người chơi

Các file public nằm trong thư mục `public/`:

- `warehouse-clean.hevc`
- `warehouse-suspect.hevc`
- `export_audit.log`
- `HINT.txt`

Có thể phát cho người chơi file zip:

```text
dist/03_empty_crate_public.zip
```

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm writeup chi tiết và script solve.
