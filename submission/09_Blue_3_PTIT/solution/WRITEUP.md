# Blue 3? - Writeup chi tiết

## 1. Khảo sát file public

Bài cho hai file:

```text
blue.png
HINT.txt
```

Hint:

```text
Không phải màu xanh nào cũng giống nhau.
Nếu nhìn thấy một đường chéo hơi lạ, hãy thử đếm thay vì đoán.
```

Mở `blue.png` lên thì ảnh gần như là một mảng xanh đặc. Với ảnh kiểu này, những bước đầu mình thử là:

```bash
file public/blue.png
strings public/blue.png
binwalk public/blue.png
```

Không có file bị nối thêm, không có text flag lộ ra, cũng không thấy metadata đáng chú ý. Vì hint nhắc đến màu xanh và việc "đếm", mình chuyển hướng từ file carving sang phân tích pixel.

## 2. Đếm màu trong ảnh

Ý tưởng đầu tiên: nếu ảnh thật sự là một màu xanh đặc, phần lớn pixel phải có cùng một giá trị RGB. Nếu có giấu tin bằng thay đổi rất nhỏ, ta sẽ thấy một màu nền áp đảo và một số pixel bị lệch nhẹ.

Mình dùng Pillow đếm tần suất màu:

```python
from collections import Counter
from PIL import Image

im = Image.open("public/blue.png").convert("RGB")
pixels = list(im.getdata())
counter = Counter(pixels)

main_color, main_count = counter.most_common(1)[0]
changed = sum(1 for p in pixels if p != main_color)

print(im.size)
print(main_color, main_count)
print("changed pixels:", changed)
print("number of colors:", len(counter))
```

Kết quả khi mình chạy:

```text
(512, 512)
(64, 77, 180) 259280
changed pixels: 2864
number of colors: 47
```

Ảnh có `512 * 512 = 262144` pixel. Trong đó màu `(64, 77, 180)` chiếm 259280 pixel. Chỉ có 2864 pixel khác màu nền. Như vậy khả năng cao dữ liệu nằm trong các pixel lệch nền.

## 3. Vì sao không đọc LSB?

Với ảnh PNG, phản xạ quen thuộc là thử LSB trước. Nhưng ở đây có hai dấu hiệu làm mình đổi hướng:

- Ảnh gần như một màu phẳng, số màu khác nền rất ít.
- Các pixel khác nền không ngẫu nhiên theo toàn ảnh mà tạo cảm giác có cấu trúc theo đường chéo.

LSB thường giấu bit bằng bit thấp nhất của nhiều pixel. Còn bài này giống kiểu "đếm số lần thay đổi" hơn: mỗi pixel lệch nền đóng góp một lượng rất nhỏ vào một tổng nào đó.

Để kiểm tra, mình trừ từng pixel với màu nền:

```python
delta = (
    pixel[0] - main_color[0],
    pixel[1] - main_color[1],
    pixel[2] - main_color[2],
)
```

Các pixel bị đổi thường chỉ tăng `+1` ở một kênh màu. Điều này rất quan trọng: nếu cộng tổng sai khác RGB trong một vùng, mỗi lần chỉnh pixel sẽ đóng góp đúng `1`.

## 4. Quan sát đường chéo

Hint nhắc đến "đường chéo", nên mình không xét toàn ảnh một lần mà thử hình dung ảnh được chia thành nhiều block nhỏ nằm dọc theo đường chéo chính.

Nếu flag có độ dài `n`, ảnh sẽ được chia như sau:

```text
block 0: vùng đầu đường chéo
block 1: vùng tiếp theo
block 2: vùng tiếp theo
...
block n-1: vùng cuối đường chéo
```

Với kích thước ảnh 512x512, nếu giả sử flag dài `n` ký tự:

```text
width  = 512 // n
height = 512 // n
```

Ký tự thứ `i` sẽ nằm trong vùng:

```text
x từ width*i  đến width*(i+1)-1
y từ height*i đến height*(i+1)-1
```

Đây chính là kiểu chia block chạy theo đường chéo. Khi `n` sai, vùng bị chia lệch và tổng sai khác không ra ký tự đọc được. Khi `n` đúng, mỗi vùng gom đúng lượng thay đổi của một ký tự.

## 5. Khôi phục từng ký tự

Vì mỗi pixel bị đổi đóng góp `+1` ở đúng một kênh, tổng sai khác RGB trong block có thể được tính:

```python
total = 0
for x in range(width * index, width * (index + 1)):
    for y in range(height * index, height * (index + 1)):
        total += sum(pixels[x, y][k] - main_color[k] for k in range(3))
```

Nếu block ứng với ký tự `'A'`, tổng sẽ là `65`. Nếu ứng với `'{'`, tổng sẽ là `123`. Nói cách khác:

```python
char = chr(total)
```

Điểm chưa biết duy nhất là độ dài flag. Nhưng flag có format `blockChainPTIT{...}`, nên có thể brute-force độ dài từ 1 đến 512 và kiểm tra regex.

Regex mình dùng:

```python
r"blockChainPTIT\{[0-9A-Za-z_]*\}"
```

## 6. Script giải

Script giải nằm ở:

```text
solution/solve.py
```

Phần lõi của solver:

```python
for length in range(1, image.size[0] + 1):
    candidate = decode_with_length(image, length, main_color)
    if FLAG_RE.fullmatch(candidate):
        return candidate
```

Trong `decode_with_length`, solver:

```text
1. Chia ảnh thành length vùng trên đường chéo.
2. Với mỗi vùng, cộng sai khác RGB so với màu nền.
3. Đổi tổng sang ký tự ASCII.
4. Ghép lại thành chuỗi.
```

Khi độ dài sai, chuỗi sinh ra không khớp format. Khi độ dài đúng, chuỗi hiện ra rất sạch.

## 7. Chạy và lấy flag

Chạy solver:

```bash
python solution/solve.py public/blue.png
```

Output:

```text
blockChainPTIT{m0r3_blU3_st3g4n0gr4phy_d4_b4_d33}
```

Ảnh minh chứng:

![Kết quả chạy solver](screenshots/solve_output.png)

Flag:

```text
blockChainPTIT{m0r3_blU3_st3g4n0gr4phy_d4_b4_d33}
```
