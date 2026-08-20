# Giải thích toán học của Q-DDCA có ước lượng tắc nghẽn thời gian thực

Bạn **không cần biết gì về mạng lượng tử** để đọc tài liệu này. Toàn bộ toán ở
đây là toán của bốn môn phổ thông: **xác suất sơ cấp**, **lý thuyết đồ thị**,
**giải tích một biến** và **thống kê mô tả**. Không có cơ học lượng tử, không có
đại số tuyến tính phức, không có phương trình vi phân.

Ẩn dụ dùng suốt tài liệu:

> Mỗi **node** là một **bưu cục** có đúng `memorySize` ô kệ. Mỗi **qubit** là một
> **kiện hàng** cần chuyển từ bưu cục nguồn tới bưu cục đích. Muốn gửi kiện sang
> bưu cục kế tiếp thì phải **hỏi trước**: "còn ô trống không?". Bưu cục đầy thì
> từ chối. Thuật toán là quy tắc chọn bưu cục kế tiếp sao cho ít kiện bị huỷ
> nhất và nhiều kiện tới đích nhất.

Mọi thứ còn lại — "vướng víu lượng tử", "phân phối cặp EPR" — chỉ đổi tên gọi,
không đổi một dấu cộng nào trong công thức.

---

<a id="m0"></a>

## 0. Bản đồ môn học

