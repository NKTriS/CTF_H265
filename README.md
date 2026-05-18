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
| 01 | Silent Frame | SEI user-data + VCL trailing bytes | `blockChainPTIT{metadata_nopixel}` | Dễ |
| 02 | Night Shift Camera | `mv_x` parity | `blockChainPTIT{mvx_leaks}` | Dễ |
| 03 | Empty Crate | Filler Data NAL length parity | `blockChainPTIT{filler_voids_01}` | Dễ |
| 04 | Borrowed Shortcut | `merge_idx` parity trong trace merge mode | `blockChainPTIT{merge_path_01}` | Dễ |
| 05 | The Rabbit Gate | HEVC access-unit control channel | `blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}` | Trung bình |

## Gợi ý triển khai

Khi đưa lên hệ thống CTF, chỉ upload nội dung trong `public/` hoặc file zip tương ứng trong `dist/`.
Không upload thư mục `solution/` cho người chơi.
