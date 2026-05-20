# Đề bài Attack/Defense CTF: H265 Evidence Portal AD

## Thông tin chung

- Tên bài: H265 Evidence Portal AD
- Chủ đề: H.265/HEVC Annex-B, CCTV redaction, AUD NAL steganography
- Hình thức: Attack/Defense
- Độ khó đề xuất: Trung bình - khó
- Flag format: `blockChainPTIT{}`

## Mô tả

H265 Evidence Portal là một web service mô phỏng cổng quản lý bằng chứng CCTV.
Điều tra viên có dashboard tại `/` để import CCTV evidence từ một camera/source,
lưu raw H.265 evidence carrier và kiểm tra lại custody marker bằng operator
token. Marker là dữ liệu nội bộ do hệ thống gắn vào evidence để phục vụ
chain-of-custody; người dùng bình thường không cần tự nhập marker trên giao diện.

Để chia sẻ nhanh với bên thứ ba, portal tạo public redacted preview. Backend tin
rằng preview an toàn vì đã strip các VCL slice chứa hình ảnh CCTV. Tuy nhiên
service vẫn giữ các AUD NAL type 35 để bảo toàn nhịp/timing metadata, trong khi
custody marker lại được nhúng vào bit thấp nhất của `primary_pic_type` trong AUD.

Trong môi trường CTF, checker đóng vai hệ thống nội bộ và đặt flag vào trường
custody marker khi gọi API import case.

Nhiệm vụ của đội chơi:

- Attack: tìm case public, tải redacted preview `.h265`, parse AUD NAL và khôi
  phục custody marker/flag.
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
GET  /api/cases
GET  /case/<id>
GET  /api/cases/<id>/redacted-preview.h265
```

Trong đó `/api/carrier` là route tải raw carrier hợp lệ nhưng yêu cầu đúng `id`
và `token`. Điểm yếu nằm ở `/api/cases/<id>/redacted-preview.h265`: preview công
khai không có VCL slice nhưng vẫn giữ AUD NAL chứa custody marker.

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
