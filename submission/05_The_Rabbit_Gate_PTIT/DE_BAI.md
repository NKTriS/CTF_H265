# Đề bài Jeopardy CTF: The Rabbit Gate

## Thông tin chung

- Tên bài: The Rabbit Gate
- Chủ đề: H.265/HEVC steganography
- Hình thức: Jeopardy
- Độ khó đề xuất: Trung bình
- Flag format: `blockChainPTIT{}`

## Mô tả

Một video Big Buck Bunny H.265 nhìn bình thường. Không có chuỗi flag rõ ràng, người chơi cần phân tích bitstream HEVC và quan hệ giữa các NAL control với dữ liệu ảnh.

Nhiệm vụ của người chơi là phân tích các file public, tìm kênh giấu tin trong chuẩn H.265/HEVC và khôi phục flag theo định dạng `blockChainPTIT{...}`.

## File phát cho người chơi

Các file public nằm trong thư mục `public/`:

- `bunny_aud_suspect.hevc`
- `bunny_aud_suspect.mp4`
- `HINT.txt`

Có thể phát cho người chơi file zip:

```text
dist/05_the_rabbit_gate_public.zip
```

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm writeup chi tiết và script solve.
