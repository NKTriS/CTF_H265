# H265 Evidence Portal AD - Attack Index

Phần attack được tách theo từng vòng để đúng kiểu attack-defense:

- `ATTACK_ROUND_1.md`: khai thác public redacted preview, parse H.265 AUD NAL type 35 và lấy flag.
- `ATTACK_ROUND_2.md`: sau khi đội phòng thủ strip AUD trong code, tiếp tục khai thác preview cũ còn nằm trong cache.

File exploit dùng cho cả hai vòng:

```bash
python solution/exploit.py http://127.0.0.1:8000
python solution/exploit.py http://127.0.0.1:8000 --id flag_x
```

Luồng đọc khuyến nghị:

```text
ATTACK_ROUND_1.md
-> DEFENSE_ROUND_1.md
-> ATTACK_ROUND_2.md
-> DEFENSE_ROUND_2.md
```
