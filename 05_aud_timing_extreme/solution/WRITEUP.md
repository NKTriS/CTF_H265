# AUD Timing - Writeup

## Nguồn video

Video được tạo từ Big Buck Bunny Sunflower 1080p MP4 mirror:

```text
https://mirror.umd.edu/xbmc/demo-files/BBB/bbb_sunflower_1080p_30fps_normal.mp4
```

Nguồn metadata của file gốc ghi Creative Commons Attribution 3.0.

## Ý tưởng

Challenge dùng video Big Buck Bunny đã mã hóa H.265. Kênh giấu tin không nằm trong pixel, SEI, filler, motion vector hay CABAC trace. Payload nằm trong chuỗi `Access Unit Delimiter` NAL, cụ thể là bit chẵn/lẻ của trường `primary_pic_type`.

Trong HEVC, AUD là NAL type `35`. NAL này có thể xuất hiện trước access unit để báo loại ảnh chính. Vì nó không phải dữ liệu ảnh, video vẫn xem bình thường.

Để tránh việc đọc tuần tự là ra flag ngay, challenge trộn thêm nhiễu vào các AUD còn lại. Stream thật được ghi theo một bước nhảy cố định trên danh sách AUD:

```text
start = 19
step  = 73
```

Stream thật cũng không chứa flag ASCII trực tiếp. Cấu trúc gói là:

```text
magic       = "AU"
length      = 2 byte big-endian
ciphertext  = zlib(flag) XOR PRNG(seed)
crc32       = crc32(flag)
```

Seed PRNG được lấy từ SHA-256 của kích thước 64 VCL NAL đầu tiên. Vì vậy người giải phải vừa tìm đúng kênh, đúng lịch lấy mẫu, vừa dựng lại khóa từ chính bitstream.

## Cách giải

1. Parse Annex-B start code `00 00 01` hoặc `00 00 00 01`.
2. Lọc các NAL có `nal_unit_type = 35`.
3. Với mỗi AUD, đọc byte RBSP đầu tiên sau header NAL 2 byte.
4. Tính:

```text
primary_pic_type = rbsp_byte >> 5
bit = primary_pic_type & 1
```

5. Nếu đọc tuần tự không ra ASCII, brute force các cặp `(start, step)` sao cho `gcd(step, AUD_COUNT) = 1`.
6. Với mỗi cặp, đi qua danh sách AUD theo công thức `pos = (start + k * step) % AUD_COUNT`.
7. Khi thấy magic `AU`, đọc độ dài ciphertext.
8. Dựng seed từ SHA-256 của kích thước 64 VCL NAL đầu tiên.
9. XOR ciphertext với PRNG stream, giải nén zlib.
10. Kiểm tra CRC32 rồi lấy flag.

## Lệnh mẫu

```bash
python3 solve.py ../public/bunny_aud_suspect.hevc
```

Kết quả:

```text
AUD_NAL_COUNT=542
WALK_START=19
WALK_STEP=73
HEVC{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```

## Flag

```text
HEVC{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```
