# Solution - Filler NAL Channel

Flag nằm trong các Filler Data NAL, NAL type 38.

Quy tắc:

```text
số byte 0xff trong payload Filler NAL chẵn -> bit 0
số byte 0xff trong payload Filler NAL lẻ   -> bit 1
```

Sau khi lấy bit từ tất cả Filler NAL và ghép theo nhóm 8 bit, thu được flag.

Flag:

```text
HEVC{filler_nal_length_channel}
```
