# Screenshots can chup cho phan defense

Dat anh chup man hinh vao thu muc nay khi nop bai.

Danh sach anh de xuat:

Attack:

1. `attack-01-service-health.png`
   - Chup service chay va `/health` tra ve `ok`.
2. `attack-02-debug-list.png`
   - Chup `/api/debug/list` lam lo file `.h265`.
3. `attack-03-exploit-flag.png`
   - Chup exploit in ra flag.

Defense:

1. `defense-01-before-exploit-leaks-flag.png`
   - Chup exploit truoc khi va, output co flag.
2. `defense-02-vulnerable-code.png`
   - Chup `service/app.py` co hai route debug.
3. `defense-03-patched-code.png`
   - Chup `service/app.py` sau khi da xoa debug route.
4. `defense-04-service-health-after-patch.png`
   - Chup `curl /health` sau khi rebuild/restart service.
5. `defense-05-checker-still-ok.png`
   - Chup checker `check` hoac `put/get` tra ve `OK`.
6. `defense-06-exploit-blocked.png`
   - Chup `/api/debug/list` tra ve 404 hoac exploit khong in flag.
