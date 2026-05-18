# Ảnh chụp màn hình cần có

Đặt ảnh chụp màn hình vào thư mục này khi nộp bài.

Danh sách ảnh đề xuất:

## Attack

1. `attack-01-service-health.png`
   - Chụp service đang chạy và `/health` trả về `ok`.
2. `attack-02-debug-list.png`
   - Chụp `/api/debug/list` làm lộ file `.h265`.
3. `attack-03-exploit-flag.png`
   - Chụp exploit in ra flag.

## Defense

1. `defense-01-before-exploit-leaks-flag.png`
   - Chụp exploit trước khi vá, output có flag.
2. `defense-02-vulnerable-code.png`
   - Chụp `service/app.py` có hai route debug.
3. `defense-03-patched-code.png`
   - Chụp `service/app.py` sau khi đã xóa debug route.
4. `defense-04-service-health-after-patch.png`
   - Chụp `curl /health` sau khi rebuild/restart service.
5. `defense-05-checker-still-ok.png`
   - Chụp checker `check` hoặc `put/get` trả về `OK`.
6. `defense-06-exploit-blocked.png`
   - Chụp `/api/debug/list` trả về 404 hoặc exploit không in flag.
