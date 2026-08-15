# Khảo sát α từ 0.0 đến 1.0 cho công thức mục 7

## 1. Thiết lập

Công thức được kiểm chứng (mục 7), cài đặt tại `entity.py:congestion_state`:

$$\hat q_v(t) = \alpha\,q_v^{history} + (1-\alpha)\bigl(1-\rho_v(t)\bigr)$$

```bash
.venv/bin/python exp5.py --seeds 101,202,303,404,505,606,707,808   # ~6 phút
.venv/bin/python plot_exp5.py                                      # 3 hình PDF/PNG
```

| Tham số | Giá trị |
|---|---|
| α | 0.00, 0.02, …, 1.00 (51 giá trị) |
| seed | 101…808 (**8 lần lặp**) → 408 lần chạy |
| windowSize / memorySize / send_max_try | 20 / 10 / 10 |
| nodes / p / requests / duration | 50 / 0.1 / 5 / 10 s |
| allow_reroute | True (α chỉ có tác dụng trong nhánh định tuyến lại) |

Mỗi seed sinh cùng một topology và cùng tập request cho cả 51 giá trị α, kiểm
tra bằng `topology_signature`. Kết quả: `output/exp5/exp5_alpha_sweep.csv` (tổng hợp)
và `output/exp5/exp5_alpha_sweep_raw.csv` (**từng seed**, cần cho so sánh ghép cặp).

> **Quan trọng — số liệu này là *sau* khi vá lỗi định tuyến quay đầu** mô tả ở
> mục 6. Mọi con số trong báo cáo trước bản vá đều không còn hiệu lực.

---

## 2. Kết quả

![Fig. 1](../output/exp5/plot/exp5_fig1_edr.png)

![Fig. 2](../output/exp5/plot/exp5_fig2_drop.png)

![Fig. 3](../output/exp5/plot/exp5_fig3_delta.png)

Cột "seed" là số seed mà α đó thắng α=1 **trên cùng seed** (so sánh ghép cặp).

| α | EDR | drop | % EDR vs α=1 | seed thắng EDR | seed thắng drop |
|---:|---:|---:|---:|:---:|:---:|
| 0.00 | 516.9 | 1281 | +1.37 % | 6/8 | 6/8 |
| 0.10 | 512.2 | 1294 | +0.45 % | 5/8 | 6/8 |
| 0.20 | 504.4 | 1313 | −1.09 % | 5/8 | 6/8 |
| 0.30 | 508.7 | 1269 | −0.24 % | 5/8 | 6/8 |
| 0.40 | 510.1 | 1248 | +0.02 % | 5/8 | 6/8 |
| 0.50 | 518.2 | 1197 | +1.62 % | 5/8 | 6/8 |
| 0.60 | 528.6 | 1122 | +3.65 % | 5/8 | 7/8 |
| 0.70 | 530.4 | 1123 | +4.01 % | 5/8 | **8/8** |
| 0.80 | 530.2 | 1098 | +3.97 % | 5/8 | **8/8** |
| 0.90 | 539.1 | 1131 | +5.71 % | 6/8 | **8/8** |
| 0.94 | 546.1 | 1189 | +7.09 % | 6/8 | **8/8** |
| 0.96 | **546.7** | 1220 | **+7.21 %** | 6/8 | 7/8 |
| 0.98 | 519.1 | 1536 | +1.80 % | 4/8 | 6/8 |
| **1.00** | **509.9** | **1813** | 0 (mốc) | 0/8 | 0/8 |

Cực trị trên toàn lưới 51 điểm: EDR cao nhất **α=0.96 (546.7)**, drop thấp nhất
**α=0.84 (1076)**. **0/51** giá trị α có drop cao hơn baseline.

---

## 3. Đọc kết quả

**Lợi ích vững nằm ở drop, không phải throughput.** Với α ∈ [0.70, 0.94], mọi
seed đều cho ít drop hơn α=1 (8/8), mức giảm 680–715 qubit (≈ −38 %). Ngược lại
lợi thế EDR chỉ 4–7 % và chỉ 5–6/8 seed dương — chưa đủ để tuyên bố chắc chắn.

**Cảnh báo về số seed.** Bản báo cáo trước chạy 3 seed và kết luận "α<1 hơn α=1
từ 9 % đến 12 % EDR". Với 8 seed con số đó **co lại còn 0–7 %**. Chênh lệch đến
từ seed 202: nó phạt α=1 rất nặng và với 3 seed thì kéo lệch cả trung bình.
Đừng công bố con số EDR nào lấy từ dưới 8 seed.

