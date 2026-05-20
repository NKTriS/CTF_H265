# H265 Evidence Portal AD - Writeup

Writeup đã được tách thành hai file riêng:

- `solution/ATTACK.md`: cách khai thác redacted preview `.h265`, parse AUD NAL và lấy flag.
- `solution/DEFENSE.md`: cách vá preview, ảnh chụp màn hình cần có, và cách chứng minh checker vẫn OK.

## Tóm tắt lỗi

Service mô phỏng cổng chia sẻ bằng chứng CCTV đã redact. Dashboard `/` cho phép
import CCTV evidence từ camera/source, lưu raw H.265 evidence carrier và kiểm
tra custody marker bằng operator token. Marker là dữ liệu nội bộ do hệ thống gắn
vào evidence; trong CTF, checker đặt flag vào marker qua API. Route `/api/read`
và `/api/carrier` đều yêu cầu token.

Lỗi nằm ở tính năng public redacted preview:

```text
GET /api/cases/<id>/redacted-preview.h265
```

Backend strip các VCL slice nên nghĩ preview không còn dữ liệu hình ảnh nhạy
cảm. Nhưng preview vẫn giữ AUD NAL type 35. Trong bài này, flag/custody marker
nằm trong `primary_pic_type & 1` của các AUD NAL, nên attacker vẫn khôi phục được
packet:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

Defense chính là sửa preview để strip AUD NAL hoặc tạo lại AUD trung tính, đồng
thời giữ nguyên dashboard, `/api/store`, `/api/read` và checker.
