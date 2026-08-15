#QDDCA #RTC

[[RTC Notations & Main Equations]]
## Why Historical Acceptance Alone Is Not Enough

The original Q-DDCA estimator is based on historical request outcomes:

$$
q_v^{history}
=
\frac{A_v+\epsilon}{T_v+\epsilon}
$$

where:

- $A_v$: number of requests accepted by neighbor $v$
- $T_v$: total number of recorded requests to neighbor $v$
- $\epsilon$: smoothing constant, currently $0.5$

For example, suppose:

$$
A_v=9,\qquad T_v=10,\qquad \epsilon=0.5
$$

Then:

$$
q_v^{history}
=
\frac{9+0.5}{10+0.5}
=
\frac{9.5}{10.5}
\approx0.9048
$$

The sender therefore considers the neighbor historically reliable, with an estimated acceptance rate of approximately **90.48%**.

However, this value describes **past behavior**. It does not directly describe the neighbor's current resource state.

---

## 1. The Staleness Problem

Suppose neighbor $v$ has 10 memory slots.

Initially, only 2 slots are occupied:

$$
M_v^{used}=2,
\qquad
M_v^{capacity}=10
$$

Therefore, memory utilization is:

$$
\rho_v
=
\frac{2}{10}
=
0.2
$$

The neighbor is only 20% occupied.

Assume its historical estimate is:

$$
q_v^{history}\approx0.9048
$$

Now suppose other traffic suddenly fills all of the neighbor's memory:

$$
M_v^{used}:2\rightarrow10
$$

Therefore:

$$
\rho_v:0.2\rightarrow1.0
$$

The physical state of the node changed immediately.

However, the historical counters are still:

$$
A_v=9,
\qquad
T_v=10
$$

so:

$$
q_v^{history}\approx0.9048
$$

has not changed.

Thus:

$$
\boxed{
\text{Current congestion changed, but the historical estimate did not.}
}
$$

This is the fundamental weakness of using only historical acceptance information.

---

## 2. Why the Historical Estimate Does Not React Immediately

The historical estimator only depends on:

$$
(A_v,T_v)
$$

It does **not** contain information about:

$$
M_v^{used}(t)
$$

or:

$$
M_v^{capacity}
$$

or directly:

$$
\rho_v(t)
$$

Therefore, a change in memory occupancy cannot directly modify:

$$
q_v^{history}
$$

The sender must first send another request and observe whether the neighbor accepts or rejects it.

The process is approximately:

```text
Neighbor becomes congested
        ↓
Sender does not immediately know
        ↓
Sender sends another request
        ↓
Neighbor rejects request
        ↓
Historical counters are updated
        ↓
Historical estimate decreases
```

This makes historical acceptance a **lagging congestion indicator**.

---

## 3. Historical Inertia

The problem becomes more noticeable when a large amount of historical data has already accumulated.

Suppose:

$$
A_v=90,
\qquad
T_v=100
$$

Then:

$$
q_v^{history}
=
\frac{90.5}{100.5}
\approx0.9005
$$

Now suppose the node suddenly becomes fully congested and begins rejecting every new request.

After one failure:

$$
q_v^{history}
=
\frac{90.5}{101.5}
\approx0.892
$$

After five consecutive failures:

$$
q_v^{history}
=
\frac{90.5}{105.5}
\approx0.858
$$

After ten consecutive failures:

$$
q_v^{history}
=
\frac{90.5}{110.5}
\approx0.819
$$

Even after **10 consecutive failures**, the estimator still reports approximately:

$$
81.9\%
$$

This happens because the previous 100 observations dominate the new observations.

Therefore:

$$
\boxed{
\text{More historical data}
\Rightarrow
\text{greater stability}
}
$$

but also:

$$
\boxed{
\text{More historical data}
\Rightarrow
\text{slower reaction to sudden changes}
}
$$

This is a form of **historical inertia**.

---

# 4. Measuring Current Congestion

To address this limitation, the modified estimator measures the neighbor's memory utilization at routing time:

$$
\rho_v(t)
=
\frac{M_v^{used}(t)}
{M_v^{capacity}}
$$

where:

- $M_v^{used}(t)$: currently occupied memory
- $M_v^{capacity}$: total memory capacity
- $\rho_v(t)$: current memory utilization

For example:

$$
\rho_v=0
$$

means the memory is completely empty.

$$
\rho_v=0.5
$$

means the memory is 50% occupied.

$$
\rho_v=0.8
$$

means the memory is 80% occupied.

$$
\rho_v=1
$$

means the memory is completely full.

---

# 5. Converting Utilization into an Availability Signal

The implementation defines:

$$
q_v^{memory}(t)
=
1-\rho_v(t)
$$

This converts utilization into a normalized memory-availability signal.

| Memory utilization $\rho_v$ | Availability $1-\rho_v$ |
|---:|---:|
| 0.00 | 1.00 |
| 0.20 | 0.80 |
| 0.50 | 0.50 |
| 0.80 | 0.20 |
| 0.95 | 0.05 |
| 1.00 | 0.00 |