**Vùng α thấp không còn ưu thế.** Sau bản vá, α ∈ [0.0, 0.5] cho EDR ngang hoặc
kém α=1 (−1.1 % đến +1.6 %). Ưu thế của α thấp trong dữ liệu cũ phần lớn là hệ
quả của chính lỗi định tuyến quay đầu (mục 6), thứ đã bơm phồng cả drop lẫn số
qubit được nạp lại vào cửa sổ gửi.

**Đuôi α → 1 vẫn sụp.** EDR đi từ 546.7 (α=0.96) xuống 519.1 (0.98) rồi 509.9
(1.00); drop đi từ 1220 lên 1536 rồi 1813. Cơ chế không đổi:

1. `historical_stat2` chỉ nhận **11 giá trị rời rạc** (`query_ans_max_len = 10`),
   nên rất nhiều hàng xóm **hòa điểm** lịch sử.
2. Số hạng $(1-\alpha)(1-\rho_v)$ là đại lượng **liên tục**, phá thế hòa đó.
3. Tại đúng α = 1 cơ chế phá thế hòa biến mất; `route()` chọn theo thứ tự sắp
   xếp sẵn và dồn lưu lượng vào cùng một hàng xóm cho tới khi nó đầy.

Thêm nữa, hàng xóm chưa từng thử được `historical_stat2` trả về $0.5/0.5 = 1.0$
— **luôn trông hoàn hảo**. Ở α = 1 sự lạc quan này không có gì đối trọng.

---

## 4. Giải thích từng vùng α

Công thức mục 7 là **tổ hợp lồi**: $\alpha + (1-\alpha) = 1$, nên $\hat q_v$ luôn
nằm giữa hai tín hiệu và mọi α đều cho $\hat q_v \in [0,1]$.

| α | Ý nghĩa | Quan sát (8 seed) |
|---|---|---|
| **0.0** | $\hat q_v = 1-\rho_v(t)$. Bỏ hoàn toàn lịch sử. Phản ứng tức thì với tắc nghẽn nhưng mù với lỗi lặp lại không do bộ nhớ (nghẽn link, hàng xóm hỏng). | EDR 516.9 (+1.37 %), drop 1281. Không có ưu thế đáng kể. |
| **0.1–0.4** | Bộ nhớ chi phối, lịch sử chỉ hiệu chỉnh. | EDR 504–512, tức **ngang hoặc kém** α=1. Drop vẫn tốt hơn (6/8 seed). |
| **0.5** | Cân bằng chính xác. Mặc định của `Network`, cấu hình "real_time_memory_aware" của exp4. | EDR 518.2 (+1.62 %), drop 1197. An toàn nhưng không tối ưu. |
| **0.6–0.8** | Thiên lịch sử, bộ nhớ còn đủ mạnh để phạt node đang đầy. | EDR +3.7…+4.0 %, drop 1098–1123 và **thắng trên cả 8 seed**. Vùng đáng tin nhất về drop. |
| **0.9–0.96** | Bộ nhớ chỉ còn 4–10 % trọng số, chủ yếu đóng vai trò phá thế hòa. | **Vùng tốt nhất về EDR**: +5.7…+7.2 %, 6/8 seed dương, drop vẫn thắng 7–8/8. |
| **0.98** | Bộ nhớ còn 2 %. | Bắt đầu sụp: EDR 519.1, drop 1536. |
| **1.0** | $\hat q_v = q^{history}$. Tái tạo đúng Q-DDCA gốc; bộ nhớ hiện tại không ảnh hưởng gì — hàng xóm vừa đầy vẫn được chấm điểm như lúc còn rỗng cho tới khi lịch sử kịp cập nhật. | Kém nhất trên **cả hai** chỉ số và **cả 8 seed**: EDR 509.9, drop 1813. |

---

## 5. Độ phụ thuộc vào chính công thức mục 7

$$\frac{\partial \hat q_v}{\partial \alpha} = q_v^{history} - \bigl(1-\rho_v(t)\bigr)$$

**(a) Độ nhạy theo α không phụ thuộc α.** Đạo hàm là hằng số theo α — $\hat q_v$
**tuyến tính** theo α. Mọi phi tuyến trong đường cong EDR (vùng phẳng ở giữa,
dốc sụp ở đuôi) **không** đến từ công thức mục 7 mà từ tầng phía sau: hàm chi phí
$y = \bigl(1-(1-p)^{M-m}\bigr)\,mt + (1-p)^{M-m}\,metric\_drop$
tại `entity.py:313` và phép `argmin` chọn next-hop. `argmin` là hàm bậc thang:
$\hat q_v$ đổi liên tục nhưng next-hop chỉ đổi khi thứ hạng đảo.

