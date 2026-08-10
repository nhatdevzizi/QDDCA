"""Predictive congestion helpers.

Pure stdlib on purpose: test_predict.py imports this without qns or numpy.
"""
import math

# Routing arms compared by exp1/exp2/exp3: (label, allow_reroute, predictive)
MODES = [
    ("shortest", False, False),
    ("reactive", True, False),
    ("predictive", True, True),
]


def sec(t):
    """Seconds as a float from a SimQN Time (or a raw number)."""
    return t.sec if hasattr(t, "sec") else float(t)


def decay(rate, dt, tau):
    """Exponentially decay a rate estimate over dt seconds."""
    return rate * math.exp(-max(dt, 0.0) / tau)


def p_success(q, cap, lam, mu, delta):
    """P_success(v, t+delta): extrapolate occupancy from the net arrival rate.

    q=Q_v(t) occupancy, cap=M_v capacity, lam/mu = arrival/departure rates (1/s).
    """
    if cap <= 0:
        return 0.0
    q_hat = max(q + (lam - mu) * delta, 0.0)
    return min(max(1.0 - q_hat / cap, 0.0), 1.0)


def utility(p, hops, mode="ratio", hop_penalty=0.1):
    """U(v) = P/E[hops] (ratio) or P - lambda*E[hops] (linear)."""
    hops = max(hops, 1)
    return p / hops if mode == "ratio" else p - hop_penalty * hops
