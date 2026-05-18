# Solution - CABAC Merge Index

Flag nằm trong parity của `merge_idx` trong các record merge mode usable.

Chỉ lấy record thỏa:

```text
merge_flag == 1
candidate_count >= 2
usable == 1
```

Quy tắc:

```text
merge_idx chẵn -> bit 0
merge_idx lẻ   -> bit 1
```

Lấy 29 ký tự đầu, tức 232 bit, ghép mỗi 8 bit thành một byte.

Flag:

```text
HEVC{cabac_merge_idx_channel}
```

Tài khoản đáng ngờ trong ghi chú: `cam-admin`.
