# Đề bài Jeopardy CTF: Dinosaur

## Thông tin chung

- Tên bài: Dinosaur
- Chủ đề: Steganography, photomosaic, QR
- Hình thức: Jeopardy CTF
- Độ khó đề xuất: Easy
- Flag format: `blockChainPTIT{}`
- Nguồn tham khảo: ImaginaryCTF 2025 - `Forensics/dinosaur`

## Mô tả

Mọi người đều có một loài khủng long yêu thích. Bạn đoán được của tôi là gì không?

Người chơi nhận được một file văn bản chứa rất nhiều tên emoji/tile. Nhiệm vụ là nhận ra đây không phải văn bản để đọc trực tiếp, mà là bản đồ để dựng lại một ảnh mosaic. Ảnh sau khi dựng lại chứa QR code dẫn tới flag.

## File phát cho người chơi

Thư mục `public/` gồm:

- `STEGosaurus.txt`
- `HINT.txt`

Có thể phát file zip:

```text
dist/07_dinosaur_public.zip
```

## Docker

Bài này là bài steganography offline, không cần Docker hay service network.

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm bộ tile tham chiếu, script build, script solve, writeup và ảnh minh chứng.
