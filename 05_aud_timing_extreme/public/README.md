# AUD Timing Extreme

File chính: `bunny_aud_suspect.hevc`

File `bunny_aud_suspect.mp4` chỉ để xem nhanh video bằng trình phát phổ biến. Nếu muốn phân tích bitstream, hãy ưu tiên file `.hevc`.

Gợi ý ban đầu:

- Đây là video H.265 hợp lệ.
- Không cần brute force mật mã.
- Không có flag rõ ràng trong `strings`.
- Vấn đề nằm ở cấu trúc NAL theo từng access unit.

