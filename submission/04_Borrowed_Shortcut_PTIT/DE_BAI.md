# Đề bài Jeopardy CTF: Borrowed Shortcut

## Thông tin chung

- Tên bài: Borrowed Shortcut
- Chủ đề: H.265/HEVC steganography
- Hình thức: Jeopardy
- Độ khó đề xuất: Dễ
- Flag format: `blockChainPTIT{}`

## Mô tả

Người chơi nhận được một video nguồn và trace merge mode đã trích xuất. Flag không nằm trực tiếp trong video mà nằm trong quy luật của trace codec.

Nhiệm vụ của người chơi là phân tích các file public, tìm kênh giấu tin trong chuẩn H.265/HEVC và khôi phục flag theo định dạng `blockChainPTIT{...}`.

## File phát cho người chơi

Các file public nằm trong thư mục `public/`:

- `warehouse-source.mp4`
- `merge_trace.csv`
- `incident_note.txt`
- `HINT.txt`

Có thể phát cho người chơi file zip:

```text
dist/04_borrowed_shortcut_public.zip
```

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm writeup chi tiết và script solve.
