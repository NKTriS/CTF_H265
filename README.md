# CTF_H265

Thư mục này chuyển các lab H.265 steganography thành dạng Jeopardy CTF.

Cấu trúc mỗi challenge:

```text
<challenge>/
  challenge.yml      Metadata để đưa lên nền tảng CTF
  public/            File phát cho người chơi
  solution/          Writeup và script solve cho giảng viên
```

Các file `.zip` trong `dist/` là gói public có thể upload lên platform.

## Danh sách challenge

| ID | Tên | Kỹ thuật | Flag | Độ khó CTF |
|---|---|---|---|---|
| 01 | HEVC Metadata Slice | SEI user-data + VCL trailing bytes | `HEVC-LAB{metadata_is_not_pixels}` | Dễ |
| 02 | CCTV Motion Leak | `mv_x` parity | `HEVC{motion_leak_in_cctv}` | Dễ |
| 03 | Filler NAL Channel | Filler Data NAL length parity | `HEVC{filler_nal_length_channel}` | Dễ |
| 04 | CABAC Merge Index | `merge_idx` parity trong trace merge mode | `HEVC{cabac_merge_idx_channel}` | Trung bình |
| 05 | AUD Timing Extreme | Access Unit Delimiter `primary_pic_type` parity | `HEVC{aud_primary_pic_type_order_is_the_channel}` | Cực khó |

## Gợi ý triển khai

Khi đưa lên hệ thống CTF, chỉ upload nội dung trong `public/` hoặc file zip tương ứng trong `dist/`.
Không upload thư mục `solution/` cho người chơi.
