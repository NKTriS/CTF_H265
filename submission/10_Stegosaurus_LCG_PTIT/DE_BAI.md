# Đề bài Jeopardy CTF: Stegosaurus LCG

## Thông tin chung

- Tên bài: Stegosaurus LCG
- Chủ đề: LSB steganography, LCG, XOR keystream
- Hình thức: Jeopardy CTF
- Độ khó đề xuất: Hard
- Flag format: `blockChainPTIT{}`
- Nguồn tham khảo: BSides 2025 CTF - Stegosaurus LSB Steganography Challenge
- Link nguồn: <https://dmoges.com/posts/bsides-ctf-stegosaurus-steganography/>

## Mô tả

Một ảnh PNG bình thường, một tên file quá dài, và một cấu hình có vẻ được để lộ
hơi vụng về. Nếu đọc LSB theo thứ tự tuyến tính không ra gì, hãy để bộ sinh số
giả ngẫu nhiên dẫn đường.

Flag được mã hóa XOR bằng khóa sinh từ `DEFAULT1111`, sau đó được nhúng vào LSB của
các pixel. Vị trí pixel không đi tuần tự từ trái sang phải, mà được chọn bằng LCG
với các tham số ghi ngay trong tên file.

## File phát cho người chơi

Thư mục `public/` gồm:

- `LSBSTEGO_CONFIG_LCG[1664525,1013904223,4294967296]_DEFAULT1111.png`
- `HINT.txt`

Có thể phát file zip:

```text
dist/10_stegosaurus_lcg_public.zip
```

## Docker

Bài này là bài steganography offline, không cần Docker hay service network.

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng để build lại đề,
kiểm tra flag và xem lời giải mẫu.