| Môn học | Dùng ở đâu trong thuật toán | Câu hỏi mà nó trả lời |
|---|---|---|
| Xác suất sơ cấp (tần suất, biến cố độc lập, biến cố đối) | [`historical_stat2`](../entity.py#L406), số hạng $(1-\hat q)^{M-m}$ | *"Hàng xóm này có khả năng đồng ý nhận hàng bao nhiêu phần trăm?"* |
| Xác suất (kỳ vọng của biến hai giá trị) | Hàm chi phí `y` tại [`entity.py:317`](../entity.py#L317) | *"Đi đường này thì trung bình tốn bao nhiêu?"* |
| Trung bình có trọng số / tổ hợp lồi | [`congestion_state`](../entity.py#L427) | *"Trộn hai nguồn tin cũ và mới theo tỉ lệ nào?"* |
| Lý thuyết đồ thị (đường đi ngắn nhất, Dijkstra) | [`Network.route`](../topo.py#L116), [`query_route`](../topo.py#L172) | *"Từ đây tới đích còn mấy chặng?"* |
| Tối ưu rời rạc (`argmin` trên tập hữu hạn có ràng buộc) | Vòng lặp trong [`route`](../entity.py#L262) | *"Trong các lựa chọn còn hợp lệ, cái nào rẻ nhất?"* |
| Giải tích (đạo hàm riêng, sai phân hữu hạn, khai triển Taylor) | [`signal_gap_snapshot`](../exp4.py#L83), cột `slope_edr_per_alpha` trong [`exp5.py`](../exp5.py) | *"Vặn núm này thêm một chút thì kết quả nhúc nhích bao nhiêu?"* |
| Số học sơ cấp về hàm mũ $x^n$ với $0<x<1$ | $(1-\hat q)^{M-m}$ | *"Thử 9 lần liên tiếp mà lần nào cũng trượt thì hiếm cỡ nào?"* |
| Thống kê mô tả (trung bình, độ lệch chuẩn tổng thể, chỉ số Jain) | [`exp4.py`](../exp4.py), [`exp5.py`](../exp5.py) | *"Kết quả này có lặp lại trên mọi lần chạy không, hay chỉ may?"* |
| Kẹp giá trị (`clamp`), xử lý trường hợp suy biến | [`memory_utilization`](../entity.py#L421) | *"Nếu mẫu số bằng 0 thì sao?"* |

### Mảng nào là mới so với bản gốc

Bản Q-DDCA gốc (Chen et al., IEEE/ACM ToN 2023) đã có: đồ thị + Dijkstra, xác
suất chấp nhận lịch sử, số hạng $(1-q)^{M-m}$, chi phí drop $2d(s,d)$, và luật
`argmin`. **Phần mới của repo này chỉ nằm ở một chỗ duy nhất**: thay đầu vào
$q^{history}$ bằng một **trung bình có trọng số** giữa $q^{history}$ và mức
trống bộ nhớ đo tại chính thời điểm quyết định:

$$\hat q_v(t) = \alpha\,q_v^{history} + (1-\alpha)\bigl(1-\rho_v(t)\bigr)$$

Đó là toàn bộ luận điểm của tài liệu này. Mọi mục phía sau hoặc dựng nền cho
công thức đó ([mục 1](#m1)–[mục 4](#m4)), hoặc mô tả cỗ máy tiêu thụ nó
([mục 6](#m6)–[mục 10](#m10)), hoặc đo xem nó đáng giá bao nhiêu
([mục 11](#m11)–[mục 12](#m12)).

---

<a id="m1"></a>

## 1. Nền tảng tối thiểu

*Đã biết xác suất phổ thông và Dijkstra? Nhảy thẳng xuống [mục 2](#m2).*

Mục này chỉ dạy những khái niệm **thực sự được dùng lại**. Không có gì thừa.

<a id="s11"></a>

### 1.1 Tần suất là ước lượng của xác suất

Quan sát $T$ lần, thành công $A$ lần. Tần suất thành công là $A/T$. Khi $T$ lớn,
tần suất tiến về xác suất thật (luật số lớn). Khi $T$ nhỏ, tần suất **rất nhiễu**:
1 lần thử thành công cho $A/T = 1$, tức "chắc chắn thành công", điều rõ ràng vô lý.

Đây chính là lý do phải thêm hằng số làm trơn ở [mục 3](#m3).

<a id="s12"></a>

### 1.2 Biến cố độc lập và luật nhân

Hai biến cố độc lập thì xác suất cả hai cùng xảy ra bằng tích hai xác suất:

```
P(A và B) = P(A) · P(B)
```

Lặp $n$ lần cùng một biến cố xác suất $u$, giả thiết độc lập:

```
P(cả n lần đều xảy ra) = u · u · ... · u = u^n
                         └───── n thừa số ─────┘
```

Dùng ở [mục 7](#m7).

<a id="s13"></a>

### 1.3 Biến cố đối

Với biến cố $A$ bất kỳ, $P(\bar A) = 1 - P(A)$ trong đó $\bar A$ là biến cố
"$A$ không xảy ra". Mẹo quan trọng: "ít nhất một lần
thành công" khó đếm trực tiếp, nhưng biến cố đối của nó — "mọi lần đều trượt" —
lại là một tích đơn giản. Nên:

```
P(ít nhất 1 thành công) = 1 − P(mọi lần đều trượt)
```

Dùng ở [mục 7](#m7).

<a id="s14"></a>

### 1.4 Kỳ vọng của một biến chỉ có hai giá trị

Nếu một đại lượng nhận giá trị $c_1$ với xác suất $p$ và $c_2$ với xác suất
$1-p$, thì trung bình dài hạn của nó là

$$E = p\,c_1 + (1-p)\,c_2$$

Đây là "trung bình có trọng số", với trọng số là xác suất. Toàn bộ hàm chi phí
định tuyến ở [mục 9](#m9) chỉ là công thức này.

<a id="s15"></a>

### 1.5 Tổ hợp lồi

Cho hai số $x, y \in [0,1]$ và một trọng số $\alpha \in [0,1]$:

$$z = \alpha x + (1-\alpha) y$$

Hai tính chất cần nhớ:

1. **Bảo toàn khoảng.** $z$ luôn nằm giữa $x$ và $y$, nên $z \in [0,1]$.
   Chứng minh: $z - \min(x,y) = \alpha(x-\min) + (1-\alpha)(y-\min) \ge 0$ vì cả
   hai số hạng không âm; lập luận đối xứng cho cận trên.
2. **Tuyến tính theo $\alpha$.** Viết lại $z = y + \alpha(x-y)$: đồ thị của $z$
   theo $\alpha$ là một **đường thẳng** có hệ số góc $x-y$.

Dùng ở [mục 5](#m5) và [mục 12](#m12).

<a id="s16"></a>

### 1.6 Hàm mũ $u^n$ với $0 < u < 1$

Nhân một số nhỏ hơn 1 với chính nó thì nó tụt rất nhanh:

| $u$ | $u^1$ | $u^2$ | $u^5$ | $u^9$ | ý nghĩa khi $u$ = xác suất trượt |
|---:|---:|---:|---:|---:|---|
| 0,9 | 0,9000 | 0,8100 | 0,5905 | 0,3874 | hàng xóm gần như luôn từ chối |
| 0,7 | 0,7000 | 0,4900 | 0,1681 | 0,0404 | từ chối thường xuyên |
| 0,5 | 0,5000 | 0,2500 | 0,0313 | 0,0020 | năm ăn năm thua |
| 0,0952 | 0,0952 | 0,0091 | 0,0000 | 0,0000 | hàng xóm gần như luôn đồng ý |

Hai trường hợp biên phải nhớ:

- $u^0 = 1$ **theo quy ước**, với mọi $u$ kể cả $u = 0$. Trong Python,
  `0.0 ** 0 == 1.0`. Điều này gây một hệ quả rất cụ thể ở [mục 7.3](#m73).
- $u = 1 \Rightarrow u^n = 1$ với mọi $n$: trượt chắc chắn thì thử bao nhiêu lần
  cũng vô ích.

<a id="s17"></a>

### 1.7 Đạo hàm riêng và sai phân hữu hạn

**Đạo hàm riêng theo $\alpha$** của $z = \alpha x + (1-\alpha)y$ là

$$\frac{\partial z}{\partial \alpha} = x - y$$

tức là "vặn $\alpha$ thêm một đơn vị thì $z$ đổi bao nhiêu". Nó **không phụ
thuộc $\alpha$** — hệ quả trực tiếp của tính tuyến tính ở [mục 1.5](#s15).

**Sai phân hữu hạn** là cách đo đạo hàm khi không có công thức giải tích, chỉ có
bảng số:

$$\frac{\Delta f}{\Delta \alpha} \approx \frac{f(\alpha_k) - f(\alpha_{k-1})}{\alpha_k - \alpha_{k-1}}$$

Đây đúng là hai cột `delta_edr_vs_prev_alpha` và `slope_edr_per_alpha` mà
[`exp5.py`](../exp5.py) ghi ra. Xem [mục 12](#m12).

<a id="s18"></a>

### 1.8 Kẹp giá trị (clamp)

$$\operatorname{clamp}(x) = \max\bigl(0, \min(1, x)\bigr)$$

Đọc từ trong ra: `min(1, x)` chặn trên, `max(0, ·)` chặn dưới. Kết quả luôn thuộc
$[0,1]$. Clamp **không phải phép biến đổi vô hại**: nó làm mất thông tin ở hai
đầu và làm hàm không khả vi tại $x = 0$ và $x = 1$. Xem [mục 4.2](#m42).

<a id="s19"></a>

### 1.9 `argmin` là hàm bậc thang

$\underset{v \in S}{\arg\min}\, f(v)$ trả về **phần tử** làm $f$ nhỏ nhất, không
phải giá trị nhỏ nhất. Tính chất quyết định mọi thứ ở [mục 12.1](#m121): dù $f$
biến thiên **liên tục** theo một tham số, `argmin` chỉ **nhảy** khi thứ hạng giữa
hai ứng viên đảo chiều. Giữa hai lần đảo, tham số đổi bao nhiêu cũng không làm
đổi quyết định.

Quy ước hoà: cài đặt dùng so sánh **ngặt** `if y < min_y` ([`entity.py:318`](../entity.py#L318)),
nên khi hai ứng viên bằng điểm, ứng viên **duyệt trước** thắng. Danh sách ứng
viên đã được sắp xếp tăng dần theo độ dài đường ([`topo.py:176`](../topo.py#L176)),
nên "duyệt trước" = "đường ngắn hơn, hoặc cùng độ dài thì theo thứ tự khai báo
cạnh". Đây là chi tiết then chốt của [mục 13](#m13).

<a id="s110"></a>

### 1.10 Đồ thị, trọng số, đường đi ngắn nhất

Đồ thị vô hướng $G = (V, E)$: $V$ là tập bưu cục, $E$ là tập đường nối. Mỗi cạnh
có **trọng số** `metric`, ở repo này luôn bằng 1 ([`entity.py:456`](../entity.py#L456)),
nên "khoảng cách" $d(u,v)$ đơn giản là **số chặng** của đường ngắn nhất.

Quy ước ký hiệu dùng suốt tài liệu: $s$ là node **gửi gốc**, $u$ là **chặng hiện
tại**, $v$ là một **hàng xóm ứng viên**, và $\text{dst}$ là node **đích**. Vậy
$d(s,\text{dst})$ là độ dài đường ngắn nhất của cả request, còn $d(v,\text{dst})$
là quãng còn lại nếu đi qua $v$.

Dùng ở [mục 2](#m2), [mục 8](#m8), [mục 10](#m10).

---

<a id="m2"></a>

## 2. Đồ thị mạng và bảng khoảng cách

> **Môn: Lý thuyết đồ thị (đường đi ngắn nhất, thuật toán Dijkstra) + Xác suất sơ cấp (đồ thị ngẫu nhiên Erdős–Rényi).**
> **Vị trí trong code:** [`topo.py`](../topo.py), hàm `Network.build`, `Network.route`, `Network.query_route`. Xem [METHODOLOGY_EQUATIONS.md](../METHODOLOGY_EQUATIONS.md).

### Khái niệm nền

Trước khi nói tới tắc nghẽn, thuật toán cần biết **từ mỗi bưu cục tới mỗi bưu cục
khác còn mấy chặng**. Đó là bài toán đường đi ngắn nhất mọi cặp.

### Công thức

Sinh topo: với mỗi cặp node $(i,j)$, tạo cạnh độc lập với xác suất $p$
([`topo.py:86`](../topo.py#L86)). Số cạnh kỳ vọng:

$$E[|E|] = \binom{n}{2} p = \frac{n(n-1)}{2}p$$

Bậc trung bình của một node:

$$E[\deg] = (n-1)p$$

Dijkstra tính $d(u,v)$ thoả hệ thức Bellman:

$$d(u,v) = \min_{w \in N(u)} \bigl( \text{metric}(u,w) + d(w,v) \bigr)$$

### Suy diễn

Với cấu hình chuẩn của [`exp4.py`](../exp4.py) ($n = 50$, $p = 0{,}1$):

$$E[|E|] = \frac{50 \cdot 49}{2}\cdot 0{,}1 = 122{,}5
\qquad\qquad
E[\deg] = 49 \cdot 0{,}1 = 4{,}9$$

tức khoảng 122,5 cạnh và bậc trung bình 4,9.

Đo thực tế trên seed 101: bậc trung bình **4,92**. Khớp.

Đồ thị Erdős–Rényi với bậc trung bình $\approx 5 \gg \ln 50 \approx 3{,}9$ nằm
sâu trong pha liên thông, nên đường kính rất nhỏ. `build()` còn có vòng lặp
"vá liên thông": chừng nào bảng khoảng cách còn ô $= \infty$ thì thêm ngẫu nhiên
một cạnh giữa một cặp chưa với tới nhau ([`topo.py:93`](../topo.py#L93)).

### Ví dụ số

Đo trên 8 seed × 5 request = 40 cặp nguồn–đích của cấu hình `exp5`:

| $d(s,d)$ | số cặp | tỉ lệ |
|---:|---:|---:|
| 1 | 6 | 15 % |
| 2 | 18 | 45 % |
| 3 | 15 | 37,5 % |
| 4 | 1 | 2,5 % |

**Không có cặp nào xa hơn 4 chặng.** Con số này quyết định rất nhiều thứ ở
[mục 8](#m8) và [mục 10](#m10).

### Tại sao dùng ở đây

$d(v,\text{dst})$ là **một trong hai** đầu vào của hàm chi phí ở [mục 9](#m9)
(đầu vào kia là xác suất chấp nhận). $d(s,\text{dst})$ đặt ra cả hình phạt drop
([mục 8](#m8)) lẫn ngân sách độ dài đường ([mục 10.2](#m102)).

### Hạn chế toán học

Dijkstra chạy **một lần** lúc dựng mạng và bảng khoảng cách **không bao giờ cập
nhật** trong suốt mô phỏng. Đây là khoảng cách **hình học tĩnh**, hoàn toàn mù
với tắc nghẽn. Mọi thông tin động của thuật toán phải đi qua đường khác — chính
là ước lượng ở [mục 5](#m5).

Ngoài ra `route()` cài Dijkstra bằng **quét tuyến tính** để tìm đỉnh nhỏ nhất
($O(n^2)$ mỗi nguồn, $O(n^3)$ toàn mạng). Với $n = 50$ thì không sao; với
$n = 5000$ thì phải đổi sang hàng đợi ưu tiên.

---

<a id="m3"></a>

## 3. Xác suất chấp nhận lịch sử

> **Môn: Xác suất sơ cấp (ước lượng tần suất) + Thống kê Bayes sơ cấp (làm trơn cộng thêm hằng số).**
> **Vị trí trong code:** [`entity.py:406`](../entity.py#L406), hàm `historical_stat2`. Xem [METHODOLOGY_EQUATIONS.md, Equation 1](../METHODOLOGY_EQUATIONS.md).

### Khái niệm nền

Bưu cục $v$ đã được hỏi $T_v$ lần, đồng ý $A_v$ lần. Ước lượng "lần sau nó có
đồng ý không?".

### Công thức

$$q_v^{history} = \frac{A_v + \epsilon}{T_v + \epsilon}, \qquad \epsilon = 0{,}5$$

($\epsilon = 0{,}5$ là giá trị mặc định của repo.)

Khi $T_v = 0$, code trả về $1{,}0$ bằng một nhánh riêng ([`entity.py:413`](../entity.py#L413)).

### Suy diễn: $\epsilon$ thực sự làm gì

Đặt $F_v = T_v - A_v$ là **số lần bị từ chối**. Thay vào:

$$q_v^{history} = \frac{T_v - F_v + \epsilon}{T_v + \epsilon}
= \frac{(T_v + \epsilon) - F_v}{T_v + \epsilon}
= 1 - \frac{F_v}{T_v + \epsilon}$$

Đây là dạng đọc được nhất của công thức:

```
q_history = 1 −    F        F = số lần bị từ chối
                ───────
                T + ε       ε chỉ làm phình mẫu số của số hạng phạt
```

Ba hệ quả rút ra ngay:

1. **$\epsilon$ chỉ làm nhẹ hình phạt, không kéo về 0,5.** Đây là điểm hay bị
   hiểu nhầm. Làm trơn Laplace kinh điển là $(A+\epsilon)/(T+2\epsilon)$ và nó
   kéo ước lượng về $1/2$. Ở đây mẫu số chỉ cộng $\epsilon$ chứ không phải
   $2\epsilon$, nên với $F = 0$ ta được đúng $1$ với mọi $\epsilon$. Nó là **núm
   lạc quan**, không phải núm co về trung dung.
2. **Đơn điệu tăng theo $\epsilon$:**
   $\partial q^{history}/\partial \epsilon = F/(T+\epsilon)^2 \ge 0$.
   Độ dốc lớn nhất tại $\epsilon = 0$, bằng $F/T^2$, và tắt dần theo $1/\epsilon^2$.
3. **Giới hạn:** $\displaystyle\lim_{\epsilon\to\infty} q^{history} = 1$. Đặt
   $\epsilon$ quá lớn thì mọi hàng xóm đều "hoàn hảo" và tín hiệu lịch sử chết.

### Ví dụ số

Với $T = 10$:

| $\epsilon$ | $A=0$ (trượt sạch) | $A=5$ | $A=9$ |
|---:|---:|---:|---:|
| 0 | 0,0000 | 0,5000 | 0,9000 |
| 0,1 | 0,0099 | 0,5050 | 0,9010 |
| **0,5** | **0,0476** | **0,5238** | **0,9048** |
| 1 | 0,0909 | 0,5455 | 0,9091 |
| 2 | 0,1667 | 0,5833 | 0,9167 |
| 10 | 0,5000 | 0,7500 | 0,9500 |
| 100 | 0,9091 | 0,9545 | 0,9909 |

Cột $A=9$ gần như không nhúc nhích; cột $A=0$ đổi gấp 10 lần. Đúng như suy diễn:
$\partial q/\partial\epsilon = F/(T+\epsilon)^2$ tỉ lệ thuận với $F$.

<a id="m31"></a>

### 3.1 Cửa sổ trượt: lịch sử chỉ nhớ 10 quan sát

[`update2`](../entity.py#L442) đẩy kết quả mới vào cuối danh sách và **xoá phần
tử đầu** khi vượt `query_ans_max_len = 10`. Nên luôn có $T_v \le 10$.

Hệ quả: khi cửa sổ đầy, $q^{history}$ chỉ nhận **11 giá trị rời rạc**
$1 - F/10{,}5$ với $F = 0,\dots,10$:

| $F$ | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| $q^{history}$ | 1,0000 | 0,9048 | 0,8095 | 0,7143 | 0,6190 | 0,5238 | 0,4286 | 0,3333 | 0,2381 | 0,1429 | 0,0476 |

Bước nhảy đều $1/10{,}5 = 0{,}0952$. **Đây là lý do toán học khiến rất nhiều hàng
xóm hoà điểm nhau** — và là lý do cơ chế phá hoà ở [mục 5.2](#m52) có tác dụng.

Ưu điểm của cửa sổ trượt: nó chống lại **quán tính lịch sử**. Nếu giữ toàn bộ
lịch sử với $A=90, T=100$ thì 10 lần từ chối liên tiếp mới hạ ước lượng từ
0,9005 xuống 0,8190 — vẫn còn "rất tốt". Với cửa sổ 10, 10 lần từ chối liên tiếp
đẩy thẳng xuống 0,0476.

<a id="m32"></a>

### 3.2 Trường hợp suy biến

| Tình huống | Kết quả | Hệ quả |
|---|---|---|
| $T_v = 0$ (chưa từng hỏi) | trả về $1{,}0$ qua nhánh `if not history` | Hàng xóm lạ **luôn trông hoàn hảo**. |
| $T_v = 0$, $\epsilon > 0$, nếu bỏ nhánh guard | $\epsilon/\epsilon = 1{,}0$ | Giống hệt. Nhánh guard chỉ tồn tại để $\epsilon = 0$ không chia $0/0$. |
| $T_v = 0$, $\epsilon = 0$, nếu bỏ guard | `ZeroDivisionError` | Chính vì thế mới có guard. |
| $\epsilon = 0$, $A = 0$, $T = 10$ | đúng $0{,}0$ | Kéo theo $\hat q = 0$ ở $\alpha = 1$, rồi $(1-0)^R = 1$ — xem [mục 7](#m7). |

**Điểm yếu.** Lạc quan tuyệt đối với hàng xóm lạ là một lựa chọn "explore" hợp lý
nhưng **không có đối trọng** khi $\alpha = 1$. Ở $\alpha < 1$, số hạng bộ nhớ ít
nhất cũng kéo điểm xuống nếu hàng xóm đó đang đầy.

<a id="m33"></a>

### 3.3 Lịch sử được đánh chỉ số theo *hàng xóm*, không theo *cặp (chặng hiện tại, hàng xóm)*

Trong [`before_send_attempt`](../entity.py#L194), lời gọi là `self.update2(nexthop, ...)`
trong đó `self` là **node gửi gốc**, không phải node đang giữ qubit. Vậy
$A_v, T_v$ gộp mọi quan sát về $v$ từ **mọi chặng** mà các qubit của request này
từng đi qua.

Về mặt toán: đây là ước lượng biên $P(\text{accept} \mid v)$ chứ không phải
$P(\text{accept} \mid u \to v)$. Nếu tỉ lệ chấp nhận thật sự phụ thuộc vào chặng
xuất phát $u$ (ví dụ vì cạnh $u\to v$ hẹp băng thông), ước lượng biên **bị chệch**
theo tần suất các chặng $u$ xuất hiện. Đây là **hạn chế chưa được đo** trong repo.

### Tại sao dùng ở đây

$q^{history}$ là một trong hai đầu vào của [mục 5](#m5).

---

<a id="m4"></a>

## 4. Mức chiếm bộ nhớ và phép kẹp

> **Môn: Số học tỉ lệ (chuẩn hoá) + Giải tích sơ cấp (hàm min/max, tính khả vi).**
> **Vị trí trong code:** [`entity.py:421`](../entity.py#L421), hàm `memory_utilization`. Xem [METHODOLOGY_EQUATIONS.md, Equations 2–3](../METHODOLOGY_EQUATIONS.md).

### Khái niệm nền

"Bưu cục đang đầy bao nhiêu phần trăm kệ?"

### Công thức

$$\rho_v(t) = \max\left(0, \min\left(1, \frac{M_v^{used}(t)}{M_v^{capacity}}\right)\right),
\qquad
M_v^{capacity} \le 0 \Rightarrow \rho_v(t) = 1$$

và tín hiệu thực sự đi vào công thức là **phần còn trống**:

$$1 - \rho_v(t)$$

### Suy diễn

Chuẩn hoá bằng cách chia cho sức chứa làm cho hai bưu cục có kích thước khác nhau
so sánh được trên cùng thang $[0,1]$. Không có chuẩn hoá thì "đang giữ 8 kiện" là
tin vô nghĩa: 8/10 là sắp vỡ, 8/100 là rỗng.

### Ví dụ số

| $M^{used}$ | $M^{capacity}$ | $\rho$ | $1-\rho$ | ý nghĩa |
|---:|---:|---:|---:|---|
| 0 | 10 | 0,00 | 1,00 | kệ rỗng |
| 2 | 10 | 0,20 | 0,80 | thoải mái |
| 5 | 10 | 0,50 | 0,50 | nửa |
| 8 | 10 | 0,80 | 0,20 | sắp kẹt |
| 10 | 10 | 1,00 | 0,00 | đầy, chắc chắn từ chối |

<a id="m41"></a>

### 4.1 $1-\rho$ **không phải** một xác suất

Đây là điểm cần nói thẳng. $\rho_v = 0{,}8$ **không** có nghĩa "xác suất bưu cục
chấp nhận là 0,2". Kiểm tra thực tế trong [`query`](../entity.py#L370) là
`currentSize < memorySize` — một phép so sánh **tất định**. Xác suất chấp nhận
thật, tại đúng thời điểm $t$, chỉ nhận hai giá trị:

$$P(\text{accept}) = \begin{cases} 1 & \rho_v(t) < 1\\ 0 & \rho_v(t) = 1\end{cases}$$

tức là **hàm bậc thang**, còn $1-\rho_v$ là một **xấp xỉ tuyến tính** của nó.
Cách gọi chính xác: *tín hiệu khả dụng tài nguyên tức thời đã chuẩn hoá*
(*normalized instantaneous resource-availability signal*). Nó có ích không phải
vì đúng về xác suất, mà vì nó **đơn điệu giảm theo mức tắc nghẽn** và **liên
tục**, hai tính chất mà hàm bậc thang thật không có.

<a id="m42"></a>

### 4.2 Phép kẹp bóp méo ở đâu

Với `currentSize` và `memorySize` là số nguyên không âm và `currentSize` chỉ tăng
qua `use()` (sau khi `query()` đã xác nhận còn chỗ), tỉ lệ thô **luôn** nằm trong
$[0,1]$. Vậy **clamp thực tế không bao giờ kích hoạt** trong đường chạy hiện tại
— nó là hàng rào phòng thủ.

Nếu nó kích hoạt thì hậu quả toán học là: mọi giá trị $> 1$ bị nén về đúng 1, tức
là **mất hoàn toàn thông tin về mức độ quá tải**. Một bưu cục nhận dư 1 kiện và
một bưu cục nhận dư 50 kiện chấm điểm giống hệt nhau. Hàm cũng mất khả vi tại
biên: đạo hàm nhảy từ $1/M^{capacity}$ xuống 0.

<a id="m43"></a>

### 4.3 Trường hợp suy biến: $M^{capacity} \le 0$

Chia cho 0 là lỗi, nên code trả về $\rho = 1$, tức "đầy hoàn toàn". Đây là lựa
chọn **bảo thủ**: bưu cục không có kệ nào thì đúng là không nhận được kiện nào.
Về toán, đây là mở rộng liên tục hợp lý theo hướng $M^{capacity} \to 0^+$ với
$M^{used} > 0$ cố định, vì khi đó $M^{used}/M^{capacity} \to +\infty$ rồi bị kẹp
về 1. Nhưng nếu $M^{used} = 0$ luôn thì giới hạn là $0/0$ — không xác định, và
quy ước "coi như đầy" là **lựa chọn thiết kế**, không phải hệ quả toán học.

### Tại sao dùng ở đây

$1-\rho_v(t)$ là đầu vào thứ hai của [mục 5](#m5). Nó được đọc **tại đúng thời
điểm quyết định định tuyến**, nên khác với $q^{history}$ ở chỗ nó không trễ.

---

<a id="m5"></a>

## 5. Bộ ước lượng chấp nhận thời gian thực — **đóng góp chính**

> **Môn: Xác suất (trung bình có trọng số / tổ hợp lồi) + Giải tích (tính tuyến tính, đạo hàm riêng).**
> **Vị trí trong code:** [`entity.py:427`](../entity.py#L427), hàm `congestion_state`, gọi qua `stat2`. Xem [METHODOLOGY_EQUATIONS.md, Equation 4](../METHODOLOGY_EQUATIONS.md) và [DOCS/RTC Historical AC.md, §7](RTC%20Historical%20AC.md).

### Khái niệm nền

Ta có hai nguồn tin **không cùng loại**:

- $q_v^{history}$ — kinh nghiệm quá khứ, **ổn định nhưng trễ**;
- $1 - \rho_v(t)$ — trạng thái tài nguyên hiện tại, **tức thời nhưng nhiễu**.

Cần gộp thành một con số duy nhất, vì phần còn lại của thuật toán chỉ nhận đúng
một xác suất.

### Công thức

$$\boxed{\;\hat q_v(t) = \alpha\,q_v^{history} + (1-\alpha)\bigl(1-\rho_v(t)\bigr)\;}
\qquad 0 \le \alpha \le 1$$

```
q̂_v(t) =  α · q_history  +  (1−α) · (1 − ρ_v(t))
          └─────┬─────┘      └────────┬────────┘
        quá khứ, trễ 1 vòng      hiện tại, đọc lúc quyết định
```

### Suy diễn

**Bước 1 — kết quả luôn hợp lệ làm xác suất.** $q^{history} \in [0,1]$ (vì
$0 \le A \le T$), $1-\rho \in [0,1]$ (do phép kẹp ở [mục 4](#m4)), $\alpha \in [0,1]$.
Theo tính chất bảo toàn khoảng của tổ hợp lồi ([mục 1.5](#s15)):

$$\min\bigl(q^{history},\,1-\rho\bigr) \;\le\; \hat q_v(t) \;\le\; \max\bigl(q^{history},\,1-\rho\bigr)
\;\Rightarrow\; \hat q_v(t) \in [0,1]$$

Điều này quan trọng vì [mục 7](#m7) sẽ nâng $(1-\hat q)$ lên luỹ thừa; nếu
$\hat q$ lọt ra ngoài $[0,1]$ thì $(1-\hat q)^R$ có thể âm hoặc lớn hơn 1 và toàn
bộ hàm chi phí mất nghĩa.

**Bước 2 — hai biên.**

$$\alpha = 1 \;\Rightarrow\; \hat q_v = q_v^{history}
\qquad\qquad
\alpha = 0 \;\Rightarrow\; \hat q_v = 1 - \rho_v(t)$$

Biên trái tái tạo **đúng** Q-DDCA gốc; biên phải bỏ hẳn lịch sử.

Nghĩa là **baseline nằm ngay trong không gian tham số**, tại $\alpha=1$. Đây là
thiết kế thí nghiệm tốt: so sánh là so cùng một đoạn code, chỉ khác một hằng số.

**Bước 3 — độ nhạy.**

$$\frac{\partial \hat q_v}{\partial \alpha} = q_v^{history} - \bigl(1-\rho_v(t)\bigr)$$

Xem chi tiết ở [mục 12](#m12). Điểm cần nhớ ngay: nếu hai tín hiệu **bằng nhau**
thì đạo hàm bằng 0 và $\alpha$ **hoàn toàn vô nghĩa** với hàng xóm đó.

### Ví dụ số

Hàng xóm có $A=9, T=10, \epsilon=0{,}5$ nên $q^{history} = 0{,}9048$, và đang
chiếm 9/10 ô nhớ nên $1-\rho = 0{,}1$:

| $\alpha$ | $\hat q_v$ | diễn giải |
|---:|---:|---|
| 1,00 | 0,9048 | "nó vẫn ngon như mọi khi" — mù với việc nó sắp đầy |
| 0,90 | 0,8143 | vẫn ngon |
| 0,50 | 0,5024 | năm ăn năm thua |
| 0,10 | 0,1905 | "nó sắp vỡ" |
| 0,00 | 0,1000 | chỉ nhìn kệ |

Đây là **tuyến tính**: đi từ 0,1 tới 0,9048 theo đúng một đường thẳng.

<a id="m51"></a>

### 5.1 Tại sao không bỏ hẳn lịch sử ($\alpha = 0$)?

Vì $1-\rho$ chỉ biết **một** nguyên nhân thất bại: hết ô nhớ. Nó mù với nghẽn
băng thông đường truyền ([`Link.query`](../entity.py#L473) cũng có thể từ chối),
mù với tranh chấp thời điểm, mù với hành vi bất thường của node.

Ví dụ toán: hai hàng xóm $A, B$ cùng $\rho = 0{,}3$ nên $1-\rho = 0{,}7$ cả hai —
**bộ ước lượng thuần bộ nhớ không phân biệt được**. Nhưng nếu
$q_A^{history} = 0{,}95$ và $q_B^{history} = 0{,}55$ thì tại $\alpha = 0{,}5$:

$$\hat q_A = 0{,}5(0{,}95) + 0{,}5(0{,}7) = 0{,}8250,\qquad
\hat q_B = 0{,}5(0{,}55) + 0{,}5(0{,}7) = 0{,}6250$$

Lịch sử cung cấp đúng phần thông tin mà bộ nhớ không chứa.

<a id="m52"></a>

### 5.2 Cơ chế thật sự có tác dụng: **phá thế hoà**

Đây là kết luận quan trọng nhất và nó **không hiển nhiên từ công thức**. Theo đo
đạc ở [DOCS/alpha_sweep_report.md, §3](alpha_sweep_report.md), vùng $\alpha$ tốt
nhất là **0,90–0,96**, tức bộ nhớ chỉ được **4–10 %** trọng số. Lý do:

1. $q^{history}$ chỉ nhận **11 giá trị rời rạc** ([mục 3.1](#m31)), nên nhiều
   hàng xóm **hoà điểm nhau**.
2. Số hạng $(1-\alpha)(1-\rho_v)$ là đại lượng **liên tục**, nên nó phá thế hoà
   đó ngay cả khi trọng số rất nhỏ.
3. Tại **đúng** $\alpha = 1$, cơ chế phá hoà biến mất. `argmin` với so sánh ngặt
   ([mục 1.9](#s19)) rơi về "chọn phần tử duyệt trước", và vì danh sách được sắp
   theo độ dài đường, lưu lượng bị **dồn hết vào cùng một hàng xóm** cho tới khi
   nó đầy.

Nói cách khác: giá trị của $(1-\alpha)(1-\rho)$ ở đây phần lớn **không phải** là
"ước lượng xác suất chính xác hơn", mà là **một quy tắc phá hoà mang thông tin**.
Điều này giải thích vì sao $\alpha$ nhỏ (bộ nhớ chi phối) lại **không** tốt hơn:
xem bảng ở [alpha_sweep_report §4](alpha_sweep_report.md).

<a id="m53"></a>

### 5.3 Hạn chế toán học

- **Cộng hai đại lượng khác đơn vị ngữ nghĩa.** $q^{history}$ là ước lượng xác
  suất; $1-\rho$ là tín hiệu khả dụng ([mục 4.1](#m41)). Tổ hợp lồi của chúng
  **không còn là ước lượng không chệch của bất kỳ xác suất nào**. Nó là một
  *điểm số* nằm trong $[0,1]$, dùng được vì đơn điệu đúng chiều, không vì đúng
  về xác suất.
- **$\alpha$ là hằng số toàn cục, cố định theo thời gian.** Không thích nghi theo
  tải, theo độ tin cậy của lịch sử, hay theo $T_v$. Một biến thể hiển nhiên chưa
  làm: cho $\alpha$ tăng theo $T_v$ (lịch sử càng dày càng đáng tin).
- **$\rho_v(t)$ chụp tại đúng một thời điểm.** Không làm trơn, không EWMA. Một
  dao động nhất thời của bộ nhớ hàng xóm đi thẳng vào quyết định.
- **Chỉ có tác dụng khi bật định tuyến lại.** `stat2()` chỉ được gọi trong nhánh
  `allow_reroute=True` của [`route`](../entity.py#L262). Với `allow_reroute=False`,
  $\alpha$ **hoàn toàn vô nghĩa** — code chọn thẳng `rt[0][0]`.

---

<a id="m6"></a>

## 6. Số lần thử còn lại

> **Môn: Số học sơ cấp (đếm) + Xác suất (kích thước mẫu của dãy phép thử lặp).**
> **Vị trí trong code:** [`entity.py:274-275`](../entity.py#L274), biến `m`, `M`; cập nhật ở [`qubit.py:attempt`](../qubit.py#L48). Xem [METHODOLOGY_EQUATIONS.md, Equation 5](../METHODOLOGY_EQUATIONS.md).

### Khái niệm nền

Kiện hàng được phép hỏi tối đa $M$ lần **ở mỗi chặng**. Đã hỏi $m$ lần thì còn

$$R = M - m$$

lần nữa trước khi bị huỷ.

### Suy diễn về miền giá trị của $m$

Trình tự trong [`before_send_attempt`](../entity.py#L194):

1. `qubit.attempt()` **tăng** `try_count` lên trước, rồi trả `False` nếu
   `try_count > max_try_count`.
2. Sau đó mới gọi `route(qubit)`, và trong đó `m = qubit.try_count`.

Vậy khi `route()` chạy, $m \in \{1, 2, \dots, M+1\}$, kéo theo

$$R = M - m \in \{M-1,\; M-2,\;\dots,\; 0,\; -1\}$$

- $m = M+1$: `route()` trả `(currhop, None, None)` ngay ở dòng
  [`entity.py:277`](../entity.py#L277), nên $R = -1$ **không bao giờ** vào công
  thức luỹ thừa.
- $m = M$: $R = 0$. Trường hợp này **có** vào công thức, và nó suy biến — xem
  [mục 7.3](#m73).
- Lần thử đầu tiên có $m = 1$, tức $R = M-1$, **không phải** $M$.

`try_count` được **reset về 0** mỗi khi qubit nhảy sang chặng mới
([`qubit.py:39`](../qubit.py#L39)). Nên $M$ là ngân sách **mỗi chặng**, không phải
ngân sách toàn tuyến.

### Ví dụ số

Với $M = 10$: lần thử thứ nhất $R = 9$, thứ hai $R = 8$, …, thứ mười $R = 0$.

### Tại sao dùng ở đây

$R$ là **số mũ** trong [mục 7](#m7). Nó là thứ biến hàm chi phí từ tĩnh thành
phụ thuộc vào việc "còn bao nhiêu cơ hội".

---

<a id="m7"></a>

## 7. Xác suất trượt toàn bộ và bù của nó

> **Môn: Xác suất sơ cấp (luật nhân cho biến cố độc lập, biến cố đối).**
> **Vị trí trong code:** [`entity.py:317`](../entity.py#L317), biểu thức `(1 - p) ** (M - m)`. Xem [METHODOLOGY_EQUATIONS.md, Equations 6–7](../METHODOLOGY_EQUATIONS.md).

### Công thức

$$P_{fail}(v) = \bigl(1 - \hat q_v(t)\bigr)^{R},
\qquad
P_{success}(v) = 1 - \bigl(1 - \hat q_v(t)\bigr)^{R}$$

### Suy diễn

**Bước 1.** Một lần hỏi trượt với xác suất $1 - \hat q_v$ (biến cố đối,
[mục 1.3](#s13)).

**Bước 2.** Giả thiết $R$ lần hỏi là **độc lập** và **cùng xác suất**. Luật nhân
([mục 1.2](#s12)) cho:

$$P_{fail}(v) \;=\; \underbrace{(1-\hat q_v)\times\cdots\times(1-\hat q_v)}_{R} \;=\; (1-\hat q_v)^R$$

(dấu ngoặc dưới gom đúng $R$ thừa số)

**Bước 3.** "Ít nhất một lần thành công" là biến cố đối của "trượt sạch", nên
$P_{success} = 1 - P_{fail}$.

<a id="m71"></a>

### 7.1 Giả thiết độc lập là **sai** — và sai theo hướng nào

Đây là chỗ mô hình lệch khỏi thực tế rõ nhất.

- Các lần hỏi cách nhau `queryTime` = 0,05 s. Bộ nhớ hàng xóm **không** được rút
  thăm lại độc lập giữa hai lần; nó thay đổi chậm hơn thế nhiều.
- Nếu hàng xóm đang đầy và không có kiện nào rời đi trong 0,05 s, thì lần hỏi thứ
  hai trượt **có điều kiện gần như chắc chắn** khi lần một đã trượt:
  đặt $F_k$ là biến cố "lần hỏi thứ $k$ bị từ chối", ta có
  $P(F_2 \mid F_1) \approx 1 \gg 1 - \hat q_v$.

Hệ quả toán học: mô hình độc lập **đánh giá thấp** $P_{fail}$ thật. Với tương
quan dương hoàn hảo, $P_{fail}^{\text{true}} \approx 1-\hat q_v$ chứ không phải
$(1-\hat q_v)^R$. Chênh lệch cực lớn: tại $\hat q = 0{,}5$, $R = 9$, mô hình cho
0,0020 còn cận trên tương quan cho 0,5000 — **sai khác 256 lần**.

Đây là thứ mà tài liệu METHODOLOGY gọi là *"the routing model's independent-attempt
assumption"*. Nó được kế thừa nguyên vẹn từ bài gốc; phần mở rộng của repo này
không đụng tới.

<a id="m72"></a>

### 7.2 Hệ quả: hàm chi phí gần như bão hoà khi $R$ lớn

Vì $(1-\hat q)^R$ tụt theo hàm mũ, chỉ cần $\hat q$ khá tốt và $R$ khá lớn là
$P_{fail}$ về gần 0:

| $\hat q$ | $R=0$ | $R=1$ | $R=2$ | $R=5$ | $R=9$ |
|---:|---:|---:|---:|---:|---:|
| 0,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 |
| 0,1000 | 1,0000 | 0,9000 | 0,8100 | 0,5905 | 0,3874 |
| 0,3000 | 1,0000 | 0,7000 | 0,4900 | 0,1681 | 0,0404 |
| 0,5000 | 1,0000 | 0,5000 | 0,2500 | 0,0313 | 0,0020 |
| 0,7000 | 1,0000 | 0,3000 | 0,0900 | 0,0024 | 0,0000 |
| 0,9048 | 1,0000 | 0,0952 | 0,0091 | 0,0000 | 0,0000 |

**Chống chỉ định.** Ở lần thử đầu tiên với $M = 10$ (tức $R = 9$) và một hàng xóm
có lịch sử tạm được, $P_{fail} \approx 0$. Khi đó hàm chi phí ở [mục 9](#m9) rút
gọn thành $Y(v) \approx d(v,\text{dst})$ — **định tuyến thuần đường ngắn nhất,
ước lượng tắc nghẽn không còn ảnh hưởng gì**. Toàn bộ giá trị của $\hat q$ chỉ
xuất hiện khi $R$ nhỏ **hoặc** $\hat q$ nhỏ. Xem ngưỡng định lượng ở
[mục 10.4](#m104).

<a id="m73"></a>

### 7.3 Trường hợp suy biến $R = 0$: **thuật toán tự tắt**

Ở lần thử cuối ($m = M$), $R = 0$ và theo quy ước $u^0 = 1$ ([mục 1.6](#s16)):

$$P_{fail} = 1,\qquad P_{success} = 0,\qquad Y(v) = 0 \cdot d(v,\text{dst}) + 1 \cdot C_{drop} = C_{drop}$$

**với mọi $v$**, bất kể $\hat q_v$ hay $d(v,\text{dst})$. Ba hệ quả dây chuyền:

1. Mọi ứng viên có `y` bằng nhau, nên theo so sánh ngặt ([mục 1.9](#s19)) ứng viên
   **đầu tiên** trong danh sách đã sắp thắng. Định tuyến rơi về **đường ngắn nhất
   thuần tuý**.
2. Kiểm tra `if min_y > metric_drop` ở [`entity.py:324`](../entity.py#L324) là
   **không** thoả (vì bằng, không lớn hơn), nên qubit **không** bị drop — nó vẫn
   được gửi đi. Đổi thành `>=` sẽ làm mọi qubit ở lần thử cuối bị huỷ ngay.
3. $\alpha$, $\epsilon$, bộ nhớ hàng xóm: **tất cả bị vô hiệu hoá** ở lần thử cuối.

Đây là trường hợp biên có thật, chạy ở mọi request, và không được ghi ở đâu trong
tài liệu gốc của repo.

### Tại sao dùng ở đây

Hai xác suất này là **trọng số** của hai kết cục trong kỳ vọng ở [mục 9](#m9).

---

<a id="m8"></a>

## 8. Hình phạt huỷ kiện

> **Môn: Lý thuyết đồ thị (khoảng cách) + Thiết kế hàm mục tiêu (chi phí ảo).**
> **Vị trí trong code:** [`entity.py:278`](../entity.py#L278), biến `metric_drop`. Xem [METHODOLOGY_EQUATIONS.md, Equation 8](../METHODOLOGY_EQUATIONS.md).

### Công thức

$$C_{drop} = 2\,d(s,d)$$

trong đó $s$ là node **gửi gốc** (không phải chặng hiện tại) và $d$ là đích.

### Suy diễn: tại sao hệ số 2, không phải 1?

Hai đại lượng trong hàm chi phí phải **cùng đơn vị** — đơn vị "số chặng". Nếu
kiện bị huỷ, hệ thống phải tạo một kiện mới từ $s$ và đi lại từ đầu, tốn thêm
$d(s,d)$ chặng. Cộng với $d(s,d)$ chặng đã lãng phí, tổng thiệt hại là $2d(s,d)$.

Kiểm tra tính nhất quán của hệ số bằng cách xét cận: giả sử $C_{drop} = \lambda\,d(s,d)$
và xét một qubit **vừa xuất phát** ($h = d(s,d)$, $R$ nhỏ để $P_{fail}$ đáng kể).
Chi phí của nó là

$$Y = h(1-f) + \lambda h f = h\bigl(1 + (\lambda-1)f\bigr)$$

- $\lambda = 1$: $Y = h$ **với mọi $f$** — hình phạt biến mất, $\hat q$ mất tác
  dụng hoàn toàn. Vô nghĩa.
- $\lambda < 1$: $Y$ **giảm** khi $f$ tăng — thuật toán đi tìm hàng xóm tệ nhất.
  Sai dấu.
- $\lambda > 1$: $Y$ tăng theo $f$. Đúng chiều.

Vậy $\lambda > 1$ là **bắt buộc**; $\lambda = 2$ là giá trị nguyên nhỏ nhất thoả,
và có cách đọc vật lý gọn ("đi lần nữa"). Nhưng nó **chưa được tune** — không có
sweep nào trong repo cho $\lambda$.

### Ví dụ số

Với phân bố $d(s,d)$ đo được ở [mục 2](#m2):

| $d(s,d)$ | $C_{drop}$ | số cặp |
|---:|---:|---:|
| 1 | 2 | 6 |
| 2 | 4 | 18 |
| 3 | 6 | 15 |
| 4 | 8 | 1 |

<a id="m81"></a>

### 8.1 Điểm yếu: $C_{drop}$ đo từ **nguồn**, còn $d(v,\text{dst})$ đo từ **chặng hiện tại**

`metric_drop` dùng `self.net.route_table[self.dest][self][0]` với `self` là node
gửi gốc, nên nó là **hằng số suốt cả request**, không đổi khi qubit tiến gần đích.
Trong khi đó `mt` co lại dần.

Đặt $h$ = khoảng cách còn lại từ chặng hiện tại. Hiệu $C_{drop} - h = 2d - h$
**tăng dần** khi qubit tiến về đích. Vì [mục 9](#m9) sẽ cho thấy độ nhạy của hàm
chi phí theo $f$ đúng bằng $C_{drop} - h$, hệ quả là:

> Càng gần đích, thuật toán càng **sợ huỷ**, càng chịu đi vòng.

Đó có thể là hành vi mong muốn (đã đầu tư nhiều thì đừng bỏ), nhưng nó là **hệ
quả phụ của cách viết code**, không phải một lựa chọn được nêu ra ở đâu.

**Trường hợp suy biến nguy hiểm: $h > C_{drop}$.** Khi đó $C_{drop} - h < 0$ và
$Y$ **giảm** theo $f$ — thuật toán ưu tiên hàng xóm **tệ hơn**. Điều kiện xảy ra
là $h > 2d(s,d)$. Với $d(s,d) = 1$ (6/40 cặp đo được) thì $C_{drop} = 2$ và một
ứng viên có `mt = 3` đã đủ lật dấu. Bộ lọc `mt > lmt` ([mục 10.1](#m101)) thường
chặn được, nhưng **không có gì đảm bảo về mặt toán**. Chưa có test nào khoá điều
này.

---

<a id="m9"></a>

## 9. Kỳ vọng chi phí định tuyến của một ứng viên

> **Môn: Xác suất (kỳ vọng của biến hai giá trị) + Giải tích sơ cấp (hàm affine theo $f$).**
> **Vị trí trong code:** [`entity.py:317`](../entity.py#L317). Xem [METHODOLOGY_EQUATIONS.md, Equation 9](../METHODOLOGY_EQUATIONS.md).

### Công thức

$$Y(v) = \underbrace{\bigl[1 - (1-\hat q_v)^{R}\bigr]}_{P_{success}}\; d(v,\text{dst})
\;+\;
\underbrace{(1-\hat q_v)^{R}}_{P_{fail}}\; C_{drop}$$

Trong code, đúng một dòng:

```python
y = (1 - (1 - p) ** (M - m)) * mt + (1 - p) ** (M - m) * metric_drop
    └──────── P_success ────────┘   └───┘   └──── P_fail ────┘   └────┘
                                   quãng                        phạt huỷ
                                  còn lại
```

### Suy diễn

Đây là kỳ vọng của một biến ngẫu nhiên chỉ có hai kết cục ([mục 1.4](#s14)):

| kết cục | xác suất | chi phí |
|---|---|---|
| có ít nhất một lần được nhận | $1-f$ | $h = d(v,\text{dst})$ chặng còn lại |
| trượt sạch $R$ lần | $f$ | $C_{drop}$ |

**Dạng rút gọn.** Đặt $f = (1-\hat q_v)^R$ và $h = d(v,\text{dst})$:

$$Y(v) = h(1-f) + C_{drop}\,f = h + f\,(C_{drop} - h)$$

```
Y = h + f · (C_drop − h)
    │   │        │
    │   │        └── đòn bẩy: chi phí phụ trội nếu phải huỷ
    │   └── xác suất trượt sạch
    └── chi phí "đi bình thường"
```

Dạng này nói hết:

- $Y$ là hàm **affine (bậc nhất)** theo $f$, hệ số góc $C_{drop} - h$.
- Khi $f = 0$: $Y = h$ — thuần đường ngắn nhất.
- Khi $f = 1$: $Y = C_{drop}$ — thuần hình phạt huỷ.
- **Toàn bộ ảnh hưởng của ước lượng tắc nghẽn đi qua đúng một số: $f$.**

### Ví dụ số

Lấy $h = 2$, $C_{drop} = 6$ nên $C_{drop} - h = 4$:

| $\hat q$ | $R$ | $f$ | $Y = 2 + 4f$ |
|---:|---:|---:|---:|
| 0,9048 | 2 | 0,0091 | 2,0363 |
| 0,7000 | 2 | 0,0900 | 2,3600 |
| 0,5238 | 2 | 0,2268 | 2,9070 |
| 0,3000 | 2 | 0,4900 | 3,9600 |
| 0,0000 | 2 | 1,0000 | 6,0000 |

Toàn dải $\hat q$ chỉ dịch $Y$ từ 2,04 lên 6,00. Nếu hai ứng viên chênh nhau 1
chặng, khoảng dịch chuyển này phải **vượt 1** thì đường dài hơn mới có cơ hội —
định lượng ở [mục 10.4](#m104).

### Tại sao dùng ở đây

$Y$ là hàm mục tiêu duy nhất. Mọi thứ trước đó chỉ để tính nó; mọi thứ sau đó chỉ
để so sánh nó.

---

<a id="m10"></a>

## 10. Chọn chặng kế: lọc ứng viên rồi `argmin`

> **Môn: Tối ưu rời rạc có ràng buộc (`argmin` trên tập hữu hạn) + Xác suất (thăm dò ngẫu nhiên hoá) + Lý thuyết đồ thị (bất biến không lặp đỉnh).**
> **Vị trí trong code:** [`entity.py:262-332`](../entity.py#L262), hàm `route`. Xem [METHODOLOGY_EQUATIONS.md, Equation 10](../METHODOLOGY_EQUATIONS.md) và [alpha_sweep_report §6](alpha_sweep_report.md).

### Công thức

$$v^* = \underset{v \in S_C}{\arg\min}\; Y(v)$$

Qubit bị drop khi $\displaystyle\min_{v \in S_C} Y(v) > C_{drop}$.

Tập ứng viên $S_C$ là tập hàng xóm của chặng hiện tại **sau bốn bộ lọc**:

$$S_C = \Bigl\{v \in N(u) \;\Bigm|\; v \notin \text{route}(q),\;\; mt_v \le \ell,\;\; |\text{route}(q)| + mt_v \le L_{max} \Bigr\}$$

<a id="m101"></a>

### 10.1 Bộ lọc độ dài + thăm dò ngẫu nhiên

$$L_{max} = \max\bigl(d(s,\text{dst}),\; 5\bigr),
\qquad
p_{ce} = 1 - \frac{d(s,\text{dst})}{L_{max}}$$

$$\ell = \begin{cases}
\texttt{min\_mt} + 1 & \text{(xs. } p_{ce})\\[2pt]
\texttt{min\_mt} & \text{(xs. } 1-p_{ce})
\end{cases}$$

Cột phải là **xác suất** của mỗi nhánh; đồng xu được tung lại cho **mỗi** ứng viên.

trong đó `min_mt` là độ dài của ứng viên tốt nhất **tìm được cho tới lúc này**
trong vòng lặp.

**Suy diễn.** Danh sách `rt` đã sắp tăng dần theo `mt`
([`topo.py:176`](../topo.py#L176)). Ban đầu `min_mt = INF`, nên ứng viên đầu tiên
luôn lọt. Sau khi nó thắng, `min_mt` bằng độ dài nhỏ nhất. Từ đó về sau, bộ lọc
`mt > lmt` chỉ cho qua các ứng viên **cùng độ dài**, hoặc **dài hơn đúng 1 chặng
với xác suất $p_{ce}$**. Vậy $p_{ce}$ là **ngân sách đi vòng**: xác suất được
phép cân nhắc một đường vòng 1 chặng, tung lại cho **mỗi** ứng viên.

**Ví dụ số** — đo trên 40 cặp nguồn–đích của cấu hình `exp5`:

| $d(s,\text{dst})$ | $L_{max}$ | $p_{ce}$ | số cặp |
|---:|---:|---:|---:|
| 1 | 5 | 0,80 | 6 |
| 2 | 5 | 0,60 | 18 |
| 3 | 5 | 0,40 | 15 |
| 4 | 5 | 0,20 | 1 |

**Trường hợp suy biến: $d(s,\text{dst}) \ge 5$.** Khi đó $L_{max} = d(s,\text{dst})$,
nên

$$p_{ce} = 1 - \frac{d}{d} = 0$$

**thăm dò tắt hoàn toàn**, và đồng thời ngân sách độ dài đường bằng đúng độ dài
đường ngắn nhất, nên **mọi đường vòng đều bị loại**. Với request xa hơn 4 chặng,
định tuyến lại **không tồn tại về mặt toán học** — thuật toán rơi về đường ngắn
nhất tĩnh. Trong cấu hình thí nghiệm hiện tại điều này **không xảy ra** (mọi
$d(s,\text{dst}) \le 4$), nhưng nó sẽ xảy ra ngay khi $p$ giảm hoặc $n$ tăng.

**Điểm yếu.** Cả $L_{max}$ lẫn $p_{ce}$ chỉ phụ thuộc $d(s,\text{dst})$ — một
đại lượng **tĩnh, cố định suốt request**. Chúng **không phản ứng với tắc nghẽn**
chút nào. Hằng số 5 không có nguồn gốc trong tài liệu nào của repo. Ngoài ra
`min_mt` chỉ được cập nhật **bên trong** nhánh `if y < min_y`, nên khi một ứng
viên ngắn nhưng đắt bị một ứng viên dài hơn đánh bại, cửa sổ lọc **nới rộng ra**
theo cách không hiển nhiên khi đọc code.

<a id="m102"></a>

### 10.2 Ngân sách độ dài toàn tuyến

$$|\text{route}(q)| + mt_v \le L_{max}$$

`route` khởi tạo bằng `[src]` nên $|\text{route}| = 1$ ở chặng đầu. Đây là ràng
buộc **toàn cục**: tổng số chặng đã đi cộng số chặng còn lại không vượt $L_{max}$.

Suy biến: nếu **mọi** ứng viên đều rớt bộ lọc này thì `min_y` giữ nguyên `INF`,
điều kiện `min_y > metric_drop` thoả, và qubit bị **drop ngay lập tức, không
retry**. Nhánh này theo [alpha_sweep_report §8](alpha_sweep_report.md) chiếm
**0,2–5 %** số drop sau bản vá, và **trước bản vá thì không bao giờ chạy**.

<a id="m103"></a>

### 10.3 Bất biến không quay đầu — và cái bẫy toán học đã được vá

$$v \in \text{route}(q) \;\Rightarrow\; v \notin S_C$$

**Tại sao bất biến này phải có.** Đây là ví dụ đẹp về việc một công thức đúng có
thể sinh hành vi sai qua tương tác với phần khác của hệ thống.

Chuỗi nhân quả:

1. Qubit chuyển từ $A$ sang $B$ thành công. Ngay lúc đó $A$ **giải phóng** một ô
   nhớ ([`entity.py:340`](../entity.py#L340)), nên $\rho_A$ **giảm**.
2. Tới lượt $B$ chọn chặng kế, $A$ là hàng xóm **vừa mới trống thêm**, thường là
   hàng xóm **rảnh nhất**.
3. Với $\alpha$ nhỏ, $\hat q_v \approx 1 - \rho_v$, nên $A$ có điểm **cao nhất**.
4. `argmin` chọn $A$ → qubit quay đầu → phát hiện lặp đường → **drop ngay, không
   retry**.

Nói cách khác: **chính hành động chuyển tiếp thành công tự tạo ra mồi nhử ngay
sau lưng qubit.** Đây là vòng phản hồi dương giữa cơ chế giải phóng tài nguyên và
hàm chấm điểm.

Số đo (3 seed, [alpha_sweep_report §6](alpha_sweep_report.md)):

| $\alpha$ | drop trước vá | drop sau vá | trong đó drop do lặp đường |
|---:|---:|---:|---|
| 0,00 | 6337 | 3681 | 3100 → **0** |
| 0,06 | 7764 | 3930 | 4669 → **0** |
| 0,50 | 4267 | 3341 | 1359 → **0** |
| 1,00 | 6545 | 4741 | 2197 → **0** |

Tại $\alpha = 0{,}06$: **60 %** số drop là lặp đường, **100 %** trong số đó là
quay lại đúng node vừa rời, và **100 %** các lần đó node được chọn là hàng xóm
rảnh nhất.

Bản vá là ba dòng, đặt **trước** khi chấm điểm ([`entity.py:306`](../entity.py#L306)):

```python
if np in qubit.route:
    continue
```

Còn một lớp bảo vệ thứ hai ở [`entity.py:329`](../entity.py#L329), vì `nexthop`
vẫn giữ giá trị mặc định `rt[0][0]` nếu không ứng viên nào được chọn.

**Hệ quả toán học của bất biến.** Đường đi của mỗi qubit là một **đường đơn**
(*simple path*) trong đồ thị: không đỉnh nào lặp lại. Kết hợp với ngân sách
$L_{max}$, độ dài đường bị chặn trên bởi $\min(L_{max}, |V|-1)$, nên **không tồn
tại chu trình vô hạn**. Đây là tính chất **kết thúc** (*termination*) của thuật
toán, và trước bản vá nó được đảm bảo bằng cách drop qubit — một cách rất đắt.

<a id="m104"></a>

### 10.4 Suy diễn: **khi nào một đường vòng thực sự thắng?**

Đây là kết quả định lượng quan trọng nhất của mục này và nó không có trong tài
liệu nào của repo.

Xét chặng hiện tại $u$ với hai ứng viên:

- $A$: nằm trên đường ngắn nhất, $h_A = h$, xác suất trượt sạch $f_A$;
- $B$: đi vòng đúng 1 chặng, $h_B = h+1$, xác suất trượt sạch $f_B$.

Dùng dạng rút gọn $Y = h + f(C-h)$ với $C = C_{drop}$:

$$Y_A = h + f_A(C-h), \qquad Y_B = (h+1) + f_B(C-h-1)$$

$B$ thắng khi $Y_B < Y_A$:

$$\begin{aligned}
(h+1) + f_B(C-h-1) &< h + f_A(C-h)\\
1 + f_B(C-h-1) &< f_A(C-h)\\
\boxed{\;f_A \;>\; \frac{1 + f_B\,(C-h-1)}{C-h}\;}
\end{aligned}$$

**Trường hợp thuận lợi nhất cho $B$** ($f_B = 0$, tức $B$ chắc chắn nhận):

$$f_A > \frac{1}{C - h}$$

Tại điểm xuất phát, $h = d(s,\text{dst}) = d$ và $C = 2d$, nên $C - h = d$ và
điều kiện là

$$f_A > \frac{1}{d}
\qquad\Longleftrightarrow\qquad
(1-\hat q_A)^R > \frac{1}{d}
\qquad\Longleftrightarrow\qquad
\hat q_A < 1 - d^{-1/R}$$

**Bảng ngưỡng $\hat q_A$ tối đa để một đường vòng 1 chặng có cơ hội:**

| $d(s,\text{dst})$ | $C_{drop}$ | cần $f_A >$ | $R=1$ | $R=2$ | $R=3$ | $R=5$ | $R=9$ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 1,0000 | *không thể* | *không thể* | *không thể* | *không thể* | *không thể* |
| 2 | 4 | 0,5000 | 0,5000 | 0,2929 | 0,2063 | 0,1294 | 0,0741 |
| 3 | 6 | 0,3333 | 0,6667 | 0,4226 | 0,3066 | 0,1973 | 0,1149 |
| 4 | 8 | 0,2500 | 0,7500 | 0,5000 | 0,3700 | 0,2421 | 0,1428 |

Đọc bảng: với $d = 2$ (45 % số cặp) và $M = 10$ nên $R = 9$ ở lần thử đầu, hàng
xóm trên đường ngắn nhất phải bị chấm dưới **7,41 %** thì một đường vòng mới có
cơ hội. Với $\hat q$ chỉ tụt xuống 0,3 chẳng hạn, đường vòng **không bao giờ**
được chọn.

**Trường hợp suy biến $d(s,\text{dst}) = 1$:** cần $f_A > 1$ — **không thể**.
Khi nguồn và đích kề nhau, không đường vòng nào thắng được, với mọi $\alpha$, mọi
$\epsilon$, mọi trạng thái bộ nhớ. Với 6/40 cặp đo được, **15 % số request chạy
với định tuyến lại bị vô hiệu hoá về mặt toán học**.

**Chống chỉ định tổng hợp.** Ghép kết quả này với [mục 7.2](#m72): đường vòng chỉ
xảy ra ở **cuối** ngân sách thử (khi $R$ nhỏ) hoặc khi ứng viên ngắn nhất đã bị
chấm rất thấp. Ở đầu ngân sách thử, thuật toán **là** đường ngắn nhất. Điều này
khớp với quan sát đo được rằng lợi ích lớn nhất của $\alpha < 1$ nằm ở **phá thế
hoà giữa các ứng viên cùng độ dài** ([mục 5.2](#m52)) chứ không ở việc đổi sang
đường dài hơn.

<a id="m105"></a>

### 10.5 Ngưỡng từ chối

$$\min_{v} Y(v) > C_{drop}
\;\Longrightarrow\;
\texttt{return (u, None, None)}
\;\Longrightarrow\;
\text{drop}$$

**Suy diễn.** Vì $Y = h + f(C-h)$ với $f \in [0,1]$ và $h \le C$, ta có
$Y \in [h, C]$, nên $Y \le C_{drop}$ **luôn đúng** với mọi ứng viên hợp lệ. Kết
luận: điều kiện `min_y > metric_drop` **chỉ có thể thoả khi $S_C$ rỗng** (lúc đó
`min_y` vẫn là `INF`). Nó không phải một phép so sánh chi phí thật, mà là **cách
viết trá hình của "không còn ứng viên nào"**.

Ngoại lệ duy nhất là trường hợp lật dấu $h > C_{drop}$ đã nêu ở [mục 8.1](#m81) —
khi đó $Y$ có thể vượt $C_{drop}$ thật.

<a id="m106"></a>

### 10.6 Sơ đồ dòng chảy toàn bộ

```
(A_v, T_v, ε)  ──► q_history        [mục 3]
                        │
(used, capacity) ─► 1 − ρ_v(t)      [mục 4]
                        │
                   α ───┴──► q̂_v(t)  = α·q_history + (1−α)(1−ρ)   [mục 5]
                                │
                     (M, m) ────┴──► f = (1 − q̂_v)^(M−m)          [mục 6, 7]
                                          │
      d(v,đích) ───────────────────────┐  │
      C_drop = 2·d(s,đích) ────────────┴──┴──► Y(v) = h + f(C−h)  [mục 8, 9]
                                                     │
                              lọc S_C ──────────────►│
                                                argmin Y(v)        [mục 10]
                                                     │
                                                   v* = chặng kế
```

---

<a id="m11"></a>

## 11. Các đại lượng đo kết quả

> **Môn: Thống kê mô tả (trung bình, độ lệch chuẩn tổng thể) + Bất đẳng thức Cauchy–Schwarz (chỉ số công bằng Jain).**
> **Vị trí trong code:** [`exp4.py`](../exp4.py), hàm `jain_fairness`, `percent_change`, `run_simulation`, `aggregate_measurements`. Xem [FULL_GRAPH_EXPERIMENT_REPORT.md §6](../FULL_GRAPH_EXPERIMENT_REPORT.md).

### 11.1 Thông lượng và EDR

$$\text{throughput}_i = \frac{\text{completed}_i}{T_{sim}},
\qquad
\text{EDR} = \sum_{i=1}^{n_{req}} \text{throughput}_i = \frac{\sum_i \text{completed}_i}{T_{sim}}$$

Chỉ là phép chia. $T_{sim} = 10$ s trong mọi thí nghiệm. `mean_request_throughput`
là trung bình cộng của $n_{req}$ request, nên **luôn** bằng $\text{EDR}/n_{req}$ —
hai cột trong CSV chênh nhau đúng một hệ số hằng.

Lưu ý đơn vị: nhãn đồ thị ghi `qubits/s`, còn đại lượng đo thật là **số cặp hoàn
tất mỗi giây**. `dropped_pairs` là **số đếm trong 10 s**, không phải tốc độ — hai
cột này không cùng thứ nguyên dù nằm cạnh nhau.

<a id="m112"></a>

### 11.2 Chỉ số công bằng Jain

$$J(x_1,\dots,x_n) = \frac{\bigl(\sum_i x_i\bigr)^2}{n \sum_i x_i^2}$$

**Suy diễn miền giá trị.** Bất đẳng thức Cauchy–Schwarz với vector $(x_i)$ và
vector $(1,1,\dots,1)$:

$$\Bigl(\sum_i x_i \cdot 1\Bigr)^2 \le \Bigl(\sum_i x_i^2\Bigr)\Bigl(\sum_i 1^2\Bigr) = n\sum_i x_i^2$$

nên $J \le 1$, và dấu bằng xảy ra **khi và chỉ khi** mọi $x_i$ bằng nhau. Cận
dưới: nếu chỉ một $x_k > 0$ còn lại bằng 0 thì $J = x_k^2/(n x_k^2) = 1/n$.

$$\frac{1}{n} \le J \le 1$$

Với $n_{req} = 5$: $J \in [0{,}2;\, 1]$. **$J = 0$ là bất khả thi** với vector
khác không.

**Trường hợp suy biến.** Nếu mọi $x_i = 0$ thì $J = 0/0$. Code trả về **0,0**
([`exp4.py:79`](../exp4.py#L79)) — một quy ước, không phải giá trị toán học, và
nó **nằm ngoài miền $[1/n, 1]$**. Hệ quả cụ thể: một lần chạy không hoàn tất cặp
nào kéo `mean_fairness_index` xuống theo cách **không so sánh được** với các lần
chạy khác. Nếu nó xảy ra trong một seed nào đó, trung bình 3 seed bị bóp méo. Chưa
có kiểm tra nào cảnh báo điều này.

**Chống chỉ định.** Bài gốc báo cáo công bằng bằng **hệ số biến thiên (CV)**, thấp
là công bằng; ở đây là Jain, cao là công bằng. **Hai đường cong không so trực tiếp
được với nhau.**

<a id="m113"></a>

### 11.3 Độ lệch chuẩn tổng thể và phần trăm thay đổi

`statistics.pstdev` dùng **mẫu số $n$** (tổng thể), không phải $n-1$:

$$\sigma = \sqrt{\frac{1}{n}\sum_i (x_i - \bar x)^2}$$

Với $n = 3$ hoặc $n = 8$ seed, đây là ước lượng **chệch xuống** của độ lệch chuẩn
tổng thể thật (hệ số Bessel $n/(n-1)$ là 1,5 khi $n=3$). Nghĩa là **thanh sai số
hẹp hơn thực tế**.

$$\text{pct} = \frac{v - b}{b}\times 100$$

Suy biến: $b = 0$ → trả chuỗi rỗng thay vì `inf`.

### 11.4 Điểm yếu về thiết kế thống kê

- **3 seed là quá ít.** [alpha_sweep_report §3](alpha_sweep_report.md) ghi rõ:
  bản 3 seed kết luận "$\alpha<1$ hơn $\alpha=1$ từ 9 % đến 12 % EDR"; với 8 seed
  con số co lại còn **0–7 %**, do một seed duy nhất (202) kéo lệch trung bình.
- **Không có kiểm định ý nghĩa nào** trong repo. Cách trình bày duy nhất có căn
  cứ là **đếm số seed thắng theo cặp** (paired), như cột "seed thắng" trong báo
  cáo $\alpha$ — đó là một kiểm định dấu thô sơ, và nó cho kết luận vững về **drop**
  (8/8 seed) chứ không về EDR (5–6/8 seed).

---

<a id="m12"></a>

## 12. Đạo hàm theo $\alpha$ và cách đọc đường cong sweep

> **Môn: Giải tích (đạo hàm riêng, sai phân hữu hạn) + Giải tích số (tính không trơn của `argmin`).**
> **Vị trí trong code:** [`exp4.py:83`](../exp4.py#L83) `signal_gap_snapshot`; [`exp5.py`](../exp5.py) `aggregate_sweep`, các cột `delta_edr_vs_prev_alpha` và `slope_edr_per_alpha`.

### Công thức

$$\frac{\partial \hat q_v}{\partial \alpha} = q_v^{history} - \bigl(1 - \rho_v(t)\bigr)$$

Đại lượng này được gọi là **khoảng lệch tín hiệu** (*signal gap*).

<a id="m121"></a>

### 12.1 Ba kết luận rút ra từ đạo hàm

**(a) Độ nhạy theo $\alpha$ không phụ thuộc $\alpha$.** Đạo hàm là hằng số theo
$\alpha$ ([mục 1.5](#s15)), nên $\hat q_v$ **tuyến tính** theo $\alpha$. Suy ra:
mọi phi tuyến quan sát được trong đường cong EDR — vùng phẳng ở giữa, dốc sụp ở
$\alpha \to 1$ — **không đến từ công thức mục 5**. Chúng đến từ hai tầng phía sau:

1. $f = (1-\hat q)^R$ — hàm luỹ thừa, **lồi mạnh** theo $\hat q$;
2. `argmin` — hàm **bậc thang** ([mục 1.9](#s19)): $\hat q$ đổi liên tục nhưng
   chặng kế chỉ đổi khi thứ hạng đảo.

Đây là lý do toán học khiến đường cong EDR có thể phẳng trên cả một dải $\alpha$
rồi nhảy đột ngột.

**(b) $\alpha$ chỉ có tác dụng khi hai tín hiệu bất đồng.** Nếu
$q^{history} = 1-\rho_v$ thì đạo hàm bằng 0 và $\alpha$ **vô nghĩa** với hàng xóm
đó. `signal_gap_snapshot` đo đúng đại lượng này; cột `mean_abs_signal_gap` cho
**0,29–0,52** suốt sweep ([alpha_sweep_report §5](alpha_sweep_report.md)), tức hai
tín hiệu lệch nhau 29–52 điểm phần trăm — đủ lớn để $\alpha$ có việc để làm.

**(c) Cảnh báo diễn giải: signal gap là biến nội sinh.** Nó được chụp **một lần**
lúc kết thúc mô phỏng, và chính $\alpha$ quyết định lưu lượng chảy đi đâu, từ đó
quyết định $\rho_v$ tại thời điểm chụp. Dùng nó như **chẩn đoán điểm vận hành**,
**không** hồi quy EDR theo nó.

<a id="m122"></a>

### 12.2 Sai phân hữu hạn của sweep

[`exp5.py`](../exp5.py) ghi hai cột:

$$\Delta_k = \overline{\text{EDR}}(\alpha_k) - \overline{\text{EDR}}(\alpha_{k-1}),
\qquad
\text{slope}_k = \frac{\Delta_k}{\alpha_k - \alpha_{k-1}}$$

Đây là **xấp xỉ sai phân tiến** của $\dfrac{d\,\text{EDR}}{d\alpha}$, sai số bậc
$O(\Delta\alpha)$ theo khai triển Taylor:

$$f(\alpha + h) = f(\alpha) + h f'(\alpha) + \frac{h^2}{2}f''(\xi)
\;\Rightarrow\;
\frac{f(\alpha+h) - f(\alpha)}{h} = f'(\alpha) + \frac{h}{2}f''(\xi)$$

**Điểm yếu.** Xấp xỉ này giả định $f$ khả vi. Ở đây $f$ **không khả vi**: nó là
kết quả của một mô phỏng ngẫu nhiên đi qua một `argmin` bậc thang. Với
`--alpha-step 0,02`, "độ dốc" đo được là tỉ số của **nhiễu giữa các seed** chia
cho một bước rất nhỏ, nên nó bị **khuếch đại 50 lần**. Đọc cột `slope` như một
đạo hàm thật là sai; nó chỉ dùng để **định vị chỗ đường cong gãy**.

Hàng đầu tiên có $\Delta$ rỗng vì không có điểm trước — xử lý bằng chuỗi rỗng
trong CSV, đúng như hàm `demo()` khoá lại
([`exp5.py`](../exp5.py), `assert rows[0]["delta_edr_vs_prev_alpha"] == ""`).

### 12.3 Lưới $\alpha$ được dựng bằng số nguyên

```python
count = int(round((stop - start) / step))
values = tuple(round(start + index * step, 4) for index in range(count + 1))
```

Cộng dồn `alpha += step` sẽ tích luỹ sai số dấu phẩy động (kinh điển:
$0{,}1 + 0{,}2 = 0{,}30000000000000004$), và giá trị $\alpha = 1{,}0$ có thể không
bao giờ trúng đúng — làm hỏng việc tìm hàng baseline. Nhân từ chỉ số nguyên thì
sai số **không tích luỹ**.

---

<a id="m13"></a>

## 13. Chạy tay một quyết định

Tình huống dựng theo đúng cấu hình `exp5` (mọi hằng số đều là hằng số thật của
repo).

### Bối cảnh

| Đại lượng | Giá trị | Nguồn |
|---|---|---|
| $d(s,\text{dst})$ | 3 chặng | *(đồ thị — [mục 2](#m2))* |
| $C_{drop} = 2 \cdot 3$ | 6 | *(đồ thị + thiết kế hàm mục tiêu — [mục 8](#m8))* |
| $L_{max} = \max(3,5)$ | 5 | *(tối ưu có ràng buộc — [mục 10.1](#m101))* |
| $p_{ce} = 1 - 3/5$ | 0,4000 | *(xác suất — [mục 10.1](#m101))* |
| $M$, $m$ | 10, 8 → $R = 2$ | *(đếm — [mục 6](#m6))* |
| $\epsilon$ | 0,5 | *(làm trơn — [mục 3](#m3))* |
| $\alpha$ | 0,9 | *(tổ hợp lồi — [mục 5](#m5))* |
| Đường đã đi | `[s, u]`, độ dài 2 | — |

Qubit đang ở $u$. Hai hàng xóm hợp lệ, **cùng độ dài đường còn lại $mt = 2$**:

| | lịch sử $A/T$ | ô nhớ đang dùng | $\rho$ |
|---|---:|---:|---:|
| $v_1$ (đứng trước trong danh sách đã sắp) | 5/10 | 10/10 | 1,0 |
| $v_2$ | 5/10 | 2/10 | 0,2 |

### Bước 1 — qua các bộ lọc *(tối ưu có ràng buộc — [mục 10](#m10))*

- Không quay đầu: $v_1, v_2 \notin \{s, u\}$ ✔
- Ngân sách độ dài: $2 + 2 = 4 \le 5$ ✔ cho cả hai
- Bộ lọc $mt$: $v_1$ vào đầu tiên khi `min_mt = INF` ✔; sau đó `min_mt = 2` và
  $v_2$ có $mt = 2 \not> 2$ ✔. Đồng hạng nên **đồng xu $p_{ce}$ không ảnh hưởng**.

$S_C = \{v_1, v_2\}$.

### Bước 2 — xác suất chấp nhận lịch sử *(xác suất — [mục 3](#m3))*

$$q_{v_1}^{history} = q_{v_2}^{history} = \frac{5 + 0{,}5}{10 + 0{,}5} = \frac{5{,}5}{10{,}5} = 0{,}5238$$

**Hai hàng xóm hoà điểm tuyệt đối trên lịch sử.**

### Bước 3 — tín hiệu bộ nhớ *(tỉ lệ chuẩn hoá — [mục 4](#m4))*

$$1 - \rho_{v_1} = 1 - 1{,}0 = 0{,}0000, \qquad 1 - \rho_{v_2} = 1 - 0{,}2 = 0{,}8000$$

### Bước 4 — bộ ước lượng *(tổ hợp lồi — [mục 5](#m5))*

$$\begin{aligned}
\hat q_{v_1} &= 0{,}9(0{,}5238) + 0{,}1(0{,}0000) = 0{,}4714 + 0{,}0000 = \mathbf{0{,}4714} \\
\hat q_{v_2} &= 0{,}9(0{,}5238) + 0{,}1(0{,}8000) = 0{,}4714 + 0{,}0800 = \mathbf{0{,}5514}
\end{aligned}$$

Thế hoà đã bị phá. Khoảng cách $0{,}0800 = (1-\alpha)\bigl[(1-\rho_{v_2}) - (1-\rho_{v_1})\bigr]$.

### Bước 5 — xác suất trượt sạch *(luật nhân — [mục 7](#m7))*

$$\begin{aligned}
f_{v_1} &= (1 - 0{,}4714)^2 = 0{,}5286^2 = \mathbf{0{,}2794} \\
f_{v_2} &= (1 - 0{,}5514)^2 = 0{,}4486^2 = \mathbf{0{,}2012}
\end{aligned}$$

### Bước 6 — kỳ vọng chi phí *(kỳ vọng hai kết cục — [mục 9](#m9))*

Dùng dạng rút gọn $Y = h + f(C-h)$ với $h = 2$, $C = 6$, nên $C - h = 4$:

$$\begin{aligned}
Y(v_1) &= 2 + 4(0{,}2794) = 2 + 1{,}1176 = \mathbf{3{,}1176} \\
Y(v_2) &= 2 + 4(0{,}2012) = 2 + 0{,}8049 = \mathbf{2{,}8049}
\end{aligned}$$

### Bước 7 — `argmin` *(tối ưu rời rạc — [mục 1.9](#s19))*

$2{,}8049 < 3{,}1176$ nên $v^* = v_2$. Kiểm tra ngưỡng từ chối
([mục 10.5](#m105)): $2{,}8049 \le 6$, không drop.

### Kết cục

$v_2$ còn 8 ô trống, `query()` trả `True`, kiện được nhận **ngay lần hỏi đầu**.
Không lượt thử nào bị đốt.

<a id="m131"></a>

### Bản baseline quyết định gì trên cùng tình huống?

Baseline là **cùng đoạn code**, chỉ đặt $\alpha = 1$.

$$\begin{aligned}
\hat q_{v_1} &= \hat q_{v_2} = q^{history} = 0{,}5238 \\
f_{v_1} &= f_{v_2} = (1 - 0{,}5238)^2 = 0{,}4762^2 = 0{,}2268 \\
Y(v_1) &= Y(v_2) = 2 + 4(0{,}2268) = \mathbf{2{,}9070}
\end{aligned}$$

**Hoà chính xác.** So sánh ngặt `if y < min_y` ([mục 1.9](#s19)) giữ nguyên ứng
viên duyệt trước, tức $v_1$ — bưu cục **đang đầy**.

Kết cục: `v1.query()` trả `False`, kiện không đi được, lịch thêm một
`QNodeQueryBeforeEvent` sau `queryTime`, `try_count` tăng lên 9, $R$ tụt còn 1.
Một lượt thử bị đốt, và ở lượt sau tình huống gần như y hệt.

**Tại sao baseline không sai theo logic của chính nó.** Với đầu vào mà nó có —
hai hàng xóm cùng lịch sử 5/10, cùng độ dài đường còn lại 2 — hai ứng viên
**không phân biệt được**. Hàm chi phí của nó cho hai giá trị bằng nhau, và đó là
câu trả lời **đúng** cho câu hỏi mà nó đang hỏi. Một quy tắc phá hoà tất định
theo thứ tự sắp xếp là lựa chọn hợp lý duy nhất còn lại. Baseline không tính sai;
nó **thiếu một biến đầu vào**. Toàn bộ đóng góp toán học của repo này là bổ sung
đúng biến đó, với trọng số $1 - \alpha = 0{,}1$.

Lưu ý: nếu $v_1$ và $v_2$ **cũng khác nhau về lịch sử**, baseline đã phân biệt
được và cả hai bản sẽ chọn giống nhau. Đó là lý do lợi ích đo được tập trung ở
**drop** (giảm ≈ 38 %, thắng trên 8/8 seed) chứ không ở EDR (0–7 %, thắng 5–6/8
seed) — xem [alpha_sweep_report §3](alpha_sweep_report.md).

---

<a id="m14"></a>

## 14. Bảng tra cứu

### (a) Công thức → môn học → vị trí

| Công thức | Môn học | Vị trí trong code | Mục |
|---|---|---|---|
| $E[\deg] = (n-1)p$ | Xác suất (đồ thị ngẫu nhiên) | [`topo.py:86`](../topo.py#L86) | [2](#m2) |
| $d(u,v) = \min_w\bigl(\text{metric} + d(w,v)\bigr)$ | Lý thuyết đồ thị (Dijkstra) | [`topo.py:116`](../topo.py#L116) | [2](#m2) |
| $q^{history} = \dfrac{A+\epsilon}{T+\epsilon} = 1 - \dfrac{F}{T+\epsilon}$ | Xác suất (tần suất + làm trơn) | [`entity.py:406`](../entity.py#L406) | [3](#m3) |
| $\rho_v = \max(0,\min(1, \text{used}/\text{cap}))$ | Tỉ lệ + kẹp giá trị | [`entity.py:421`](../entity.py#L421) | [4](#m4) |
| $\hat q_v = \alpha q^{history} + (1-\alpha)(1-\rho_v)$ | Tổ hợp lồi | [`entity.py:427`](../entity.py#L427) | [5](#m5) |
| $R = M - m$ | Đếm | [`entity.py:275`](../entity.py#L275) | [6](#m6) |
| $f = (1-\hat q_v)^R$ | Xác suất (luật nhân) | [`entity.py:317`](../entity.py#L317) | [7](#m7) |
| $C_{drop} = 2d(s,\text{dst})$ | Đồ thị + thiết kế hàm mục tiêu | [`entity.py:278`](../entity.py#L278) | [8](#m8) |
| $Y = h(1-f) + C_{drop} f = h + f(C_{drop}-h)$ | Kỳ vọng hai kết cục | [`entity.py:317`](../entity.py#L317) | [9](#m9) |
| $L_{max} = \max(d,5)$, $p_{ce} = 1 - d/L_{max}$ | Xác suất (thăm dò ngẫu nhiên hoá) | [`entity.py:293`](../entity.py#L293) | [10.1](#m101) |
| $v^* = \arg\min_{v \in S_C} Y(v)$ | Tối ưu rời rạc | [`entity.py:318`](../entity.py#L318) | [10](#m10) |
| $f_A > \dfrac{1 + f_B(C-h-1)}{C-h}$ | Bất đẳng thức (dẫn xuất trong tài liệu này) | — | [10.4](#m104) |
| $J = \dfrac{(\sum x_i)^2}{n\sum x_i^2}$ | Cauchy–Schwarz | [`exp4.py:68`](../exp4.py#L68) | [11.2](#m112) |
| $\sigma = \sqrt{\frac1n\sum(x_i-\bar x)^2}$ | Thống kê mô tả | [`exp4.py`](../exp4.py) | [11.3](#m113) |
| $\partial\hat q/\partial\alpha = q^{history} - (1-\rho_v)$ | Đạo hàm riêng | [`exp4.py:83`](../exp4.py#L83) | [12](#m12) |
| $\Delta f/\Delta\alpha$ | Sai phân hữu hạn | [`exp5.py`](../exp5.py) | [12.2](#m122) |

### (b) Đại lượng **đo được** (không phải tham số)

Đây là những thứ mô phỏng **quan sát** trong lúc chạy. Chúng không được đặt sẵn.

| Ký hiệu | Trong code | Đo cái gì | Miền giá trị |
|---|---|---|---|
| $M_v^{used}(t)$ | `node.currentSize` | Số ô nhớ đang giữ qubit tại thời điểm quyết định | $0 \dots M^{capacity}$ |
| $A_v$ | số phần tử `True` trong `query_list[v]` | Số lần hàng xóm $v$ đã đồng ý nhận | $0 \dots 10$ |
| $T_v$ | `len(query_list[v])` | Tổng số lần đã hỏi $v$ (cửa sổ trượt 10) | $0 \dots 10$ |
| $d(u,v)$ | `route_table[v][u][0]` | Số chặng đường ngắn nhất trên đồ thị đã dựng | $1 \dots \infty$ |
| $mt$ | `neigh[2]` | $1 + d(v,\text{dst})$ với $v$ là hàng xóm — quãng còn lại nếu đi qua nó | $\ge 1$ |
| $m$ | `qubit.try_count` | Số lần đã hỏi ở **chặng hiện tại** (reset mỗi chặng) | $1 \dots M+1$ |
| $\lvert\text{route}\rvert$ | `len(qubit.route)` | Số node đã đi qua, kể cả nguồn | $\ge 1$ |
| `current_send_time` | `Link.current_send_time` | Thời điểm sớm nhất đường truyền rảnh trở lại | thời gian mô phỏng |
| `completed` / `dropped` / `in_flight` | `len(sendedList/dropList/sendingList)` | Số kiện tới đích / bị huỷ / còn đang đi | $\ge 0$ |
| `mean_signal_gap` | `signal_gap_snapshot` | $q^{history} - (1-\rho_v)$, chụp lúc kết thúc | $[-1, 1]$ |

### (c) Hằng số

| Hằng số | Giá trị | Nguồn gốc | Đã tune chưa? |
|---|---:|---|---|
| $\epsilon$ (`smoothing_epsilon`) | 0,5 | Bài Q-DDCA gốc, §V-C | **Chưa.** [`exp6.py`](../exp6.py) đã có công cụ quét, **repo chưa có báo cáo kết quả** |
| $\alpha$ (`congestion_history_weight`) | 0,5 mặc định | Tài liệu research-directions, tr. 2 | **Có** — quét 51 giá trị × 8 seed. Khuyến nghị **0,85–0,95**, nhưng **mặc định trong code vẫn là 0,5** |
| Hệ số 2 trong $C_{drop}$ | 2 | Bài gốc, Algorithm 3 | **Chưa.** Chỉ chứng minh được cần $>1$ ([mục 8](#m8)) |
| `query_ans_max_len` | 10 | Không có nguồn | **Chưa — cảm tính chưa tune.** Quyết định độ phân giải 11 mức của $q^{history}$ ([mục 3.1](#m31)) |
| Sàn 5 trong $L_{max}$ | 5 | Không có nguồn | **Chưa — cảm tính chưa tune.** Quyết định cả $p_{ce}$ lẫn ngân sách đường ([mục 10.1](#m101)) |
| `Link.metric` | 1 | Mọi cạnh như nhau | **Chưa.** Khiến "khoảng cách" = "số chặng" |
| `handle_step_time` | 0,01 s | Chi tiết mô phỏng | **Chưa** |
| `query_delta` | 0,001 s | Chống đồng bộ hoá sự kiện | **Chưa — cảm tính chưa tune** |
| `queryTime` | 0,05 s | Chi tiết mô phỏng | **Chưa.** Cố định trong khi $M$ thay đổi — xem cảnh báo ở [FULL_GRAPH_EXPERIMENT_REPORT §9](../FULL_GRAPH_EXPERIMENT_REPORT.md) |
| $M$ (`send_max_try`) | 10 | Tham số thí nghiệm | **Có** — quét $M = 1\dots10$ |
| Seed | 101, 202, 303 (+ 404…808) | Tái lập | — |

---

<a id="m15"></a>

## 15. Tóm lại: bài này đã thêm gì về mặt toán học

Bản gốc và bản mở rộng chạy **cùng một hàm chi phí**, **cùng một `argmin`**,
**cùng một hình phạt huỷ**. Khác biệt duy nhất nằm ở **một biến đầu vào**:

> **Từ "hàng xóm này *trước đây* có hay nhận hàng không?" sang "hàng xóm này
> *trước đây* có hay nhận hàng không, **và ngay lúc này kệ của nó còn trống bao
> nhiêu?**"**

Cụ thể, toàn bộ đóng góp là một **trung bình có trọng số** giữa hai tín hiệu, cộng
với bốn thứ mà tài liệu này dẫn xuất chứ code không nói:

1. Tín hiệu mới có tác dụng **chủ yếu như một quy tắc phá thế hoà liên tục** trên
   một lịch sử chỉ có 11 mức rời rạc ([mục 5.2](#m52), [mục 3.1](#m31)).
2. Một đường vòng chỉ thắng khi $f_A > \dfrac{1 + f_B(C-h-1)}{C-h}$, nên với
   $d(s,\text{dst}) = 1$ thì định tuyến lại **không thể** xảy ra
   ([mục 10.4](#m104)).
3. Ở lượt thử cuối ($R = 0$) mọi ứng viên đồng giá $C_{drop}$ và **cả $\alpha$
   lẫn $\epsilon$ đều bị vô hiệu hoá** ([mục 7.3](#m73)).
4. Chính cơ chế giải phóng ô nhớ khi chuyển tiếp đã tạo một vòng phản hồi dương
   khiến qubit quay đầu — vá bằng bất biến đường đơn ([mục 10.3](#m103)).

Không nơ-ron, không huấn luyện, không mô hình dự báo, không thêm một dependency
nào — chỉ có một trung bình có trọng số, một hàm mũ $(1-\hat q)^{M-m}$, một kỳ
vọng hai kết cục, và một `argmin`.
