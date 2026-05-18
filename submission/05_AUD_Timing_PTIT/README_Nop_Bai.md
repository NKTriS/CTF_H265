# Gói nộp bài Jeopardy: AUD Timing

## Nội dung gói

Gói này được chuẩn bị theo yêu cầu trong form đăng ký/góp ý bài Jeopardy/Attack Defense.

```text
README_Nop_Bai.md          Mô tả gói nộp
DE_BAI.md                  Đề bài cho người chơi
public/                    File phát cho người chơi
solution/WRITEUP.md        Writeup chi tiết
solution/solve.py          Script giải tham khảo
challenge.yml              Metadata challenge
```

## Thông tin bài

- Hình thức: Jeopardy
- Chủ đề: H.265/HEVC steganography
- Độ khó: Khá khó
- Số bước trong writeup: 16 bước
- Flag format: `blockChainPTIT{}`

## Flag

```text
blockChainPTIT{4ud_pr1m4ry_p1c_type_order_1s_the_ch4nnel}
```

## File phát cho người chơi

Chỉ phát nội dung trong thư mục:

```text
public/
```

Không phát thư mục:

```text
solution/
```

## Ghi chú ảnh chụp màn hình

Khi nộp chính thức, có thể chụp thêm các màn hình sau từ máy làm bài:

1. `ffprobe` xác nhận video là HEVC.
2. Script thống kê NAL type.
3. Output solve tìm được `WALK_START`, `WALK_STEP`.
4. Output flag cuối cùng.

Các bước tương ứng đã được mô tả chi tiết trong `solution/WRITEUP.md`.
