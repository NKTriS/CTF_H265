# Đề bài Jeopardy CTF: Pixel Delta

## Thông tin chung

- Tên bài: Pixel Delta
- Chủ đề: PNG steganography
- Hình thức: Jeopardy CTF
- Độ khó đề xuất: Medium
- Flag format: `blockChainPTIT{}`
- Nguồn tham khảo: ImaginaryCTF 2023 - `Forensics/steganographic`

## Mô tả

Nếu tôi muốn gửi một thông điệp giấu tin qua Internet, chắc chắn tôi sẽ tự viết thuật toán riêng. Đừng vội cắm ảnh vào hàng loạt công cụ stego ngẫu nhiên rồi mong thấy flag. Không có đâu.

File phát cho người chơi là `chall.png`. Nhiệm vụ của người chơi là phân tích kênh giấu tin trong pixel, tìm cách thông điệp được mã hóa và khôi phục flag theo định dạng `blockChainPTIT{...}`.

## File phát cho người chơi

Thư mục `public/` gồm:

- `chall.png`
- `HINT.txt`

Có thể phát file zip:

```text
dist/06_pixel_delta_public.zip
```

## Docker

Bài này là bài steganography offline, không cần Docker hay service network.

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm ảnh cover `original.png`, script build, script solve, writeup và ảnh minh chứng.
