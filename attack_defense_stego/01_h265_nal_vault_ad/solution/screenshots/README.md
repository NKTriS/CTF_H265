# Ảnh chụp màn hình cần có

Đặt ảnh chụp màn hình vào thư mục này khi nộp bài.

Danh sách ảnh đề xuất:

## Attack

1. `attack-01-dashboard.png`
   - Chụp dashboard `/` có form store/read và public preview.
2. `attack-02-vaults.png`
   - Chụp `/api/vaults` làm lộ target id và preview URL.
3. `attack-03-preview-download.png`
   - Chụp tải được public preview `.h265`.
4. `attack-04-exploit-flag.png`
   - Chụp exploit in ra flag.

## Defense

1. `defense-01-before-exploit-leaks-flag.png`
   - Chụp exploit trước khi vá, output có flag.
2. `defense-02-vulnerable-preview-code.png`
   - Chụp `service/app.py` có hàm preview giữ lại AUD NAL.
3. `defense-03-patched-preview-code.png`
   - Chụp `service/app.py` sau khi preview đã strip AUD NAL.
4. `defense-04-service-health-after-patch.png`
   - Chụp `curl /health` sau khi rebuild/restart service.
5. `defense-05-checker-still-ok.png`
   - Chụp checker `check` hoặc `put/get` trả về `OK`.
6. `defense-06-exploit-blocked.png`
   - Chụp exploit không còn in flag từ public preview.
