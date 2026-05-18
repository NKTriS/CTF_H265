# Solution - CCTV Motion Leak

Flag được giấu bằng parity của motion-vector sample `mv_x`.

Quy tắc:

```text
mv_x chẵn -> bit 0
mv_x lẻ   -> bit 1
```

Trong challenge này, sample motion vector được dựng từ các byte carrier trong VCL NAL. Lấy 200 bit đầu, ghép 8 bit thành byte theo thứ tự bit cao trước.

Flag:

```text
HEVC{motion_leak_in_cctv}
```

User trong log: `intern01`.
