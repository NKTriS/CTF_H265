# Insanity Check Reimagined - Writeup

## 1. Tìm điểm đáng nghi

Bài cho `demo_page.html` và `favicon.svg`. File HTML gần như rỗng, chỉ load favicon:

```html
<link rel="icon" href="favicon.svg" type="image/svg+xml" />
```

Mở `favicon.svg` thì thấy đây là một SVG có CSS animation. Hình nhìn bình thường, nhưng object ở giữa ổ khóa có animation `blink`:

```css
.center {
  animation: blink 1200s infinite;
  animation-delay: 10s;
  animation-timing-function: steps(1, end);
}
```

Trong `@keyframes blink`, SVG đổi `fill` giữa hai giá trị:

```text
#FFFF
#FFF6
```

Các mốc phần trăm không đều nhau, nên mình nghi đây không phải hiệu ứng ngẫu nhiên mà là tín hiệu bật/tắt.

## 2. Extract dữ liệu animation

Làm giống hướng giải public của bài gốc: trích các dòng có `fill:` trong SVG, đưa về dạng `timestamp,color`.

```bash
grep "fill:" favicon.svg \
  | sed -e 's/ {/,/g' -e 's/ fill: #//g' -e 's/; }//g' \
  | tr -d % > favicon_data.txt
```

Một phần output:

```text
0.000,FFFF
0.288,FFF6
0.576,FFFF
0.865,FFF6
1.153,FFFF
```

Mình tính delta giữa các timestamp liên tiếp. Khi in delta ra thì thấy có pattern ngắn/dài rất rõ, giống Morse.

## 3. Nhận ra Morse

Ý tưởng map:

```text
delta ngắn  -> .
delta dài   -> -
delta vừa   -> hết một ký tự
delta rất dài -> hết một từ
```

Với file gốc của bài này, script solve đo unit nhỏ nhất rồi phân loại:

```python
if fill == "#FFFF":
    symbols.append("-" if units >= 3 else ".")
else:
    if units >= 7:
        symbols.append(" / ")
    elif units >= 3:
        symbols.append(" ")
```

Sau khi ghép lại, Morse decode thành:

```text
blockchainptit 1ns4n1ty svg to 1ts fullest
```

Đổi về flag format:

```text
blockChainPTIT{1ns4n1ty_svg_to_1ts_fullest}
```

## 4. Chạy solver

```bash
python solution/solve.py public/favicon.svg
```

Output:

```text
blockChainPTIT{1ns4n1ty_svg_to_1ts_fullest}
```

Ảnh minh chứng:

![Kết quả chạy solver](screenshots/solve_output.png)

Flag:

```text
blockChainPTIT{1ns4n1ty_svg_to_1ts_fullest}
```

## Tham khảo

Writeup public của bài gốc cũng giải theo hướng này: phân tích favicon SVG, extract các mốc `fill`, tính delta và decode Morse.

```text
https://meashiri.github.io/ctf-writeups/posts/202403-utctf/
```
