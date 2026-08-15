"""Sweep the Section 7 blending weight alpha from 0.0 to 1.0.

Every alpha is measured on identical seeded topologies and request pairs, so the
differences come only from the estimator

    q_hat_v(t) = alpha * q_history + (1 - alpha) * (1 - rho_v(t)).

The output CSV carries finite differences per 0.1 alpha step, plus a snapshot of
q_history - (1 - rho) — the analytic derivative of the estimator with respect to
alpha, which explains why some alpha ranges move the results and others do not.
"""

import argparse
import statistics
from collections import namedtuple

from exp4 import build_parser, percent_change, run_simulation, write_csv


SweepSpec = namedtuple(
    "SweepSpec", "measurement_key column baseline delta_col slope_col pct_col")

ALPHA = SweepSpec(
    measurement_key="congestion_history_weight",
    column="alpha",
    baseline=1.0,
    delta_col="delta_edr_vs_prev_alpha",
    slope_col="slope_edr_per_alpha",
    pct_col="edr_change_pct_vs_alpha1",
)


RAW_FIELDS = (
    "seed",
    "congestion_history_weight",
    "smoothing_epsilon",
    "window_size",
    "total_edr_pairs_s",
    "mean_request_throughput_pairs_s",
    "completed_pairs",
    "dropped_pairs",
    "in_flight_pairs",
    "mean_signal_gap",
    "mean_abs_signal_gap",
    "topology_signature",
)


def parse_float_list(value):
    """Parse a comma-separated list of alphas, each within [0, 1]."""
    values = tuple(round(float(item.strip()), 4) for item in value.split(",") if item.strip())
    if not values:
        raise argparse.ArgumentTypeError("expected at least one float")
    for alpha in values:
        if not 0.0 <= alpha <= 1.0:
            raise argparse.ArgumentTypeError(f"alpha {alpha} outside [0, 1]")
    return values


def csv_fields(spec, extra_names=()):
    """Column order for a sweep CSV, keyed on the swept parameter's own names."""
    return (
        (spec.column,)
        + tuple(extra_names)
        + (
            "window_size",
            "send_max_try",
            "request_count",
            "simulation_duration_s",
            "node_count",
            "edge_probability",
            "memory_size",
            "repetitions",
            "seeds",
            "mean_request_throughput_pairs_s",
            "throughput_std_pairs_s",
            "total_edr_pairs_s",
            "edr_std_pairs_s",
            "mean_completed_pairs",
            "mean_dropped_pairs",
            "mean_in_flight_pairs",
            "mean_signal_gap",
            "mean_abs_signal_gap",
            spec.delta_col,
            spec.slope_col,
            spec.pct_col,
        )
    )


def aggregate_sweep(measurements, args, spec, values, extra=None):
    """Aggregate replicates per swept value and add per-step difference columns.

    `spec` names the measurement key to group on and the CSV columns to write,
    so alpha and epsilon sweeps share this code without sharing column names.
    """
    window_size = args.windows[0]
    rows = []
    previous_edr = None
    at_baseline = [item for item in measurements
                   if item[spec.measurement_key] == spec.baseline]
    baseline_edr = statistics.fmean(
        item["total_edr_pairs_s"] for item in at_baseline) if at_baseline else None

    for index, value in enumerate(values):
        samples = [item for item in measurements if item[spec.measurement_key] == value]
        throughputs = [item["mean_request_throughput_pairs_s"] for item in samples]
        edrs = [item["total_edr_pairs_s"] for item in samples]
        mean_edr = statistics.fmean(edrs)
        delta = "" if index == 0 else mean_edr - previous_edr
        step = 0.0 if index == 0 else value - values[index - 1]

        rows.append({
            spec.column: value,
            **(extra or {}),
            "window_size": window_size,
            "send_max_try": args.send_max_try,
            "request_count": args.requests,
            "simulation_duration_s": args.duration,
            "node_count": args.nodes,
            "edge_probability": args.edge_probability,
            "memory_size": args.memory_size,
            "repetitions": len(args.seeds),
            "seeds": ";".join(str(seed) for seed in args.seeds),
            "mean_request_throughput_pairs_s": statistics.fmean(throughputs),
            "throughput_std_pairs_s": statistics.pstdev(throughputs),
            "total_edr_pairs_s": mean_edr,
            "edr_std_pairs_s": statistics.pstdev(edrs),
            "mean_completed_pairs": statistics.fmean(item["completed_pairs"] for item in samples),
            "mean_dropped_pairs": statistics.fmean(item["dropped_pairs"] for item in samples),
            "mean_in_flight_pairs": statistics.fmean(item["in_flight_pairs"] for item in samples),
            "mean_signal_gap": statistics.fmean(item["mean_signal_gap"] for item in samples),
            "mean_abs_signal_gap": statistics.fmean(item["mean_abs_signal_gap"] for item in samples),
            spec.delta_col: delta,
            spec.slope_col: "" if delta == "" or step == 0 else delta / step,
            spec.pct_col: "" if baseline_edr is None else percent_change(mean_edr, baseline_edr),
        })
        previous_edr = mean_edr
    return rows


