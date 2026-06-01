# H265 Evidence Portal AD - Defense Index

Phần defense được tách theo từng vòng để thể hiện đúng nhịp attack-defense:

- `DEFENSE_ROUND_1.md`: vá lỗi chính bằng cách strip AUD NAL type 35 khỏi public preview.
- `DEFENSE_ROUND_2.md`: vá phần còn sót sau khi attacker khai thác stale preview cache.

Patch nộp cuối:

```bash
git apply solution/defense.patch
```

Patch cuối đã bao gồm cả hai lớp:

- Không copy AUD NAL type 35 sang preview public.
- Không dùng lại preview cache cũ nếu cache chưa được sinh bởi sanitizer version mới.

Luồng đọc khuyến nghị:

```text
ATTACK_ROUND_1.md
-> DEFENSE_ROUND_1.md
-> ATTACK_ROUND_2.md
-> DEFENSE_ROUND_2.md
```
