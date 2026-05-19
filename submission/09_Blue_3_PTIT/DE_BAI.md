# Đề bài Jeopardy CTF: Blue 3?

## Thông tin chung

- Tên bài: Blue 3?
- Chủ đề: Image steganography, pixel delta, diagonal blocks
- Hình thức: Jeopardy CTF
- Độ khó đề xuất: Hard
- Flag format: `blockChainPTIT{}`
- Nguồn tham khảo: BYU old CTF challenges - `forensics-steganography/blue-3`
- Link nguồn: <https://github.com/BYU-CSA/old-ctf-challenges/tree/master/forensics-steganography/blue-3>

## Mô tả

Lại là màu xanh. Nhưng nếu một bức ảnh gần như toàn một màu được chọn làm đề bài,
có lẽ điều đáng nhìn không nằm ở hình dạng mà nằm ở những khác biệt rất nhỏ.

Người chơi nhận được một ảnh PNG màu xanh. Flag được giấu bằng cách chia ảnh thành
nhiều vùng nhỏ trên đường chéo. Với mỗi ký tự, một số pixel trong vùng tương ứng
được tăng nhẹ ở một kênh màu; tổng độ lệch của vùng chính là mã ASCII của ký tự đó.

## File phát cho người chơi

Thư mục `public/` gồm:

- `blue.png`
- `HINT.txt`

Có thể phát file zip:

```text
dist/09_blue_3_public.zip
```

## Docker

Bài này là bài steganography offline, không cần Docker hay service network.

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng để build lại đề,
kiểm tra flag và xem lời giải mẫu.
