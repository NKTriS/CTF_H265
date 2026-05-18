# H265 NAL Vault AD - Writeup

Writeup đã được tách thành hai file riêng để đúng yêu cầu Attack/Defense:

- `solution/ATTACK.md`: cách khai thác, tải carrier `.h265`, parse AUD NAL và lấy flag.
- `solution/DEFENSE.md`: cách vá service, ảnh chụp màn hình cần có, và cách chứng minh checker vẫn OK.

## Tóm tắt lỗi

Service lưu flag vào raw HEVC Annex-B bitstream. API đọc hợp lệ `/api/read` có
kiểm tra `token`, nhưng service lại để lộ hai route debug:

```text
/api/debug/list
/api/debug/file/<filename>
```

Attacker tải carrier `.h265`, tách AUD NAL type 35, đọc bit ẩn trong
`primary_pic_type & 1`, rồi khôi phục packet:

```text
H5AD || 2-byte length || flag || crc32(flag)
```

Defense chính là xóa hoặc chặn hai endpoint debug, đồng thời giữ nguyên
`/health`, `/api/store`, và `/api/read` để checker vẫn hoạt động.
