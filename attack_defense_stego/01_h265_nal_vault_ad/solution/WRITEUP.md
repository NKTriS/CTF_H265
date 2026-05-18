# H265 NAL Vault AD - Writeup

Writeup da duoc tach thanh hai file rieng de dung dung yeu cau Attack/Defense:

- `solution/ATTACK.md`: cach khai thac, tai carrier `.h265`, parse AUD NAL va lay flag.
- `solution/DEFENSE.md`: cach va service, anh chup man hinh can co, va cach chung minh checker van OK.

## Tom tat loi

Service luu flag vao raw HEVC Annex-B bitstream. API doc hop le `/api/read` co
kiem tra `token`, nhung service lai de lo hai route debug:

```text
/api/debug/list
/api/debug/file/<filename>
```

Attacker tai carrier `.h265`, tach AUD NAL type 35, doc bit an trong
`primary_pic_type & 1`, roi khoi phuc packet:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

Defense chinh la xoa hoac chan hai endpoint debug, dong thoi giu nguyen
`/health`, `/api/store`, va `/api/read` de checker van hoat dong.
