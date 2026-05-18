# CTF_H265

Thư mục này chuyển 4 lab H.265 steganography thành dạng Jeopardy CTF.

Cấu trúc mỗi challenge:

```text
<challenge>/
  challenge.yml      Metadata để đưa lên nền tảng CTF
  public/            File phát cho người chơi
  solution/          Writeup và script solve cho giảng viên
```

Các file `.zip` trong `dist/` là gói public có thể upload lên platform.

## Danh sách challenge

| ID | Tên | Kỹ thuật | Flag | Điểm gợi ý |
|---|---|---|---|---|
| 01 | HEVC Metadata Slice | SEI user-data + VCL trailing bytes | `HEVC-LAB{metadata_is_not_pixels}` | 100 |
| 02 | CCTV Motion Leak | `mv_x` parity | `HEVC{motion_leak_in_cctv}` | 200 |
| 03 | Filler NAL Channel | Filler Data NAL length parity | `HEVC{filler_nal_length_channel}` | 250 |
| 04 | CABAC Merge Index | `merge_idx` parity trong trace merge mode | `HEVC{cabac_merge_idx_channel}` | 400 |

## Gợi ý triển khai

Khi đưa lên hệ thống CTF, chỉ upload nội dung trong `public/` hoặc file zip tương ứng trong `dist/`.
Không upload thư mục `solution/` cho người chơi.