**(b) α chỉ có tác dụng khi hai tín hiệu bất đồng.** Nếu $q^{history} = 1-\rho_v$
thì đạo hàm bằng 0 và α vô nghĩa. Cột `|gap|` đo đúng đại lượng này: **0.29–0.52**
suốt sweep, tức hai tín hiệu lệch nhau 29–52 điểm phần trăm.

**(c) α chỉ ảnh hưởng khi có định tuyến lại.** `stat2()` chỉ được gọi trong nhánh
`allow_reroute=True` của `route()`.

**Cảnh báo diễn giải:** `|gap|` chụp tại thời điểm kết thúc mô phỏng và là **biến
nội sinh** — chính α quyết định lưu lượng chảy đi đâu, từ đó quyết định $\rho_v$
lúc chụp ảnh. Dùng nó như chẩn đoán điểm vận hành, đừng hồi quy EDR theo nó.

---

## 6. Lỗi định tuyến quay đầu đã được vá

Trong lúc phân tích cái bướu drop ở vùng α thấp, đo bằng bản sao `route()` có gắn
bộ đếm (bản sao tái tạo **chính xác** số liệu gốc) phát hiện:

- Chỉ có 2 nguyên nhân drop thực sự chạy: **hết lượt thử mỗi chặng** và **lặp đường**.
- Ở α = 0.06, **60 %** số drop là lặp đường (4669/7764 trên 3 seed).
- **100 %** số drop lặp đường là quay lại **đúng node vừa đi qua ở chặng trước**.
- Ở α ≤ 0.06, **100 %** các lần đó, node bị chọn là hàng xóm **rảnh nhất**.

Nguyên nhân gốc: khi qubit chuyển từ A sang B, chính A giải phóng ô nhớ
(`entity.py:336`). Đến lượt B quyết định chặng kế, A vừa trống thêm một ô nên
thường là hàng xóm rảnh nhất — và với α nhỏ, $\hat q_v \approx 1-\rho_v$ nên A
thắng. Việc chuyển tiếp thành công tự tạo ra mồi nhử phía sau lưng qubit. Chọn
phải node đã đi qua thì qubit bị **drop ngay**, không retry.

Bản vá tại `entity.py:302`: loại node đã đi qua khỏi danh sách ứng viên **trước**
khi chấm điểm, thay vì để nó thắng rồi mới phát hiện và huỷ.

```python
if np in qubit.route:
    continue
```

Kết quả đo (3 seed, so cùng cấu hình):

| α | drop trước | drop sau | trong đó drop lặp đường |
|---:|---:|---:|---|
| 0.00 | 6337 | 3681 | 3100 → **0** |
| 0.06 | 7764 | 3930 | 4669 → **0** |
| 0.50 | 4267 | 3341 | 1359 → **0** |
| 1.00 | 6545 | 4741 | 2197 → **0** |

Test khoá hành vi: `test_routing_never_returns_to_a_node_the_qubit_has_visited`
trong `test_congestion.py` — đã kiểm chứng là nó **fail** nếu gỡ bản vá.

---

## 7. Khuyến nghị

1. **Đừng dùng α = 1.0.** Kém nhất trên cả EDR lẫn drop, trên cả 8/8 seed.
2. **Dùng α ≈ 0.85–0.95.** Vùng này cho EDR tốt nhất (+5.7…+7.2 %) và drop
   thắng 7–8/8 seed. Nếu ưu tiên tuyệt đối việc giảm drop thì α ≈ 0.7–0.84.
3. **Trình bày lợi ích theo drop, không theo EDR.** Giảm drop ≈ 38 % là kết quả
   vững trên mọi seed; lợi thế EDR nhỏ và chưa chắc chắn.

## 8. Hạn chế

- Một cấu hình tải duy nhất (windowSize = 20). Kiểm tra thêm bằng
  `exp5.py --windows 10` và `--windows 30`.
- 8 seed đủ để bác bỏ α = 1 nhưng chưa đủ để xếp hạng các α trong vùng 0.6–0.96.
- `|gap|` là ảnh chụp cuối phiên và là biến nội sinh (mục 5).
- Sau bản vá, một số ít drop chuyển sang nhánh "hết ứng viên do ngân sách độ dài
  đường" (0.2–5 % số drop). Nhánh này trước đây không bao giờ chạy; chưa khảo sát.
