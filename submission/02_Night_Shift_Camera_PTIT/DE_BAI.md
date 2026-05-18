# Đề bài Jeopardy CTF: Night Shift Camera

## Thông tin chung

- Tên bài: Night Shift Camera
- Chủ đề: H.265/HEVC steganography
- Hình thức: Jeopardy
- Độ khó đề xuất: Dễ
- Flag format: `blockChainPTIT{}`

## Mô tả

Một video CCTV H.265 bị tải ra ngoài. Không có chuỗi flag rõ ràng hoặc metadata dễ thấy, người chơi cần phân tích kênh ẩn liên quan tới dữ liệu chuyển động.

Nhiệm vụ của người chơi là phân tích các file public, tìm kênh giấu tin trong chuẩn H.265/HEVC và khôi phục flag theo định dạng `blockChainPTIT{...}`.

## File phát cho người chơi

Các file public nằm trong thư mục `public/`:

- `cctv.hevc`
- `cctv_export.log`
- `HINT.txt`

Có thể phát cho người chơi file zip:

```text
dist/02_night_shift_camera_public.zip
```

## Ghi chú cho ban tổ chức

Không đưa thư mục `solution/` cho người chơi. Thư mục này chỉ dùng cho người ra đề/chấm bài, gồm writeup chi tiết và script solve.
