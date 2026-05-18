# Đề bài Jeopardy CTF: AUD Timing

## Thông tin chung

- Tên bài: AUD Timing
- Chủ đề: H.265/HEVC steganography
- Hình thức: Jeopardy
- Độ khó đề xuất: Khá khó
- Flag format: `blockChainPTIT{}`

## Mô tả

SOC thu được một video H.265 hợp lệ. Video có thể phát bình thường, không có chuỗi flag rõ ràng khi dùng `strings`, không có SEI user-data dễ thấy, không có filler payload, cũng không có trace phân tích đi kèm.

Nhiệm vụ của người chơi là phân tích cấu trúc bitstream H.265 để tìm kênh giấu tin nằm ngoài dữ liệu ảnh hiển thị, sau đó khôi phục flag theo định dạng `blockChainPTIT{...}`.

## File phát cho người chơi

Các file public nằm trong thư mục `public/`:

- `bunny_aud_suspect.hevc`: file H.265 chính để phân tích.
- `bunny_aud_suspect.mp4`: bản MP4 để xem nhanh video.
- `HINT.txt`: gợi ý dạng đánh đố.

Có thể phát cho người chơi file zip:

```text
dist/05_aud_timing_extreme_public.zip
```

## Gợi ý public

```text
Đừng soi từng khung hình; hãy đứng ở cửa ra vào của mỗi nhịp video.
Người gác cửa thì thầm rất khẽ; cái bóng của bức tranh phía sau chỉ rõ lời thì thầm ấy nên lật hay giữ.
Con đường không đi từng viên gạch liền nhau; có vài viên chỉ được đặt để đánh lạc hướng.
Nếu nghe đúng nhịp, lá thư mở đầu bằng hai chữ `AU`, sau đó là độ dài và một dấu kiểm ở cuối.
```

## Kết quả cần tìm

```text
blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm writeup chi tiết và script solve.
