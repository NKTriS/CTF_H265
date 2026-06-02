# H265 Evidence Portal AD - Writeup

Writeup được tách thành hai file chính:

- `solution/ATTACK.md`: phân tích một root bug lớn và nhiều hướng khai thác từ bug đó.
- `solution/DEFENSE.md`: chiến lược vá tổng thể cho cả class lỗi, không vá từng dấu hiệu.

Phần checker/platform nằm ở:

- `checker/checker.py`: checker `check/put/get` kiểu Hackerdom/ADArena.
- `checker/adarena_task.yml`: cấu hình đề xuất cho 20 round, 300 giây/round, flag lifetime 5.
- `checker/ADARENA.md`: cách tích hợp và test checker.

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

Trong luồng thực tế hơn, preview này thường được phát hiện qua `/api/cases`,
`/share/<share_id>` hoặc `/api/share/<share_id>/manifest.json`.

Backend tạo bản preview CCTV đã redact và vẫn phát được bằng cách copy NAL từ raw
carrier. Đây là root bug: public artifact bị lẫn private metadata/custody side-channel.
Trong bài này, attacker có nhiều hướng từ cùng một lỗi:

- AUD NAL type 35 chứa timing channel.
- SEI prefix NAL type 39 chứa debug trace đã mask.
- Parameter set NAL type 34 chứa trace `H5PSET`.
- Diagnostics public trả `custody_hint` có thể giải ngược.
- Thumbnail public làm lộ custody hint qua HTTP header.
- Operator debug route trả marker nếu còn deploy.
- Preview cache cũ có thể vẫn giữ artifact sinh bởi sanitizer lỗi.

Flag/custody marker không nằm ở dạng đọc thẳng. Packet gốc là:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

Defense chính là sửa preview theo allowlist NAL an toàn, strip metadata phụ như
AUD/SEI/parameter set trace, invalidate preview cache cũ bằng sanitizer version,
tắt diagnostics/debug route public, bỏ custody header ở thumbnail, đồng thời giữ
nguyên dashboard, `/api/store`, `/api/read` và checker.

Checker chỉ public `flag_id`, không public token. Khi `get`, checker tự tính token
từ `flag_id + flag` do hệ thống chấm truyền lại, nên attacker không thể bỏ qua bài
bằng cách gọi `/api/read` nếu chỉ biết `flag_id`.
