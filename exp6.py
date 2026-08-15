"""Sweep the smoothing constant epsilon of the historical acceptance estimate.

    q_v^history = (A_v + epsilon) / (T_v + epsilon)

Epsilon is added to numerator and denominator alike, so it pulls the estimate
towards 1.0 rather than towards 0.5 -- it is an optimism knob, not a shrinkage
towards a neutral prior. An untried neighbour already scores 1.0 for any
epsilon > 0, so what epsilon really controls is how harshly a neighbour with
recorded failures is punished: at epsilon = 0.5 a 0/10 neighbour scores 0.048,
at epsilon = 1.0 it scores 0.091.

Alpha is held at 1.0 by default so epsilon acts undiluted: it only reaches the
routing decision through q_history, which the estimator weights by alpha, and at
alpha = 0 epsilon has no effect whatsoever.
"""

import argparse

from exp4 import build_parser, run_simulation
from exp5 import (SweepSpec, aggregate_sweep, csv_fields, parse_float_list,
                  print_table, write_sweep)


EPSILON = SweepSpec(
    measurement_key="smoothing_epsilon",
    column="epsilon",
    baseline=0.5,  # the value the estimator has always used
    delta_col="delta_edr_vs_prev_epsilon",
    slope_col="slope_edr_per_epsilon",
    pct_col="edr_change_pct_vs_epsilon05",
)

EXTRA_COLUMNS = ("congestion_history_weight",)


def demo():
    """Self-check for the epsilon aggregation; runs without SimQN."""
    args = argparse.Namespace(
        windows=(20,), seeds=(1,), send_max_try=10, requests=5,
        duration=10.0, nodes=50, edge_probability=0.1, memory_size=10,
    )
    values = (0.0, 0.5, 1.0)
    measurements = [
        {"smoothing_epsilon": eps, "mean_request_throughput_pairs_s": edr / 5,
         "total_edr_pairs_s": edr, "completed_pairs": edr * 10, "dropped_pairs": 0.0,
         "in_flight_pairs": 0.0, "mean_signal_gap": 0.1, "mean_abs_signal_gap": 0.1}
        for eps, edr in ((0.0, 10.0), (0.5, 8.0), (1.0, 12.0))
    ]
    rows = aggregate_sweep(measurements, args, EPSILON, values,
                           extra={"congestion_history_weight": 1.0})

    fields = csv_fields(EPSILON, EXTRA_COLUMNS)
    assert fields[0] == "epsilon"
    assert fields[1] == "congestion_history_weight"
    assert fields[-1] == "edr_change_pct_vs_epsilon05"
    assert [row["epsilon"] for row in rows] == [0.0, 0.5, 1.0]
    assert rows[0]["delta_edr_vs_prev_epsilon"] == ""
    assert rows[1]["delta_edr_vs_prev_epsilon"] == -2.0
    assert abs(rows[1]["slope_edr_per_epsilon"] + 4.0) < 1e-9  # -2.0 over a 0.5 step
    assert rows[1]["edr_change_pct_vs_epsilon05"] == 0.0  # eps=0.5 is its own baseline
    assert abs(rows[2]["edr_change_pct_vs_epsilon05"] - 50.0) < 1e-9  # 12 vs 8
    assert rows[0]["congestion_history_weight"] == 1.0
    print("self-check OK")


def main():
    parser = build_parser()
    parser.add_argument("--epsilons", type=parse_float_list, default=None,
                        help="explicit epsilon list; overrides --epsilon-step")
    parser.add_argument("--epsilon-step", type=float, default=0.05,
                        help="epsilon grid spacing over [0, 1]")
    parser.add_argument("--history-weight", type=float, default=1.0,
                        help="alpha held fixed for the sweep; epsilon is inert at alpha=0")
    parser.add_argument("--self-check", action="store_true", help="run assertions and exit")
    parser.set_defaults(output="output/exp6/exp6_epsilon_sweep.csv", windows=(20,))
    args = parser.parse_args()

    if args.self_check:
        demo()
        return

    if not 0.0 <= args.history_weight <= 1.0:
        parser.error("--history-weight must be within [0, 1]")
    if args.history_weight == 0.0:
        parser.error("--history-weight 0 makes epsilon inert: q_history is weighted out")

    if args.epsilons is None:
        if not 0.0 < args.epsilon_step <= 1.0:
            parser.error("--epsilon-step must be within (0, 1]")
        steps = int(round(1.0 / args.epsilon_step))
        args.epsilons = tuple(round(i / steps, 4) for i in range(steps + 1))

    window_size = args.windows[0]
    measurements = []
    for seed in args.seeds:
        signatures = set()
        requests = set()
        for epsilon in args.epsilons:
            result = run_simulation(args, seed, window_size, args.send_max_try,
                                    f"eps_{epsilon:g}", args.history_weight, epsilon)
            measurements.append(result)
            signatures.add(result["topology_signature"])
            requests.add(result["request_pairs"])
            print(f"seed={seed} epsilon={epsilon:g} edr={result['total_edr_pairs_s']:.3f}")
        if len(signatures) != 1 or len(requests) != 1:
            raise RuntimeError(f"epsilons did not share one scenario for seed {seed}")

    rows = aggregate_sweep(measurements, args, EPSILON, args.epsilons,
                           extra={"congestion_history_weight": args.history_weight})
    write_sweep(rows, measurements, args.output, csv_fields(EPSILON, EXTRA_COLUMNS))
    print()
    print_table(rows, EPSILON)
    print(f"\nWrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
