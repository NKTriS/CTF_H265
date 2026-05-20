# Đề bài Attack/Defense CTF: H265 NAL Vault AD

## Thông tin chung

- Tên bài: H265 NAL Vault AD
- Chủ đề: H.265/HEVC Annex-B, AUD NAL steganography, public preview leak
- Hình thức: Attack/Defense
- Độ khó đề xuất: Trung bình - khó
- Flag format: `blockChainPTIT{}`

## Mô tả

H265 NAL Vault là một web service lưu bí mật của đội chơi trong raw HEVC
Annex-B bitstream. Người dùng có dashboard tại `/` để store/read secret. Khi
checker đặt flag, service nhúng flag vào chuỗi AUD NAL type 35. Mỗi AUD mang
1 bit thông qua bit thấp nhất của trường `primary_pic_type`.

Luồng đọc hợp lệ yêu cầu đúng `id` và `token`. Service cũng có tính năng public
share/preview để người khác xem cấu trúc carrier mà không cần token. Backend tin
rằng preview an toàn vì đã strip các VCL slice chứa dữ liệu ảnh hiển thị. Tuy
nhiên preview vẫn giữ các AUD NAL, trong khi chính AUD đang mang kênh ẩn.

Nhiệm vụ của đội chơi:

- Attack: tìm carrier public preview của đội khác, tải preview `.h265`, parse
  AUD NAL và khôi phục flag.
- Defense: sửa preview để không còn rò kênh AUD, nhưng vẫn giữ dashboard,
  `/api/store`, `/api/read` và checker hoạt động bình thường.

## File nộp theo yêu cầu form

- File service Docker: thư mục `service/`
- File writeup attack và defense: `solution/ATTACK.md`, `solution/DEFENSE.md`,
  và file tổng quan `solution/WRITEUP.md`
- File checker: `checker/checker.py`
- File giải trình hoạt động checker: `checker/CHECKER_EXPLAIN.md`

## Chạy service local

```bash
cd service
docker compose up --build
```

Service mặc định lắng nghe tại:

```text
http://127.0.0.1:8000
```

## API chính

```text
GET  /
GET  /health
POST /api/store
POST /api/read
POST /api/carrier
GET  /api/vaults
GET  /share/<id>
GET  /api/share/<id>/preview.h265
```

Trong đó `/api/carrier` là route tải carrier hợp lệ nhưng yêu cầu đúng `id` và
`token`. Điểm yếu nằm ở `/api/share/<id>/preview.h265`: preview công khai không
có VCL slice nhưng vẫn giữ AUD NAL chứa kênh ẩn.

## Cơ chế giấu tin

Carrier là raw HEVC Annex-B gồm các NAL unit có start code:

```text
00 00 00 01
```

Service chèn packet:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

vào chuỗi AUD NAL. Với mỗi AUD:

```text
nal_unit_type = 35
hidden_bit = primary_pic_type & 1
```

## Flag mẫu

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Khi vận hành attack/defense thật, checker sẽ đặt flag mới theo từng vòng.
