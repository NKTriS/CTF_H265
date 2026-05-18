# Solution - HEVC Metadata Slice

Flag chính nằm trong SEI `user_data_unregistered`.

Các bước:

1. Parse Annex B start code để tách NAL.
2. Tìm NAL type 39 hoặc 40.
3. Chuyển EBSP sang RBSP bằng cách bỏ emulation-prevention byte `0x03`.
4. Parse SEI payload. `user_data_unregistered` có `payload_type = 5`.
5. Bỏ 16 byte UUID đầu payload, phần còn lại bị XOR 1 byte.
6. Brute-force XOR key, plaintext đúng bắt đầu bằng `HEVC-LAB{`.

Flag:

```text
HEVC-LAB{metadata_is_not_pixels}
```

Trong file còn có token phụ ở VCL trailing bytes: `SLICE:qpel_path`.
