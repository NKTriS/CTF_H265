# ADArena Checker Integration

File này mô tả cách đưa bài `H265 Evidence Portal AD` vào mô hình chấm kiểu ADArena/Hackerdom.

## Cấu hình đề xuất

```yaml
name: H265 Evidence Portal AD
checker: checker/checker.py
checker_type: hackerdom
service_port: 8000
checker_timeout: 20
puts: 1
gets: 2
places: 3
round_time: 300
max_round: 20
flag_lifetime: 5
flag_prefix: blockChainPTIT
```

Các giá trị `round_time`, `max_round`, `flag_lifetime` và `flag_prefix` khớp với demo ADArena đã kiểm tra.

## Dữ liệu public và private

Mode `put` in ra đúng một dòng `flag_id`:

```text
flag_id
```

Token đọc marker không được in ra. Checker tự tính token khi `get` bằng `flag_id` và flag thật do hệ thống chấm truyền lại.

Attacker chỉ cần biết `flag_id`/`case_id`. Service public các case qua:

```text
GET /api/cases
GET /case/<case_id>
GET /share/<share_id>
GET /api/share/<share_id>/manifest.json
```

Vì vậy bài vẫn có dữ liệu public để tấn công, nhưng checker không tự làm lộ token riêng tư.

## Places

`places = 3` dùng để làm flag được đặt ở nhiều camera source khác nhau:

| Place | Source |
| --- | --- |
| `1` | `lobby_cam_01` |
| `2` | `parking_gate_02` |
| `3` | `evidence_upload` |

Điều này giúp nhiều round không hoàn toàn giống nhau, nhưng vẫn giữ cùng root bug H.265/public metadata leak.
