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

| ID | Tên | Kỹ thuật | Flag | Độ khó CTF |
|---|---|---|---|---|
| 01 | HEVC Metadata Slice | SEI user-data + VCL trailing bytes | `HEVC-LAB{metadata_is_not_pixels}` | Dễ |
| 02 | CCTV Motion Leak | `mv_x` parity | `HEVC{motion_leak_in_cctv}` | Trung bình |
| 03 | Filler NAL Channel | Filler Data NAL length parity | `HEVC{filler_nal_length_channel}` | Khá |
| 04 | CABAC Merge Index | `merge_idx` parity trong trace merge mode | `HEVC{cabac_merge_idx_channel}` | Khó |

## Quy đổi độ khó

| Điểm | Độ khó | Mô tả |
|---:|---|---|
| 100 | Dễ | Người chơi cần biết cấu trúc NAL/SEI cơ bản và thử phân tích metadata. |
| 200 | Trung bình | Cần loại trừ metadata, đọc log, hiểu parity của motion-vector sample. |
| 250 | Khá | Cần so sánh clean/suspect và phát hiện Filler Data NAL là carrier. |
| 400 | Khó | Cần hiểu trace cú pháp H.265, lọc record usable và suy ra kênh `merge_idx`. |

## Gợi ý triển khai

Khi đưa lên hệ thống CTF, chỉ upload nội dung trong `public/` hoặc file zip tương ứng trong `dist/`.
Không upload thư mục `solution/` cho người chơi.
