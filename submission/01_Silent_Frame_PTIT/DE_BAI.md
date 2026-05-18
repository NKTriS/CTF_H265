# Đề bài Jeopardy CTF: Silent Frame

## Thông tin chung

- Tên bài: Silent Frame
- Chủ đề: H.265/HEVC steganography
- Hình thức: Jeopardy
- Độ khó đề xuất: Dễ
- Flag format: `blockChainPTIT{}`

## Mô tả

SOC nhận được một file HEVC nghi vấn và một bản clean để đối chiếu. Video xem bình thường nhưng có dữ liệu ẩn nằm ngoài phần ảnh hiển thị.

Nhiệm vụ của người chơi là phân tích các file public, tìm kênh giấu tin trong chuẩn H.265/HEVC và khôi phục flag theo định dạng `blockChainPTIT{...}`.

## File phát cho người chơi

Các file public nằm trong thư mục `public/`:

- `suspicious.hevc`
- `clean.hevc`
- `HINT.txt`

Có thể phát cho người chơi file zip:

```text
dist/01_silent_frame_public.zip
```

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm writeup chi tiết và script solve.
