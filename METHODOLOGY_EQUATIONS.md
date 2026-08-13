# Real-Time Congestion Estimation in Q-DDCA

## Purpose and scope

This document explains the equations used by the real-time congestion extension
implemented in this repository. For every equation, it answers:

1. Why the program needs the equation.
2. What the equation calculates and how the result is used.
3. How the equation was built and whether it appears in a source.

Two sources must be distinguished:

- **Original Q-DDCA paper:** Chen et al., *Q-DDCA: Decentralized Dynamic
  Congestion Avoid Routing in Large-Scale Quantum Networks*, IEEE/ACM
  Transactions on Networking, DOI
  [10.1109/TNET.2023.3285093](https://doi.org/10.1109/TNET.2023.3285093).
- **Research-directions document:** [*Advanced Research & Implementation
  Directions for Q-DDCA*](<D:/QuantumDocuments/Advanced Research & Implementation Directions for Q-DDCA.pdf>),
  especially direction 2 on pages 2-3.

The original paper provides the historical acceptance estimator and the
expected-hop routing utility. The research-directions document proposes adding
live memory utilization and blending it with historical acceptance. The current
program implements that first extension; it does not yet implement queue length,
arrival rate, waiting time, EWMA prediction, or predictive routing.

## Notation

| Symbol | Meaning | Program representation |
|---|---|---|
| $$v$$ | Candidate neighbor being evaluated | `node` or `np` |
| $$t$$ | Current routing-decision time | Current simulator time |
| $$A_v$$ | Accepted requests recorded for neighbor $$v$$ | Count of `True` values in `query_list[v]` |
| $$T_v$$ | Total recorded requests to neighbor $$v$$ | `len(query_list[v])` |
| $$\epsilon$$ | Smoothing constant | `delta = 0.5` |
| $$q_v^{\mathrm{history}}$$ | Smoothed historical acceptance estimate | `historical_stat2(v)` |
| $$M_v^{\mathrm{used}}(t)$$ | Memory slots currently occupied at $$v$$ | `v.currentSize` |
| $$M_v^{\mathrm{capacity}}$$ | Total memory slots at $$v$$ | `v.memorySize` |
| $$\rho_v(t)$$ | Current memory utilization of $$v$$ | `memory_utilization(v)` |
| $$\alpha$$ | Weight assigned to historical evidence | `congestion_history_weight` |
| $$\hat q_v(t)$$ | Real-time estimated acceptance probability | `stat2(v)` |
| $$M$$ | Maximum attempts permitted at the current hop | `qubit.max_try_count` |
| $$m$$ | Attempts already made at the current hop | `qubit.try_count` |
| $$R$$ | Remaining attempts | `M - m` |
| $$d(v,d)$$ | Remaining path metric from candidate $$v$$ to destination $$d$$ | `mt` |
| $$C_{\mathrm{drop}}$$ | Cost assigned to dropping and retransmission | `metric_drop` |
| $$Y(v)$$ | Expected routing cost for candidate $$v$$ | `y` |
| $$S_C$$ | Feasible candidate-neighbor set | Filtered entries in `rt` |
| $$v^*$$ | Selected next-hop neighbor | `nexthop` |

## Equation 1: Historical acceptance probability

$$
q_v^{\mathrm{history}}
=
\frac{A_v+\epsilon}{T_v+\epsilon}
$$

### Why the program needs this equation

Q-DDCA needs a local estimate of how likely a neighbor is to accept a resource
reservation request. A raw current-memory reading alone contains no information
about the neighbor's recent behavior. Historical outcomes preserve that evidence
and stabilize the routing decision when memory usage changes briefly.

### What it calculates and how the result is used

The equation calculates a smoothed ratio of accepted requests to total requests.
The implementation counts successful Boolean outcomes in `query_list[v]`, uses
the history length as the total, and sets the smoothing constant to 0.5.

The result becomes the historical component of the real-time estimator in
Equation 4. It is no longer passed directly to the routing utility unless
$$\alpha=1$$.

### How the equation is built and where it appears

Without smoothing, the empirical acceptance rate is accepted requests divided
by total requests. Adding the same small positive value to numerator and
denominator avoids division by zero when no request has yet been recorded and
gives an unseen neighbor an optimistic initial value.

This equation is **not newly invented by this implementation**. It appears in:

- the original Q-DDCA paper, Section V-C, "The Implementation of the Q-DDCA,"
  printed page 9 (PDF page 8), where it is written as
  $$q_i=(acc_i+\epsilon)/(tol_i+\epsilon)$$;
- the research-directions document, page 2, as the current estimator that should
  be improved.

## Equation 2: Raw memory utilization

$$
\rho_v^{\mathrm{raw}}(t)
=
\frac{M_v^{\mathrm{used}}(t)}{M_v^{\mathrm{capacity}}}
$$

### Why the program needs this equation

Historical acceptance is a lagging signal. A neighbor can have an excellent
recent acceptance history and then suddenly run out of memory. The program needs
a measurement that reacts during the current routing decision.

### What it calculates and how the result is used

The equation calculates the fraction of the neighbor's memory that is occupied:

- 0 means no memory is occupied;
- 0.8 means 80 percent is occupied;
- 1 means the memory is full.

The value is normalized, so nodes with different absolute memory capacities can
be compared on the same scale. After defensive normalization by Equation 3, it
is converted into live availability and used in Equation 4.

### How the equation is built and where it appears

Utilization is defined as used capacity divided by total capacity. This is the
standard normalized load ratio.

This equation is **not part of the original Q-DDCA routing metric**. It is
explicitly proposed in the research-directions document on page 2 under
"Advanced version: queue/memory-aware congestion."

## Equation 3: Defensive memory-utilization normalization

For a node with positive memory capacity, the program uses:

$$
\rho_v(t)
=
\max\left(0,\min\left(1,
\frac{M_v^{\mathrm{used}}(t)}{M_v^{\mathrm{capacity}}}
\right)\right)
$$

For a node with zero or invalid capacity, it uses the safe fallback:

$$
M_v^{\mathrm{capacity}}\leq 0
\quad\Longrightarrow\quad
\rho_v(t)=1
$$

### Why the program needs this equation

The blended estimator assumes that memory utilization is a valid probability-like
quantity between 0 and 1. Invalid or transient simulator state must not produce a
negative probability, a value above 1, or division by zero.

### What it calculates and how the result is used

The nested minimum and maximum clamp the raw utilization to the closed interval
from 0 to 1. A node with invalid capacity is treated as fully utilized, which is
the conservative routing choice. The normalized result is supplied to Equation 4.

### How the equation is built and where it appears

The inner minimum imposes the upper bound and the outer maximum imposes the lower
bound. The fallback handles a zero denominator.

This defensive formula is **an implementation safeguard and is not stated in
either the original paper or the research-directions document**. The source
document gives only the ideal ratio in Equation 2 and implicitly assumes valid
memory state.

## Equation 4: Real-time acceptance estimator

$$
\hat q_v(t)
=
\alpha q_v^{\mathrm{history}}
+
(1-\alpha)\left(1-\rho_v(t)\right)
$$

subject to:

$$
0\leq\alpha\leq1
$$

### Why the program needs this equation

The program needs one probability-like value that is compatible with the
existing Q-DDCA routing utility but reacts faster than historical acceptance
alone. This equation lets the extension improve congestion awareness without
replacing the rest of the routing algorithm.

### What it calculates and how the result is used

The term below is the current free-memory fraction:

$$
1-\rho_v(t)
$$

The estimator forms a weighted average of historical acceptance and current
free-memory fraction. Because the weights sum to 1 and both inputs lie between 0
and 1, the result also lies between 0 and 1:

$$
0\leq\hat q_v(t)\leq1
$$

The routing loop calls `stat2(v)` for every feasible neighbor. That method returns
this value, which replaces the original historical-only probability in Equations
7-9.

The weight has clear boundary behavior:

$$
\alpha=1
\quad\Longrightarrow\quad
\hat q_v(t)=q_v^{\mathrm{history}}
$$

$$
\alpha=0
\quad\Longrightarrow\quad
\hat q_v(t)=1-\rho_v(t)
$$

The program defaults to equal weighting:

$$
\alpha=0.5
$$

### How the equation is built and where it appears

This is a convex combination: one weight is $$\alpha$$ and the other is its
complement, so the weights add to 1. It preserves the scale of both inputs and
makes the trade-off directly configurable.

This equation is **not in the original Q-DDCA paper**. It is explicitly proposed
in the research-directions document on page 2 as:

$$
\hat q_v(t)
=
\alpha q_v^{\mathrm{history}}
+
(1-\alpha)(1-\rho_v(t))
$$

The program implements this proposed equation directly.

## Equation 5: Remaining attempts

$$
R=M-m
$$

### Why the program needs this equation

The probability of eventual success depends on how many resource-allocation
attempts remain. A candidate with a moderate acceptance probability is less risky
when many retries remain than when the current attempt is the last opportunity.

### What it calculates and how the result is used

The equation calculates the number of attempts remaining at the current hop.
The result is used as the exponent in the all-fail and at-least-one-success
probabilities in Equations 6 and 7.

### How the equation is built and where it appears

It is the maximum attempt budget minus the attempt count already consumed.

The symbol $$R$$ is introduced in this document only for readability. The
original paper does **not** name this quantity $$R$$, but its Equation (5) uses
the expression $$M-m$$ directly. The implementation also uses `M - m` directly.

## Equation 6: Probability that all remaining attempts fail

$$
P_{\mathrm{fail}}(v)
=
\left(1-\hat q_v(t)\right)^{M-m}
$$

### Why the program needs this equation

The routing cost must account for the risk that every remaining request to a
candidate fails, causing the entangled pair to be dropped and retransmitted.

### What it calculates and how the result is used

One attempt fails with probability $$1-\hat q_v(t)$$. Under the routing model's
independent-attempt assumption, multiplying this probability once for every
remaining attempt produces the probability that all of them fail.

The result weights the drop penalty in Equation 9.

### How the equation is built and where it appears

For $$M-m$$ independent attempts with the same estimated acceptance probability,
the joint probability that every attempt fails is the product:

$$
\underbrace{(1-\hat q_v(t))\cdots(1-\hat q_v(t))}_{M-m\text{ factors}}
=
(1-\hat q_v(t))^{M-m}
$$

The original paper's Equation (5), Section V-B, contains the same failure term
using the historical probability $$q_i$$. The implemented extension substitutes
the real-time estimate $$\hat q_v(t)$$ for $$q_i$$. This substitution is the
program's integration step; the exponent structure comes from the paper.

## Equation 7: Probability of at least one successful attempt

$$
P_{\mathrm{success}}(v)
=
1-\left(1-\hat q_v(t)\right)^{M-m}
$$

### Why the program needs this equation

The routing utility needs to balance two mutually exclusive outcomes: at least
one attempt succeeds, or all attempts fail. This equation provides the weight for
the successful-routing outcome.

### What it calculates and how the result is used

It calculates the complement of the all-fail probability:

$$
P_{\mathrm{success}}(v)
=
1-P_{\mathrm{fail}}(v)
$$

The result weights the remaining path metric in Equation 9.

### How the equation is built and where it appears

"At least one success" is the complement of "every attempt fails," so its
probability is one minus Equation 6.

The original paper's Equation (5) explicitly contains
$$1-(1-q_i)^{M-m}$$. The implementation retains that construction and replaces
the historical-only $$q_i$$ with the real-time estimate $$\hat q_v(t)$$.

## Equation 8: Drop and retransmission penalty

$$
C_{\mathrm{drop}}
=
2\,d(s,d)
$$

### Why the program needs this equation

If every attempt fails, dropping the entangled pair is more expensive than
making ordinary progress toward the destination. Without a larger penalty, the
router could prefer dropping too readily.

### What it calculates and how the result is used

The equation assigns dropping a virtual route length equal to twice the shortest
distance from source $$s$$ to destination $$d$$. The value is used as the cost of
the all-fail outcome in Equation 9 and as the rejection threshold after candidate
evaluation.

In code, it is calculated from the route table as `metric_drop`.

### How the equation is built and where it appears

The factor 2 is a deliberate penalty representing the cost of abandoning the
current pair and starting distribution again.

This formula comes from the original paper, Section V-C, printed page 9 (PDF page
8). The paper describes the drop node as a virtual neighbor and Algorithm 3 sets
$$L_{drop}=2\,dist(u_k^s,u_k^d)$$. It is not introduced by the real-time
congestion extension.

## Equation 9: Expected routing cost for one candidate

$$
Y(v)
=
\left[1-\left(1-\hat q_v(t)\right)^{M-m}\right]d(v,d)
+
\left(1-\hat q_v(t)\right)^{M-m}C_{\mathrm{drop}}
$$

Equivalently:

$$
Y(v)
=
P_{\mathrm{success}}(v)d(v,d)
+
P_{\mathrm{fail}}(v)C_{\mathrm{drop}}
$$

### Why the program needs this equation

The router must compare a short but congested neighbor with a longer but
available neighbor using one common score. Hop count alone ignores congestion,
while acceptance probability alone ignores route length. This expected cost
combines both.

### What it calculates and how the result is used

The first term is the path cost weighted by the probability of obtaining at
least one successful reservation. The second term is the drop cost weighted by
the probability that all remaining reservations fail.

The routing loop calculates `y` for each feasible neighbor. A high real-time
acceptance estimate lowers the failure-weighted drop penalty; low availability
raises it. The resulting values are compared by Equation 10.

### How the equation is built and where it appears

This is a two-outcome expected value:

$$
\operatorname{ExpectedCost}
=
P(\mathrm{success})\,Cost(\mathrm{success})
+
P(\mathrm{failure})\,Cost(\mathrm{failure})
$$

The routing structure comes from the original paper's Equation (5), Section V-B,
printed page 8 (PDF page 7), which uses acceptance probability, remaining
attempts, and distance to construct the expected-hop utility. The paper's Section
V-C and Algorithm 3 define the virtual drop cost.

The exact formula above is the **implemented extension** of that paper equation:
it replaces the paper's historical $$q_i$$ with $$\hat q_v(t)$$ and expresses the
failure outcome using the program's explicit drop penalty
$$C_{\mathrm{drop}}=2d(s,d)$$.

## Equation 10: Next-hop selection

$$
v^*
=
\underset{v\in S_C}{\operatorname{arg\,min}}\;Y(v)
$$

### Why the program needs this equation

Calculating a score does not itself make a routing decision. The program needs a
selection rule that converts all candidate costs into one next hop.

### What it calculates and how the result is used

The arg-min operator returns the candidate neighbor whose expected routing cost
is smallest. The selected node becomes `nexthop`, and its associated link becomes
`nextlink`. The program then asks that neighbor to reserve memory and attempts to
use the link.

If the best candidate is worse than the drop penalty, or if it would create a
route loop, the implementation returns no next hop and the current pair is
dropped or retried according to the surrounding control flow.

### How the equation is built and where it appears

The candidate set first removes routes that violate the hop and fidelity-related
bounds. Minimization then chooses the lowest expected cost among the remaining
options.

This rule is present in the original paper:

- Equation (6) formulates the constrained minimization with Boolean selection
  variables;
- Algorithm 3, line 9, says to find the candidate in $$S_C$$ that minimizes
  Equation (5).

The real-time extension does not change this selection rule. It changes the
acceptance estimate used inside the candidate cost.

## End-to-end calculation sequence

For every feasible neighbor, the program evaluates the equations in this order:

$$
(A_v,T_v)
\longrightarrow
q_v^{\mathrm{history}}
$$

$$
(M_v^{\mathrm{used}},M_v^{\mathrm{capacity}})
\longrightarrow
\rho_v(t)
$$

$$
(q_v^{\mathrm{history}},\rho_v(t),\alpha)
\longrightarrow
\hat q_v(t)
$$

$$
(\hat q_v(t),M,m)
\longrightarrow
P_{\mathrm{success}}(v),P_{\mathrm{fail}}(v)
$$

$$
(P_{\mathrm{success}},P_{\mathrm{fail}},d,C_{\mathrm{drop}})
\longrightarrow
Y(v)
$$

$$
\{Y(v):v\in S_C\}
\longrightarrow
v^*
$$

This preserves Q-DDCA's expected-hop decision process while replacing a lagging
historical-only input with a combined historical and real-time congestion input.

## Worked example

Assume a neighbor has 9 accepted requests in a 10-result history, uses 8 of 10
memory slots, the smoothing constant is 0.5, and the history weight is 0.5.

$$
q_v^{\mathrm{history}}
=
\frac{9+0.5}{10+0.5}
=
0.9048
$$

$$
\rho_v(t)
=
\frac{8}{10}
=
0.8
$$

$$
\hat q_v(t)
=
0.5(0.9048)+0.5(1-0.8)
=
0.5524
$$

If two attempts remain, the all-fail and success probabilities are:

$$
P_{\mathrm{fail}}(v)
=
(1-0.5524)^2
\approx
0.2003
$$

$$
P_{\mathrm{success}}(v)
=
1-0.2003
\approx
0.7997
$$

If the remaining route is 3 hops and the drop penalty is 8 cost units:

$$
Y(v)
=
0.7997(3)+0.2003(8)
\approx
4.0015
$$

The router compares this value with the corresponding cost for every other
feasible neighbor and selects the smallest one.

## Source-to-implementation summary

| Equation | Original Q-DDCA paper | Research-directions document | Current program |
|---|---|---|---|
| Historical acceptance | Yes, Section V-C | Repeated on page 2 | Implemented |
| Memory utilization | No | Yes, page 2 | Implemented with clamping |
| Blended real-time estimator | No | Yes, page 2 | Implemented directly |
| Remaining-attempt failure term | Yes, Equation (5) | Not the focus | Reused with real-time estimate |
| At-least-one-success term | Yes, Equation (5) | Not the focus | Reused with real-time estimate |
| Drop penalty | Yes, Section V-C and Algorithm 3 | Not the focus | Reused |
| Expected routing cost | Yes, Equation (5) | Discussed conceptually | Extended with real-time estimate |
| Arg-min next-hop choice | Yes, Equation (6) and Algorithm 3 | General selection discussed | Reused |

## Implementation locations

- `entity.py`, `historical_stat2`: Equation 1.
- `entity.py`, `memory_utilization`: Equations 2-3.
- `entity.py`, `congestion_state` and `stat2`: Equation 4.
- `entity.py`, `route`: Equations 5-10.
- `topo.py`, `Network.__init__` and `Network.build`: validation and propagation
  of $$\alpha$$.
- `test_congestion.py`: numerical, boundary, propagation, sudden-saturation,
  and route-selection tests.
