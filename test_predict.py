"""Self-check for the predictive congestion math. Pure stdlib: run with `python3 test_predict.py`."""
import math
from util import decay, p_success, sec, utility


def close(a, b, eps=1e-9):
    return abs(a - b) < eps


# sec(): SimQN Time or a raw number
class FakeTime:
    sec = 2.5


assert close(sec(FakeTime()), 2.5)
assert close(sec(3), 3.0)
print("sec: ok")

# decay(): halves after tau*ln2, never grows, clamps negative dt
assert close(decay(1.0, 0.5 * math.log(2), 0.5), 0.5)
assert close(decay(1.0, 0.0, 0.5), 1.0)
assert close(decay(1.0, -5.0, 0.5), 1.0)
print("decay: ok")

# p_success(): idle empty node is free, full node is not
assert close(p_success(q=0, cap=10, lam=0, mu=0, delta=0.5), 1.0)
assert close(p_success(q=10, cap=10, lam=0, mu=0, delta=0.5), 0.0)

# The whole point: half-full but filling at 10/s saturates within the 0.5s lead time.
# The reactive check (currentSize < memorySize) still says "free" here.
assert close(p_success(q=5, cap=10, lam=10, mu=0, delta=0.5), 0.0)
assert 5 < 10  # what QNNode.query() sees at that same instant

# Draining node: 9 + (0-10)*0.5 = 4 -> 60% headroom
assert close(p_success(q=9, cap=10, lam=0, mu=10, delta=0.5), 0.6)

# Monotone in the arrival rate
rising = [p_success(q=2, cap=10, lam=l, mu=0, delta=0.5) for l in (0, 4, 8, 16)]
assert rising == sorted(rising, reverse=True), rising

# Clamped to [0, 1] on absurd inputs
assert close(p_success(q=99, cap=10, lam=99, mu=0, delta=9), 0.0)
assert close(p_success(q=0, cap=10, lam=0, mu=99, delta=9), 1.0)
assert close(p_success(q=1, cap=0, lam=0, mu=0, delta=1), 0.0)
print("p_success: ok")

# utility(): both forms prefer higher P at equal hops, and fewer hops at equal P
for mode in ("ratio", "linear"):
    assert utility(0.9, 3, mode) > utility(0.4, 3, mode), mode
    assert utility(0.6, 2, mode) > utility(0.6, 5, mode), mode
# hop_penalty=0 reduces the linear form to P itself
assert close(utility(0.7, 4, "linear", hop_penalty=0.0), 0.7)
assert close(utility(0.8, 4, "ratio"), 0.2)
# hops is floored at 1, so a zero/negative metric can't blow up the ratio
assert close(utility(0.5, 0, "ratio"), 0.5)

# A congested 2-hop neighbor loses to a clear 3-hop one under both forms
assert utility(0.1, 2, "ratio") < utility(0.9, 3, "ratio")
assert utility(0.1, 2, "linear") < utility(0.9, 3, "linear")
print("utility: ok")

# The rate estimator as QNNode uses it: decay to now, then add 1/tau per event.
# Feeding one event every dt seconds must converge to ~1/dt events/sec.
for dt in (0.01, 0.05, 0.2):
    tau, lam = 0.5, 0.0
    for _ in range(2000):
        lam = decay(lam, dt, tau) + 1.0 / tau
    # Biased high by (dt/tau)/(1-exp(-dt/tau)): ~1% at dt=0.01, ~21% at dt=0.2.
    # Overestimating load is the safe direction for a congestion signal.
    assert 0 <= (lam - 1.0 / dt) / (1.0 / dt) < 0.25, (dt, lam)
    # and it decays back toward zero once the traffic stops
    assert decay(lam, 10 * tau, tau) < 0.01 * lam
print("rate estimator: ok")


# The claim of the change, scored the way QNNode.route() scores it.
# Two 3-hop neighbors, neither has failed yet, so the reactive history is
# identical for both. One is quietly saturating; only the predictor sees it.
BLEND, CAP, LEAD = 0.7, 10, 0.05
p_hist = (0 + 0.5) / (0 + 0.5)  # stat2() with no observations -> 1.0 for both


def score(lam, q, hops=3, predictive=True):
    p = p_hist
    if predictive:
        p = BLEND * p_success(q, CAP, lam, mu=0, delta=LEAD) + (1 - BLEND) * p
    return utility(p, hops)


filling, clear = (120, 6), (0, 6)  # (arrival rate, current occupancy)
assert score(*filling) < score(*clear), "predictor must avoid the filling neighbor"
assert score(*filling, predictive=False) == score(*clear, predictive=False), \
    "reactive scoring cannot tell them apart -- that is the gap being closed"
print("predictive beats reactive pre-failure: ok")

print("all ok")
