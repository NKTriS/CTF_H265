# Stegosaurus LCG - Writeup chi tiết

## 1. Khảo sát file public

Bài cho hai file:

```text
LSBSTEGO_CONFIG_LCG[1664525,1013904223,4294967296]_DEFAULT1111.png
HINT.txt
```

Hint:

```text
Tên file lắm lời hơn bạn tưởng.
LSB cho biết chỗ đọc bit, LCG cho biết thứ tự đọc, DEFAULT1111 cho biết chìa khóa.
```

Tên ảnh dài bất thường:

```text
LSBSTEGO_CONFIG_LCG[1664525,1013904223,4294967296]_DEFAULT1111.png
```

Mình tách tên file thành các phần:

```text
LSBSTEGO        -> dữ liệu có thể nằm trong bit thấp nhất của pixel
LCG[...]        -> thứ tự pixel không đọc tuyến tính mà sinh bằng LCG
1664525         -> a, hệ số nhân
1013904223      -> c, số cộng
4294967296      -> m, modulo
DEFAULT1111     -> password/seed/config mặc định
```

Mở ảnh bằng mắt thường không thấy gì bất thường. `strings`, metadata, hay `binwalk` cũng không ra flag. Vì vậy mình tập trung vào LSB.

## 2. Thử LSB tuyến tính trước

Với bài LSB đơn giản, cách thử đầu tiên là đọc bit thấp nhất của pixel từ trái sang phải, trên xuống dưới:

```text
R&1, G&1, B&1, R&1, G&1, B&1, ...
```

Nhưng khi đọc tuần tự, dữ liệu sinh ra không có text rõ ràng, cũng không thấy header nào dễ nhận diện. Đây là lúc phần `LCG[...]` trong tên file trở nên quan trọng: LSB đúng, nhưng thứ tự đọc pixel sai.

## 3. Hiểu LCG từ tên file

LCG là bộ sinh số giả ngẫu nhiên tuyến tính, có công thức:

```text
X(n+1) = (a * X(n) + c) mod m
```

Với bài này:

```text
a = 1664525
c = 1013904223
m = 4294967296
```

Mỗi giá trị `X(n)` được đưa về vị trí pixel bằng:

```python
pixel_index = X(n) % total_pixels
x = pixel_index % width
y = pixel_index // width
```

Vì LCG có thể sinh trùng vị trí sau khi modulo theo số pixel, solver bỏ qua pixel đã đọc rồi:

```python
if pixel_index in used:
    continue
used.add(pixel_index)
```

Sau đó lấy 3 bit từ 3 kênh:

```python
bits.extend([R & 1, G & 1, B & 1])
```

## 4. Seed đến từ DEFAULT1111

Tên file có `DEFAULT1111`, nên mình dùng nó làm password/config để sinh seed. Trong solver, seed được lấy ổn định bằng SHA-256:

```python
seed = int.from_bytes(sha256(password.encode()).digest()[:4], "little")
```

Với password sai, thứ tự pixel sai hoàn toàn và 6 byte đầu sẽ không đọc được magic. Với password đúng, 6 byte đầu hiện ra:

```text
BCPT 00 2f
```

Trong đó:

```text
BCPT  -> magic/header để biết đã đọc đúng
00 2f -> độ dài ciphertext, 0x002f = 47 byte
```

Khi mình kiểm tra bằng solver:

```text
1664525 1013904223 4294967296 DEFAULT1111 b'BCPT\x00/' 47
```

Đến đây có thể chắc chắn ba thứ đã đúng:

```text
1. Đúng LSB.
2. Đúng thứ tự pixel theo LCG.
3. Đúng password/seed DEFAULT1111.
```

## 5. Vì sao chưa ra flag ngay?

Sau header, phần dữ liệu còn lại không phải plaintext trực tiếp. Nếu in ra thô sẽ thấy byte không đọc được. Điều này khớp với hướng của bài gốc: ngoài steganography còn có một lớp cryptography.

Vì tên file và hint nhấn mạnh `DEFAULT1111`, mình dùng chuỗi này để sinh keystream rồi XOR với ciphertext.

Keystream được sinh bằng SHA-256:

```python
digest = sha256((password + ":blockChainPTIT").encode()).digest()
out = bytearray()
counter = 0

while len(out) < length:
    out.extend(sha256(digest + counter.to_bytes(4, "little")).digest())
    counter += 1
```

Giải mã:

```python
plaintext = bytes(c ^ k for c, k in zip(ciphertext, key))
```

Vì XOR là phép đảo của chính nó, cùng một keystream dùng để mã hóa và giải mã.

## 6. Luồng giải hoàn chỉnh

Từ ảnh public, solver làm theo thứ tự:

```text
1. Parse tên file để lấy a, c, m và password.
2. Dùng password sinh seed.
3. Chạy LCG để sinh thứ tự pixel.
4. Đọc LSB RGB theo thứ tự đó.
5. Ghép bit thành byte.
6. Kiểm tra header BCPT.
7. Lấy độ dài ciphertext.
8. Đọc đủ payload.
9. Sinh keystream từ DEFAULT1111.
10. XOR ciphertext để lấy plaintext.
```

Phần parse tên file:

```python
LCG_RE = re.compile(r"LCG\[(\d+),(\d+),(\d+)\]")
PASSWORD_RE = re.compile(r"_([A-Z0-9]+)\.png$")
```

Phần đọc bit:

```python
header = bytes_from_bits(extract_bits(image, 6 * 8, a, c, m, password))
length = int.from_bytes(header[4:6], "big")
raw = bytes_from_bits(extract_bits(image, (6 + length) * 8, a, c, m, password))
```

## 7. Chạy solver

Script giải nằm ở:

```text
solution/solve.py
```

Chạy:

```bash
python solution/solve.py "public/LSBSTEGO_CONFIG_LCG[1664525,1013904223,4294967296]_DEFAULT1111.png"
```

Output:

```text
blockChainPTIT{l5b_lcg_4nd_x0r_4r3_4_fun_ch41n}
```

Ảnh minh chứng:

![Kết quả chạy solver](screenshots/solve_output.png)

Flag:

```text
blockChainPTIT{l5b_lcg_4nd_x0r_4r3_4_fun_ch41n}
```
