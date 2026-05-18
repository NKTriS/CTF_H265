# AUD Timing Extreme - Writeup

## Ý tưởng

Challenge dùng video Big Buck Bunny đã mã hóa H.265. Kênh giấu tin không nằm trong pixel, SEI, filler, motion vector hay CABAC trace. Payload nằm trong chuỗi `Access Unit Delimiter` NAL, cụ thể là bit chẵn/lẻ của trường `primary_pic_type`.

Trong HEVC, AUD là NAL type `35`. NAL này có thể xuất hiện trước access unit để báo loại ảnh chính. Vì nó không phải dữ liệu ảnh, video vẫn xem bình thường.

## Cách giải

1. Parse Annex-B start code `00 00 01` hoặc `00 00 00 01`.
2. Lọc các NAL có `nal_unit_type = 35`.
3. Với mỗi AUD, đọc byte RBSP đầu tiên sau header NAL 2 byte.
4. Tính:

```text
primary_pic_type = rbsp_byte >> 5
bit = primary_pic_type & 1
```

5. Ghép bit theo thứ tự xuất hiện, chia mỗi 8 bit thành 1 byte.
6. Tìm chuỗi dạng `HEVC{...}`.

## Lệnh mẫu

```bash
python3 solve.py ../public/bunny_aud_suspect.hevc
```

Kết quả:

```text
AUD_NAL_COUNT=480
HEVC{aud_primary_pic_type_order_is_the_channel}
```

## Flag

```text
HEVC{aud_primary_pic_type_order_is_the_channel}
```
