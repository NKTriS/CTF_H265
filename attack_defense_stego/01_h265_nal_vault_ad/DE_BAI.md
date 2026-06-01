# Đề bài Attack/Defense CTF: H265 Evidence Portal AD

## Thông tin chung

- Tên bài: H265 Evidence Portal AD
- Chủ đề: H.265/HEVC Annex-B, CCTV redaction, preview sanitizer, metadata side-channel
- Hình thức: Attack/Defense
- Độ khó đề xuất: Khó
- Flag format: `blockChainPTIT{}`

## Mô tả

H265 Evidence Portal là một web service mô phỏng cổng quản lý bằng chứng CCTV. Điều tra viên dùng dashboard tại `/` để import CCTV evidence từ camera/source, lưu raw H.265 evidence carrier và kiểm tra custody marker bằng operator token.

Marker là dữ liệu nội bộ phục vụ chain-of-custody. Trong môi trường CTF, checker đặt flag động vào marker khi gọi API import case.

Service có kiến trúc giống một bài attack-defense thật hơn:

- `proxy` Nginx phục vụ frontend tĩnh.
- `backend` Flask xử lý API và H.265.
- `preview-worker` render preview bất đồng bộ.
- `postgres` lưu metadata case, audit trail và preview job queue.

Service cũng có operator login, registry camera, public case/share link, manifest, audit trail và redacted preview.

## Root bug

Bug lớn của bài nằm ở public preview pipeline:

```text
Service tạo redacted-preview.h265 bằng cách copy NAL từ private raw evidence carrier.
Preview đã redact phần hình ảnh, nhưng vẫn copy nhầm metadata/custody side-channel.
```

Đây không phải một bug nhỏ kiểu quên check token. `/api/read` và `/api/carrier` vẫn yêu cầu đúng `id` và `token`.

Vấn đề là preview public bị lẫn dữ liệu nội bộ. Từ cùng một root bug này, attacker có nhiều hướng khai thác:

- AUD NAL type 35 chứa timing channel.
- SEI prefix NAL type 39 chứa operator debug trace đã mask.
- Preview cache cũ có thể vẫn giữ artifact sinh bởi sanitizer lỗi.

Vì vậy defender không thể chỉ vá một dấu hiệu là xong. Defense đúng phải xử lý cả class lỗi: public preview không được copy metadata không nằm trong allowlist an toàn.

## Nhiệm vụ đội chơi

### Attack

Người chơi cần:

- Recon `/api/cases`, share link hoặc manifest để lấy `case id` và `preview_url`.
- Tải `redacted-preview.h265`.
- Parse HEVC Annex-B NAL.
- Khai thác một hoặc nhiều side-channel còn sót trong preview public:
  - AUD timing channel.
  - SEI debug trace.
  - Stale preview artifact.
- Khôi phục custody marker/flag động do checker đặt.

### Defense

Người chơi cần:

- Giữ dashboard và API hợp lệ hoạt động.
- Giữ `checker check/put/get` chạy bình thường.
- Tạo preview public theo allowlist NAL an toàn.
- Strip metadata phụ như AUD/SEI/debug trace khỏi preview.
- Invalidate preview cache cũ bằng sanitizer version hoặc purge cache.

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
POST /api/operator/login
GET  /api/operator/me
GET  /api/cameras
POST /api/store
POST /api/read
POST /api/carrier
GET  /api/cases
GET  /case/<id>
GET  /share/<share_id>
GET  /api/share/<share_id>/manifest.json
GET  /api/audit
GET  /api/preview-jobs
GET  /api/cases/<id>/redacted-preview.h265
```

`/api/carrier` là route tải raw carrier hợp lệ nhưng cần token. Điểm yếu nằm ở public preview:

```text
GET /api/cases/<id>/redacted-preview.h265
```

## Cơ chế giấu tin

Packet marker:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

AUD channel:

```text
packet bits -> XOR mask theo case id -> Manchester encode -> AUD cadence có decoy
```

Bit thật nằm ở:

```text
nal_unit_type = 35
encoded_bit = primary_pic_type & 1
```

SEI debug trace:

```text
H5DBG || 2-byte length || xor(packet, SHA256("h265-ad-sei-trace:" || case_id || counter))
```

## Flag mẫu

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Khi vận hành attack-defense thật, checker sẽ đặt flag động mới theo từng chu kỳ/team/service.
