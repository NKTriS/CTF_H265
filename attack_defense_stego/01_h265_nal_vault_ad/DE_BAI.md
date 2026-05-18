# De bai Attack/Defense CTF: H265 NAL Vault AD

## Thong tin chung

- Ten bai: H265 NAL Vault AD
- Chu de: H.265/HEVC Annex-B, AUD NAL steganography
- Hinh thuc: Attack/Defense
- Do kho de xuat: De
- Flag format: `blockChainPTIT{}`

## Mo ta

H265 NAL Vault la service luu bi mat cua doi choi trong raw HEVC Annex-B
bitstream. Khi checker dat flag, service nhung flag vao chuoi AUD NAL type 35.
Moi AUD mang 1 bit thong qua bit thap nhat cua truong `primary_pic_type`.

API doc hop le can dung `id` va `token`. Tuy nhien ban goc de sot debug endpoint
cho phep liet ke va tai truc tiep cac carrier `.h265`. Neu attacker tai duoc
carrier, attacker co the tach NAL, doc AUD va khoi phuc flag cua doi khac.

Nhiem vu cua doi choi:

- Attack: khai thac debug endpoint de lay carrier `.h265` va giai kenh AUD.
- Defense: sua service de checker van put/get duoc flag, nhung attacker khong con
  tai duoc carrier trai phep.

## File nop theo yeu cau form

- File service docker: thu muc `service/`
- File writeup attack va defense: `solution/WRITEUP.md`
- File checker: `checker/checker.py`
- File giai trinh hoat dong checker: `checker/CHECKER_EXPLAIN.md`

## Chay service local

```bash
cd service
docker compose up --build
```

Service mac dinh lang nghe tai:

```text
http://127.0.0.1:8000
```

## API chinh

```text
GET  /health
POST /api/store
POST /api/read
GET  /api/debug/list
GET  /api/debug/file/<filename>
```

Trong do `/api/debug/list` va `/api/debug/file/<filename>` la diem yeu cua ban
goc.

## Co che giau tin

Carrier la raw HEVC Annex-B gom cac NAL unit co start code:

```text
00 00 00 01
```

Service chen packet:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

vao chuoi AUD NAL. Voi moi AUD:

```text
nal_unit_type = 35
hidden_bit = primary_pic_type & 1
```

## Flag mau

```text
blockChainPTIT{4ud_n4l_d3bug_l34k_br34ks_h265_v4ult}
```

Khi van hanh attack/defense that, checker se dat flag moi theo tung vong.