def write_sweep(rows, measurements, output, fields):
    """Write the aggregate CSV plus the per-seed raw CSV beside it.

    The per-seed rows are what a paired comparison needs; the aggregate alone
    cannot tell a consistent gain from one that only holds on average.
    """
    write_csv(rows, output, fields)
    raw_path = output.replace(".csv", "_raw.csv")
    write_csv([{key: row[key] for key in RAW_FIELDS} for row in measurements],
              raw_path, RAW_FIELDS)
    print(f"Wrote {len(measurements)} per-seed rows to {raw_path}")


def print_table(rows, spec):
    """Print the sweep as a readable table so the trend is visible immediately."""
    name = spec.column
    header = (f"{name:>7} {'EDR':>9} {'thr/req':>9} {'drop':>9} {'dEDR':>9} "
              f"{'dEDR/d' + name:>13} {'%vs base':>9} {'|gap|':>7}")
    print(header)
    print("-" * len(header))
    for row in rows:
        def fmt(key, width=9, digits=3):
            value = row[key]
            return f"{value:>{width}.{digits}f}" if isinstance(value, float) else f"{'-':>{width}}"
        print(
            f"{row[name]:>7.2f}"
            f"{fmt('total_edr_pairs_s')}"
            f"{fmt('mean_request_throughput_pairs_s')}"
            f"{fmt('mean_dropped_pairs', 9, 1)}"
            f"{fmt(spec.delta_col)}"
            f"{fmt(spec.slope_col, 14)}"
            f"{fmt(spec.pct_col, 10, 2)}"
            f"{fmt('mean_abs_signal_gap', 8)}"
        )


def demo():
    """Self-check for the difference columns; runs without SimQN."""
    args = argparse.Namespace(
        alphas=(0.0, 0.5, 1.0), windows=(20,), seeds=(1,), send_max_try=10, requests=5,
        duration=10.0, nodes=50, edge_probability=0.1, memory_size=10,
    )
    measurements = [
        {"congestion_history_weight": alpha, "mean_request_throughput_pairs_s": edr / 5,
         "total_edr_pairs_s": edr, "completed_pairs": edr * 10, "dropped_pairs": 0.0,
         "in_flight_pairs": 0.0, "mean_signal_gap": 0.1, "mean_abs_signal_gap": 0.1}
        for alpha, edr in ((0.0, 10.0), (0.5, 12.0), (1.0, 8.0))
    ]
    rows = aggregate_sweep(measurements, args, ALPHA, args.alphas)

    assert csv_fields(ALPHA)[0] == "alpha"
    assert csv_fields(ALPHA)[-1] == "edr_change_pct_vs_alpha1"
    assert [row["alpha"] for row in rows] == [0.0, 0.5, 1.0]
    assert rows[0]["delta_edr_vs_prev_alpha"] == ""
    assert rows[1]["delta_edr_vs_prev_alpha"] == 2.0
    assert abs(rows[1]["slope_edr_per_alpha"] - 4.0) < 1e-9  # +2.0 EDR over a 0.5 step
    assert rows[2]["delta_edr_vs_prev_alpha"] == -4.0
    assert rows[2]["edr_change_pct_vs_alpha1"] == 0.0  # alpha=1 is its own baseline
    assert abs(rows[1]["edr_change_pct_vs_alpha1"] - 50.0) < 1e-9  # 12 vs 8
    print("self-check OK")


def main():
    parser = build_parser()
    parser.add_argument("--alphas", type=parse_float_list, default=None,
                        help="explicit alpha list; overrides --alpha-step")
    parser.add_argument("--alpha-step", type=float, default=0.02,
                        help="alpha grid spacing over [0, 1]")
    parser.add_argument("--self-check", action="store_true", help="run assertions and exit")
    parser.set_defaults(output="output/exp5/exp5_alpha_sweep.csv", windows=(20,))
    args = parser.parse_args()

    if args.self_check:
        demo()
        return

    if args.alphas is None:
        if not 0.0 < args.alpha_step <= 1.0:
            parser.error("--alpha-step must be within (0, 1]")
        steps = int(round(1.0 / args.alpha_step))
        args.alphas = tuple(round(i / steps, 4) for i in range(steps + 1))

    window_size = args.windows[0]
    measurements = []
    for seed in args.seeds:
        signatures = set()
        requests = set()
        for alpha in args.alphas:
            result = run_simulation(args, seed, window_size, args.send_max_try,
                                    f"alpha_{alpha:g}", alpha)
            measurements.append(result)
            signatures.add(result["topology_signature"])
            requests.add(result["request_pairs"])
            print(f"seed={seed} alpha={alpha:g} edr={result['total_edr_pairs_s']:.3f}")
        if len(signatures) != 1 or len(requests) != 1:
            raise RuntimeError(f"alphas did not share one scenario for seed {seed}")

    rows = aggregate_sweep(measurements, args, ALPHA, args.alphas)
    write_sweep(rows, measurements, args.output, csv_fields(ALPHA))
    print()
    print_table(rows, ALPHA)
    print(f"\nWrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
