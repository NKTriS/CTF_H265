# H265 NAL Vault AD - Writeup

Writeup đã được tách thành hai file riêng:

- `solution/ATTACK.md`: cách khai thác public preview `.h265`, parse AUD NAL và lấy flag.
- `solution/DEFENSE.md`: cách vá preview, ảnh chụp màn hình cần có, và cách chứng minh checker vẫn OK.

## Tóm tắt lỗi

Service có dashboard web tại `/` để store/read secret. Bên dưới, service lưu
flag vào raw HEVC Annex-B bitstream. API đọc hợp lệ `/api/read` có kiểm tra
`token`, và route `/api/carrier` cũng yêu cầu token khi tải raw carrier.

Lỗi nằm ở tính năng public preview:

```text
GET /api/share/<id>/preview.h265
```

Backend strip các VCL slice nên nghĩ preview không còn dữ liệu nhạy cảm. Nhưng
preview vẫn giữ AUD NAL type 35. Trong bài này, flag lại nằm trong
`primary_pic_type & 1` của các AUD NAL, nên attacker vẫn khôi phục được packet:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

Defense chính là sửa preview để strip AUD NAL hoặc tạo lại AUD trung tính, đồng
thời giữ nguyên dashboard, `/api/store`, `/api/read` và checker.