Thus:

$$
\rho_v\uparrow
\quad\Rightarrow\quad
q_v^{memory}\downarrow
$$

Higher memory utilization means lower resource availability.

---

# 6. Important Interpretation of $1-\rho$

The quantity:

$$
1-\rho_v
$$

should not necessarily be interpreted as the **true probability that the neighbor accepts a request**.

For example:

$$
\rho_v=0.8
$$

gives:

$$
1-\rho_v=0.2
$$

This does not prove that the neighbor literally has exactly a 20% acceptance probability.

Instead, it is better interpreted as:

> A normalized instantaneous resource-availability signal derived from current memory utilization.

This distinction is important when describing the method academically.

---

# 7. Combining Historical and Current Information

The new congestion estimator combines the historical acceptance estimate with the real-time memory signal:

$$
\boxed{
\hat q_v(t)
=
\alpha q_v^{history}
+
(1-\alpha)(1-\rho_v(t))
}
$$

where:

$$
0\leq\alpha\leq1
$$

The two weights sum to one:

$$
\alpha+(1-\alpha)=1
$$

Therefore, the equation is a **convex combination**, or weighted average.

The two components represent different types of information:

$$
\underbrace{q_v^{history}}_{\text{past empirical experience}}
$$

and:

$$
\underbrace{1-\rho_v(t)}_{\text{current resource availability}}
$$

The combined estimate is:

$$
\underbrace{\hat q_v(t)}_{\text{congestion-aware routing estimate}}
$$

---

# 8. Meaning of $\alpha$

The parameter:

$$
\alpha
$$

controls the balance between historical stability and real-time responsiveness.

### When $\alpha=1$

$$
\hat q_v=q_v^{history}
$$

Memory utilization has no effect.

This reproduces the historical-only behavior.

### When $\alpha=0$

$$
\hat q_v=1-\rho_v
$$

Only current memory utilization matters.

Historical performance is ignored.

### When $\alpha=0.5$

$$
\hat q_v
=
0.5q_v^{history}
+
0.5(1-\rho_v)
$$

Historical information and current memory state receive equal weight.

---

# 9. Stability vs. Responsiveness

Suppose:

$$
q_v^{history}=0.9
$$

and the neighbor suddenly becomes highly congested:

$$
\rho_v=0.9
$$

Therefore:

$$
1-\rho_v=0.1
$$

Now consider different values of $\alpha$.

## High Historical Weight

For:

$$
\alpha=0.9
$$

we obtain:

$$
\hat q_v
=
0.9(0.9)+0.1(0.1)
$$

$$
\hat q_v
=
0.81+0.01
=
0.82
$$

The estimator remains relatively high.

Therefore:

$$
\boxed{
\alpha\uparrow
\Rightarrow
\text{greater stability}
}
$$

but:

$$
\boxed{
\alpha\uparrow
\Rightarrow
\text{slower congestion response}
}
$$

## Equal Weighting

For:

$$
\alpha=0.5
$$

we obtain:

$$
\hat q_v
=
0.5(0.9)+0.5(0.1)
$$

$$
\hat q_v
=
0.45+0.05
=
0.50
$$

The router reacts much more strongly to the congestion.

## High Real-Time Weight

For:

$$
\alpha=0.1
$$

we obtain:

$$
\hat q_v
=
0.1(0.9)+0.9(0.1)
$$

$$
\hat q_v
=
0.09+0.09
=
0.18
$$

The current memory state dominates.

Therefore:

$$
\boxed{
\alpha\downarrow
\Rightarrow
\text{greater responsiveness}
}
$$

However, very small values of $\alpha$ can also make routing more sensitive to temporary fluctuations.

---

# 10. Why Not Use Only Memory Utilization?

If current memory is available, one might ask why historical information is needed at all.

Consider two neighbors $A$ and $B$.

Suppose:

$$
\rho_A=\rho_B=0.3
$$

Then:

$$
1-\rho_A
=
1-\rho_B
=
0.7
$$

A memory-only estimator considers the nodes equally attractive.

However, suppose their historical performance is:

$$
q_A^{history}=0.95
$$

and:

$$
q_B^{history}=0.55
$$

This indicates that $A$ has historically performed much better.

There may be factors not represented by memory utilization alone, such as:

- link conditions,
- contention,
- timing,
- protocol interactions,
- resource-generation success,
- other node behavior.

Using:

$$
\alpha=0.5
$$

for node $A$:

$$
\hat q_A
=
0.5(0.95)+0.5(0.7)
=
0.825
$$

For node $B$:

$$
\hat q_B
=
0.5(0.55)+0.5(0.7)
=
0.625
$$

Therefore:

$$
\hat q_A>\hat q_B
$$

even though their current memory utilization is identical.

Historical observations therefore provide information that memory utilization alone may not capture.

---

# 11. Effect on Routing

The combined estimate is used as:

$$
p=\hat q_v(t)
$$

in the existing Q-DDCA routing-cost calculation.

Let:

