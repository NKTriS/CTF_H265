# Đề bài Jeopardy CTF: Insanity Check Reimagined

## Thông tin chung

- Tên bài: Insanity Check Reimagined
- Chủ đề: SVG steganography, animation timing, Morse
- Hình thức: Jeopardy CTF
- Độ khó đề xuất: Easy
- Flag format: `blockChainPTIT{}`
- Nguồn tham khảo: UTCTF 2024 - `forensics-insanity-check-reimagined`

## Mô tả

Một phiên bản làm lại của bài Insanity Check nổi tiếng. Flag nằm trong CTFd lần này, nhưng như mọi khi, bạn vẫn phải tự làm việc để lấy nó.

Bài không yêu cầu brute-force. Các công cụ quét thư mục như `dirbuster` sẽ không giúp ích. Người chơi cần quan sát kỹ file SVG và phân tích cách animation của nó thay đổi theo thời gian.

## File phát cho người chơi

Thư mục `public/` gồm:

- `demo_page.html`
- `favicon.svg`
- `HINT.txt`

Có thể phát file zip:

```text
dist/08_insanity_check_public.zip
```

## Docker

Bài này là bài steganography offline, không cần Docker hay service network.

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm script build, script solve, writeup và ảnh minh chứng.
