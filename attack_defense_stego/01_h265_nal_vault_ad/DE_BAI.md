# Đề bài Attack/Defense CTF: H265 NAL Vault AD

## Thông tin chung

- Tên bài: H265 NAL Vault AD
- Chủ đề: H.265/HEVC Annex-B, steganography bằng AUD NAL
- Hình thức: Attack/Defense
- Độ khó đề xuất: Dễ
- Flag format: `blockChainPTIT{}`

## Mô tả

H265 NAL Vault là một service lưu bí mật của đội chơi trong raw HEVC Annex-B
bitstream. Khi checker đặt flag, service nhúng flag vào chuỗi AUD NAL type 35.
Mỗi AUD mang 1 bit thông qua bit thấp nhất của trường `primary_pic_type`.

API đọc hợp lệ yêu cầu đúng `id` và `token`. Tuy nhiên, bản gốc để sót debug
endpoint cho phép liệt kê và tải trực tiếp các carrier `.h265`. Nếu attacker tải
được carrier, attacker có thể tách NAL, đọc AUD và khôi phục flag của đội khác.

Nhiệm vụ của đội chơi:

- Attack: khai thác debug endpoint để lấy carrier `.h265` và giải kênh AUD.
- Defense: sửa service để checker vẫn put/get được flag, nhưng attacker không
  còn tải được carrier trái phép.

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
GET  /health
POST /api/store
POST /api/read
GET  /api/debug/list
GET  /api/debug/file/<filename>
```

Trong đó `/api/debug/list` và `/api/debug/file/<filename>` là điểm yếu của bản
gốc.

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