- $M$: maximum allowed attempts
- $m$: attempts already used
- $R=M-m$: remaining attempts
- $h_v$: remaining path cost through neighbor $v$
- $C_{drop}$: penalty associated with failure/drop

The probability that all remaining attempts fail is:

$$
P_{fail}(v)
=
(1-p)^R
$$

The probability that at least one attempt succeeds is:

$$
P_{success}(v)
=
1-(1-p)^R
$$

The expected routing cost is:

$$
Y(v)
=
P_{success}(v)h_v
+
P_{fail}(v)C_{drop}
$$

Substituting the probability expressions:

$$
Y(v)
=
\left[1-(1-p)^R\right]h_v
+
(1-p)^R C_{drop}
$$

The router selects the feasible neighbor with the smallest:

$$
Y(v)
$$

Therefore, reducing $p$ because of current congestion increases the influence of the failure penalty.

---

# 12. Example of Congestion-Aware Route Switching

Consider two possible routes:

```text
        A
       / \
      S   D
       \ /
        B
```

Suppose $A$ provides the shorter path:

$$
h_A=2
$$

while $B$ provides:

$$
h_B=4
$$

Historically:

$$
q_A^{history}=0.90
$$

and:

$$
q_B^{history}=0.85
$$

Based only on historical performance and path length, $A$ looks attractive.

Now suppose:

$$
\rho_A=1.0
$$

while:

$$
\rho_B=0.2
$$

Then:

$$
1-\rho_A=0
$$

and:

$$
1-\rho_B=0.8
$$

Using:

$$
\alpha=0.5
$$

gives:

$$
\hat q_A
=
0.5(0.90)+0.5(0)
=
0.45
$$

while:

$$
\hat q_B
=
0.5(0.85)+0.5(0.8)
=
0.825
$$

Therefore:

$$
\boxed{\hat q_A=0.45}
$$

and:

$$
\boxed{\hat q_B=0.825}
$$

The congestion-aware estimator now strongly favors $B$'s reliability, even though $B$ has the longer path.

The routing-cost equation determines whether this reliability improvement is large enough to justify the additional path cost.

---

# 13. Historical Signal vs. Real-Time Signal

### Historical Acceptance

$$
q_v^{history}
$$

answers:

> How successful has this neighbor been based on previous observations?

It provides:

- stability,
- empirical experience,
- smoothing,
- information about behavior beyond memory occupancy.

However, it can become stale.

### Memory Utilization

$$
\rho_v(t)
$$

answers:

> How occupied is this neighbor right now?

It provides:

- immediate congestion information,
- fast response to sudden saturation,
- direct resource-state information.

However, it may fluctuate quickly and does not capture every cause of failure.

### Combined Estimator

$$
\hat q_v(t)
=
\alpha q_v^{history}
+
(1-\alpha)(1-\rho_v(t))
$$

attempts to obtain:

$$
\boxed{
\text{stability}
+
\text{responsiveness}
}
$$

---

# 14. Reactive vs. Predictive Congestion Estimation

The current implementation is **real-time reactive congestion estimation**.

It answers:

> What does the neighbor's congestion state look like right now?

It does not yet answer:

> What will the neighbor's congestion state look like in the near future?

The current state is primarily:

$$
[q_v,\rho_v]
$$

A richer congestion model could use:

$$
s_v(t)
=
[q_v,\rho_v,Q_v,\lambda_v,\bar W_v]
$$

where:

- $q_v$: historical acceptance behavior
- $\rho_v$: current memory utilization
- $Q_v$: queue length
- $\lambda_v$: traffic/request arrival rate
- $\bar W_v$: estimated average waiting time

These variables describe different aspects of congestion.

For example:

$$
\rho_v
$$

tells us:

> How full is the node?

while:

$$
Q_v
$$

tells us:

> How much work is waiting?

and:

$$
\lambda_v
$$

tells us:

> How quickly is new load arriving?

while:

$$
\bar W_v
$$

tells us:

> How much delay is the current congestion producing?

Together, these signals could support a more advanced congestion model.

---

# 15. Overall Interpretation

The original estimator can be summarized as:

$$
\boxed{
\text{Past outcomes}
\rightarrow
\text{estimated future acceptance}
}
$$

The new estimator changes this to:

$$
\boxed{
\text{Past outcomes}
+
\text{current resource state}
\rightarrow
\text{congestion-aware acceptance estimate}
}
$$

More specifically:

$$
\boxed{
q_v^{history}
=
\text{empirical historical experience}
}
$$

$$
\boxed{
1-\rho_v(t)
=
\text{instantaneous normalized memory availability}
}
$$

and:

$$
\boxed{
\hat q_v(t)
=
\text{fusion of historical and current information}
}
$$

This modification moves Q-DDCA from relying on a single delayed signal toward a **multi-signal, real-time congestion-aware routing methodology**.

The next research step would be to expand this idea from:

$$
[q_v,\rho_v]
$$

toward:

$$
[q_v,\rho_v,Q_v,\lambda_v,\bar W_v]
$$

and eventually investigate whether these measurements can be used not only to react to current congestion, but also to **predict future congestion before saturation occurs**.