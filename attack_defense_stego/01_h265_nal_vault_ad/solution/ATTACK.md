# H265 Evidence Portal AD - Writeup Attack

## 1. Nhìn bài và hiểu bối cảnh

Service là một cổng lưu trữ bằng chứng CCTV. Người điều tra import một case vào
hệ thống, service lưu raw evidence dưới dạng H.265/HEVC Annex-B và gắn thêm một
custody marker nội bộ. Trong môi trường CTF, checker đặt flag vào marker này.

Có hai luồng cần phân biệt:

- Luồng hợp lệ: `/api/read` và `/api/carrier` yêu cầu đúng `case id` và
  `operator token`.
- Luồng public: `/api/cases` và `/api/cases/<id>/redacted-preview.h265` không
  yêu cầu token.

Điểm đáng nghi nằm ở preview public. Giao diện nói đây là bản CCTV đã redact,
vẫn phát được như H.265, nhưng backend giữ lại timing metadata. Với video
HEVC, metadata này nằm trong các NAL unit, đặc biệt là AUD NAL type 35.

## 2. Recon dashboard

Chạy service:

```bash
cd attack_defense_stego/01_h265_nal_vault_ad/service
docker compose up --build -d
```

Mở dashboard:

```text
http://127.0.0.1:8000/
```

Kiểm tra health:

```bash
curl http://127.0.0.1:8000/health
```

Kết quả bình thường:

```json
{"ok":true}
```

Trên dashboard có ba ý quan trọng:

- Có form import CCTV evidence.
- Có form verify custody marker bằng `case id` và `operator token`.
- Có public redacted preview cho từng case.

Từ góc nhìn attacker, token là thứ không có. Vì vậy hướng hợp lý là tìm những
endpoint public trước.

## 3. Tìm case public

Liệt kê các case:

```bash
curl http://127.0.0.1:8000/api/cases
```

Ví dụ:

```json
{
  "items": [
    {
      "id": "flag_1710000000_abcd1234",
      "source": "lobby_cam_01",
      "case_url": "/case/flag_1710000000_abcd1234",
      "preview_url": "/api/cases/flag_1710000000_abcd1234/redacted-preview.h265"
    }
  ],
  "ok": true
}
```

Thông tin quan trọng nhất là `id`. Bài này dùng chính `case id` làm seed để tạo
cadence và XOR mask. Đây là điểm khiến preview public đủ dữ liệu để giải, dù
token không bị lộ.

Thử đọc marker bằng API hợp lệ sẽ bị chặn nếu không có token:

```bash
curl -X POST http://127.0.0.1:8000/api/read ^
  -H "Content-Type: application/json" ^
  -d "{\"id\":\"flag_1710000000_abcd1234\",\"token\":\"wrongtoken\"}"
```

Kết quả:

```json
{"error":"forbidden","ok":false}
```

Vậy ta chuyển sang preview public.

## 4. Tải và kiểm tra preview H.265

Tải preview:

```bash
curl -o preview.h265 http://127.0.0.1:8000/api/cases/flag_1710000000_abcd1234/redacted-preview.h265
```

Kiểm tra bằng `ffprobe`:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview.h265
```

Kết quả mong đợi:

```text
codec_name=hevc
width=640
height=360
```

Điều này cho thấy preview không phải file giả hoàn toàn. Nó là HEVC bitstream
có thể được nhận diện. Vì vậy cách khai thác nên bắt đầu từ parser HEVC
Annex-B, không phải tìm text flag thẳng trong file.

## 5. Tách NAL trong HEVC Annex-B

HEVC Annex-B dùng start code:

```text
00 00 01
00 00 00 01
```

Mỗi đoạn sau start code là một NAL unit. Với HEVC, `nal_unit_type` nằm trong
header byte đầu:

```python
nal_unit_type = (nal[0] >> 1) & 0x3f
```

Ta quan tâm AUD NAL:

```text
nal_unit_type = 35
```

Trong AUD, byte payload đầu tiên chứa `primary_pic_type` ở 3 bit cao:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
raw_bit = primary_pic_type & 1
```

Nếu đây là bản dễ, chỉ cần nối `raw_bit` của mọi AUD là ra `H5AD`. Nhưng bản
này không như vậy.

## 6. Vì sao cách đọc LSB trực tiếp thất bại

Thử nối thẳng `primary_pic_type & 1` của tất cả AUD, 6 byte đầu thường sẽ là
rác, ví dụ:

```text
bc 4a 17 d6 4b cb
```

Nó không phải:

```text
48 35 41 44 00 ...
H  5  A  D
```

Lý do nằm trong `service/stego.py`:

```python
bits = _manchester_encode(_xor_bits(_bytes_to_bits(packet), seed))
```

Trước khi nhúng, packet bị xử lý qua hai lớp:

- XOR mask theo `case id`.
- Manchester encoding.

Sau đó service còn chèn AUD giả:

```python
decoys = 1 + (next(cadence) % 3)
```

Nghĩa là trước mỗi AUD chứa bit thật có 1-3 AUD decoy. Nếu lấy hết AUD theo thứ
tự thì bitstream bị nhiễu ngay từ đầu.

## 7. Reverse thuật toán nhúng

Trong `/api/store`, service gọi:

```python
bitstream = embed_secret(secret, seed=item_id)
```

Vậy seed không phải token. Seed là `case id`, mà attacker lấy được từ
`/api/cases`.

Packet gốc có cấu trúc:

```text
H5AD || 2-byte length || marker || crc32(marker)
```

Quá trình nhúng:

```text
packet bytes
-> đổi sang bit MSB-first
-> XOR với keystream SHA256("h265-ad-mask:" || case_id || counter)
-> Manchester encode: 0 -> 01, 1 -> 10
-> với mỗi encoded bit: chèn 1-3 AUD giả
-> ghi bit thật vào primary_pic_type & 1 của AUD data
```

Quá trình giải phải làm ngược lại:

```text
preview.h265
-> tách NAL
-> lọc AUD type 35
-> lấy raw_bit = primary_pic_type & 1
-> sinh cadence từ case id để bỏ AUD giả
-> lấy các encoded bit thật
-> Manchester decode
-> XOR lại bằng mask theo case id
-> parse H5AD, length, marker, crc32
```

## 8. Code giải thích từng phần

Sinh stream SHA256 giống service:

```python
def byte_stream(seed: str, label: bytes):
    counter = 0
    seed_bytes = seed.encode("utf-8")
    while True:
        block = hashlib.sha256(label + seed_bytes + counter.to_bytes(4, "big")).digest()
        counter += 1
        for value in block:
            yield value
```

Bỏ AUD giả:

```python
encoded = []
pos = 0
cadence = byte_stream(case_id, b"h265-ad-cadence:")

while pos < len(aud_bits):
    decoys = 1 + (next(cadence) % 3)
    for _ in range(decoys):
        next(cadence)
        pos += 1

    next(cadence)
    encoded.append(aud_bits[pos])
    pos += 1
```

Giải Manchester:

```python
01 -> 0
10 -> 1
```

Sau đó XOR lại:

```python
bits = xor_bits(decoded_bits, case_id)
```

Cuối cùng parse packet:

```python
header = bits_to_bytes(bits[:48])
assert header[:4] == b"H5AD"
size = struct.unpack(">H", header[4:6])[0]
packet = bits_to_bytes(bits[:(10 + size) * 8])
marker = packet[6:6 + size]
crc = struct.unpack(">I", packet[6 + size:10 + size])[0]
assert zlib.crc32(marker) & 0xffffffff == crc
```

## 9. Chạy exploit hoàn chỉnh

Nếu muốn để script tự lấy case public:

```bash
python solution/exploit.py http://127.0.0.1:8000
```

Nếu đã biết id:

```bash
python solution/exploit.py http://127.0.0.1:8000 --id flag_1710000000_abcd1234
```

Output:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

## 10. Kết luận attack

Lỗi không nằm ở việc `/api/read` thiếu kiểm tra token. Route đó vẫn kiểm tra
đúng. Lỗi nằm ở assumption sai của preview pipeline: hệ thống nghĩ AUD chỉ là
timing metadata vô hại, nhưng marker lại được giấu trong AUD. Vì preview public
copy AUD nguyên vẹn và `case id` public đủ để khôi phục cadence/mask, attacker
có thể lấy flag chỉ từ redacted preview.

## 11. Ảnh chụp nên có

Đặt ảnh vào `solution/screenshots/` nếu cần nộp kèm:

- `attack-01-dashboard.png`: dashboard có import/verify và redacted preview.
- `attack-02-cases.png`: `/api/cases` làm lộ `id` và `preview_url`.
- `attack-03-ffprobe-preview.png`: preview được nhận diện là HEVC 640x360.
- `attack-04-direct-lsb-fails.png`: đọc LSB trực tiếp không ra `H5AD`.
- `attack-05-exploit-flag.png`: exploit in ra flag.
