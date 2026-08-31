"""Compare historical-only and real-time congestion-aware Q-DDCA.

The experiment uses paired random seeds: each algorithm receives the same
topology, request pairs, and network parameters. Results are aggregated into a
single graph-ready CSV containing mean per-request throughput and total EDR.
"""

import argparse
import csv
import hashlib
import random
import statistics
from pathlib import Path


ALGORITHMS = (
    ("historical_only", 1.0),
    ("real_time_memory_aware", 0.5),
)

# Use the same three deterministic scenarios for every sweep so the historical
# and real-time algorithms remain directly comparable and reproducible.
DEFAULT_SEEDS = tuple(range(101,116))
WINDOW_SWEEP_OUTPUT = "output/exp4/exp4_window_sweep.csv"
ATTEMPT_SWEEP_OUTPUT = "output/exp4/exp4_attempt_sweep.csv"

CSV_FIELDS = (
    "window_size",
    "send_max_try",
    "request_count",
    "simulation_duration_s",
    "simulator_accuracy",
    "node_count",
    "edge_probability",
    "memory_size",
    "query_time_s",
    "link_rate_pairs_s",
    "link_delay_s",
    "link_buffer",
    "repetitions",
    "seeds",
    "algorithm",
    "congestion_history_weight",
    "mean_request_throughput_pairs_s",
    "throughput_std_pairs_s",
    "total_edr_pairs_s",
    "edr_std_pairs_s",
    "mean_completed_pairs",
    "mean_dropped_pairs",
    "dropped_std_pairs",
    "mean_drop_ratio",
    "drop_ratio_std",
    "mean_in_flight_pairs",
    "mean_edr_cv",
    "edr_cv_std",
    "throughput_change_pct_vs_historical",
    "edr_change_pct_vs_historical",
)

RAW_CSV_FIELDS = (
    "seed",
    "window_size",
    "send_max_try",
    "request_count",
    "simulation_duration_s",
    "simulator_accuracy",
    "node_count",
    "edge_probability",
    "memory_size",
    "query_time_s",
    "link_rate_pairs_s",
    "link_delay_s",
    "link_buffer",
    "algorithm",
    "congestion_history_weight",
    "smoothing_epsilon",
    "mean_request_throughput_pairs_s",
    "total_edr_pairs_s",
    "completed_pairs",
    "dropped_pairs",
    "drop_ratio",
    "in_flight_pairs",
    "request_edrs_pairs_s",
    "edr_cv",
    "topology_signature",
    "request_pairs",
    "mean_signal_gap",
    "mean_abs_signal_gap",
)


def topology_signature(network):
    """Return a stable identifier for a generated topology and request set."""
    edges = sorted({link.name for links in network.links.values() for _, link in links})
    requests = sorted(f"{source.name}->{destination.name}" for source, destination in zip(network.s, network.d))
    payload = "|".join(edges + requests).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def coefficient_of_variation(values):
    """Return population standard deviation divided by the arithmetic mean.

    The all-zero case has no positive EDR mean. It is reported as zero because
    every request has the same EDR, while total EDR separately records that no
    useful distribution occurred.
    """
    if not values:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0:
        return 0.0
    return statistics.pstdev(values) / mean


def signal_gap_snapshot(network):
    """Sample q_history - (1 - rho) for every neighbor a sender has observed.

    That difference is exactly the partial derivative of the Section 7 estimator
    with respect to alpha, so it measures how much alpha can influence routing.
    Sampled once at the end of the run, not averaged over time.
    """
    from entity import QNNode

    gaps = []
    for sender in network.s:
        for neighbor, history in sender.query_list.items():
            if not history:
                continue
            availability = 1.0 - QNNode.memory_utilization(neighbor)
            gaps.append(sender.historical_stat2(neighbor) - availability)
    return gaps


def collect_metrics(network, args):
    """Collect the per-request delivery metrics shared by every case."""
    completed_by_request = [len(source.sendedList) for source in network.s]
    completed = sum(completed_by_request)
    per_request_throughput = [count / args.duration for count in completed_by_request]
    signal_gaps = signal_gap_snapshot(network)

    dropped = sum(len(source.dropList) for source in network.s)
    return {
        "mean_request_throughput_pairs_s": statistics.fmean(per_request_throughput),
        "total_edr_pairs_s": completed / args.duration,
        "completed_pairs": completed,
        "dropped_pairs": dropped,
        "drop_ratio": dropped / (completed + dropped) if completed + dropped else 0.0,
        "in_flight_pairs": sum(len(source.sendingList) for source in network.s),
        "request_edrs_pairs_s": ";".join(
            f"{throughput:.6f}" for throughput in per_request_throughput
        ),
        "edr_cv": coefficient_of_variation(per_request_throughput),
        "mean_signal_gap": statistics.fmean(signal_gaps) if signal_gaps else 0.0,
        "mean_abs_signal_gap": (
            statistics.fmean(abs(gap) for gap in signal_gaps)
            if signal_gaps
            else 0.0
        ),
    }


def run_simulation(args, seed, window_size, send_max_try, algorithm, history_weight,
                   epsilon=0.5):
    """Run one simulation replicate and return its raw measurements."""
    from qns.simulator.simulator import Simulator

    import qubit
    from topo import Network

    random.seed(seed)
    qubit.count = 0
    simulator = Simulator(0, args.duration, args.accuracy)
    network = Network(
        n=args.nodes,
        p=args.edge_probability,
        reqs=args.requests,
        memorySize=args.memory_size,
        windowSize=window_size,
        queryTime=args.query_time,
        send_max_try=send_max_try,
        allow_reroute=True,
        rate=args.link_rate,
        delay=args.link_delay,
        buffer=args.link_buffer,
        congestion_history_weight=history_weight,
        smoothing_epsilon=epsilon,
    )
    network.install(simulator)
    signature = topology_signature(network)
    request_pairs = ";".join(
        f"{source.name}->{destination.name}"
        for source, destination in zip(network.s, network.d)
    )
    simulator.run()

    result = {
        "seed": seed,
        "window_size": window_size,
        "send_max_try": send_max_try,
        "request_count": args.requests,
        "simulation_duration_s": args.duration,
        "simulator_accuracy": args.accuracy,
        "node_count": args.nodes,
        "edge_probability": args.edge_probability,
        "memory_size": args.memory_size,
        "query_time_s": args.query_time,
        "link_rate_pairs_s": args.link_rate,
        "link_delay_s": args.link_delay,
        "link_buffer": args.link_buffer,
        "algorithm": algorithm,
        "congestion_history_weight": history_weight,
        "smoothing_epsilon": epsilon,
        "topology_signature": signature,
        "request_pairs": request_pairs,
    }
    result.update(collect_metrics(network, args))
    return result


def build_cases(args):
    """Yield every reproducible ``(window, attempts, seed)`` case."""
    attempt_values = getattr(args, "attempts", None) or (args.send_max_try,)
    for window_size in args.windows:
        for send_max_try in attempt_values:
            for seed in args.seeds:
                yield window_size, send_max_try, seed


def run_case(args, window_size, send_max_try, seed):
    """Run both algorithms on one identical seeded network scenario."""
    results = [
        run_simulation(
            args,
            seed,
            window_size,
            send_max_try,
            algorithm,
            history_weight,
        )
        for algorithm, history_weight in ALGORITHMS
    ]
    if len({result["topology_signature"] for result in results}) != 1:
        raise RuntimeError("paired algorithms did not receive identical topologies")
    if len({result["request_pairs"] for result in results}) != 1:
        raise RuntimeError("paired algorithms did not receive identical request pairs")
    return results


def percent_change(value, baseline):
    """Return percentage change, or an empty value for a zero baseline."""
    if baseline == 0:
        return ""
    return (value - baseline) / baseline * 100.0


def _index_measurements(measurements, default_send_max_try):
    """Index measurements by experiment case and algorithm."""
    grouped = {}
    for item in measurements:
        key = (
            item["window_size"],
            item.get("send_max_try", default_send_max_try),
            item["algorithm"],
        )
        grouped.setdefault(key, []).append(item)
    return grouped


def _validate_samples(
    samples,
    expected_seeds,
    expected_sample_count,
    window_size,
    send_max_try,
    algorithm,
):
    """Ensure a case has exactly one sample for every expected seed."""
    observed_seeds = {item["seed"] for item in samples}
    if observed_seeds != expected_seeds or len(samples) != expected_sample_count:
        raise ValueError(
            "cannot aggregate incomplete or duplicate seed data for "
            f"window_size={window_size}, send_max_try={send_max_try}, "
            f"algorithm={algorithm}: expected {sorted(expected_seeds)}, "
            f"observed {sorted(observed_seeds)}"
        )


def _summarize_samples(samples):
    """Calculate the graph metrics for one algorithm's replicates."""
    throughputs = [item["mean_request_throughput_pairs_s"] for item in samples]
    edrs = [item["total_edr_pairs_s"] for item in samples]
    dropped = [item["dropped_pairs"] for item in samples]
    drop_ratios = [
        item.get(
            "drop_ratio",
            item["dropped_pairs"] / (item["completed_pairs"] + item["dropped_pairs"])
            if item["completed_pairs"] + item["dropped_pairs"]
            else 0.0,
        )
        for item in samples
    ]
    edr_cvs = [item["edr_cv"] for item in samples]
    return {
        "mean_request_throughput_pairs_s": statistics.fmean(throughputs),
        "throughput_std_pairs_s": statistics.pstdev(throughputs),
        "total_edr_pairs_s": statistics.fmean(edrs),
        "edr_std_pairs_s": statistics.pstdev(edrs),
        "mean_completed_pairs": statistics.fmean(
            item["completed_pairs"] for item in samples
        ),
        "mean_dropped_pairs": statistics.fmean(dropped),
        "dropped_std_pairs": statistics.pstdev(dropped),
        "mean_drop_ratio": statistics.fmean(drop_ratios),
        "drop_ratio_std": statistics.pstdev(drop_ratios),
        "mean_in_flight_pairs": statistics.fmean(
            item["in_flight_pairs"] for item in samples
        ),
        "mean_edr_cv": statistics.fmean(edr_cvs),
        "edr_cv_std": statistics.pstdev(edr_cvs),
    }


def _experiment_fields(args, window_size, send_max_try):
    """Return fields shared by every algorithm in an experiment case."""
    return {
        "window_size": window_size,
        "send_max_try": send_max_try,
        "request_count": args.requests,
        "simulation_duration_s": args.duration,
        "simulator_accuracy": args.accuracy,
        "node_count": args.nodes,
        "edge_probability": args.edge_probability,
        "memory_size": args.memory_size,
        "query_time_s": args.query_time,
        "link_rate_pairs_s": args.link_rate,
        "link_delay_s": args.link_delay,
        "link_buffer": args.link_buffer,
        "repetitions": len(args.seeds),
        "seeds": ";".join(str(seed) for seed in args.seeds),
    }


def aggregate_measurements(measurements, args):
    """Aggregate paired replicates into graph-ready rows."""
    rows = []
    attempt_values = getattr(args, "attempts", None) or (args.send_max_try,)
    measurement_index = _index_measurements(measurements, args.send_max_try)
    expected_seeds = set(args.seeds)

    for window_size in args.windows:
        for send_max_try in attempt_values:
            grouped = {
                algorithm: measurement_index.get(
                    (window_size, send_max_try, algorithm), []
                )
                for algorithm, _ in ALGORITHMS
            }
            for algorithm, samples in grouped.items():
                _validate_samples(
                    samples,
                    expected_seeds,
                    len(args.seeds),
                    window_size,
                    send_max_try,
                    algorithm,
                )

            summaries = {
                algorithm: _summarize_samples(samples)
                for algorithm, samples in grouped.items()
            }
            baseline = summaries["historical_only"]
            common_fields = _experiment_fields(args, window_size, send_max_try)

            for algorithm, history_weight in ALGORITHMS:
                summary = summaries[algorithm]
                rows.append({
                    **common_fields,
                    "algorithm": algorithm,
                    "congestion_history_weight": history_weight,
                    **summary,
                    "throughput_change_pct_vs_historical": percent_change(
                        summary["mean_request_throughput_pairs_s"],
                        baseline["mean_request_throughput_pairs_s"],
                    ),
                    "edr_change_pct_vs_historical": percent_change(
                        summary["total_edr_pairs_s"],
                        baseline["total_edr_pairs_s"],
                    ),
                })
    return rows


def write_csv(rows, output_path, fields=CSV_FIELDS):
    """Write experiment rows to a stable CSV schema."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            write_result(writer, row)


def write_result(writer, row):
    """Write one result using the stable numeric formatting of the CSV files."""
    writer.writerow({
        key: f"{value:.6f}" if isinstance(value, float) else value
        for key, value in row.items()
    })


def raw_output_path(args):
    """Return the explicit raw path or derive one beside the mean CSV."""
    if args.raw_output:
        return Path(args.raw_output)
    output_path = Path(args.output)
    return output_path.with_name(f"{output_path.stem}_raw{output_path.suffix}")


def configure_sweep(args):
    """Apply a targeted sweep preset without creating a large Cartesian grid."""
    if args.sweep == "window-size":
        args.windows = tuple(range(1, 31))
        args.attempts = None
        args.send_max_try = 10
        if args.output is None:
            args.output = WINDOW_SWEEP_OUTPUT
    elif args.sweep == "attempts":
        args.windows = (30,)
        args.attempts = tuple(range(1, 11))
        args.send_max_try = 10
        if args.output is None:
            args.output = ATTEMPT_SWEEP_OUTPUT
    return args


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="override the selected sweep output path")
    parser.add_argument(
        "--raw-output",
        help="per-seed CSV path (default: <output stem>_raw.csv)",
    )
    parser.add_argument(
        "--sweep",
        choices=("window-size", "attempts"),
        default="window-size",
        help=(
            "window-size writes w=1..30 at M=10; attempts writes M=1..10 "
            "at w=30"
        ),
    )
    parser.set_defaults(
        seeds=DEFAULT_SEEDS,
        windows=(),
        attempts=None,
        send_max_try=10,
    )
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--accuracy", type=int, default=1000)
    parser.add_argument("--nodes", type=int, default=100)
    parser.add_argument("--edge-probability", type=float, default=0.1)
    parser.add_argument("--requests", type=int, default=10)
    parser.add_argument("--memory-size", type=int, default=10)
    parser.add_argument("--query-time", type=float, default=0.05)
    parser.add_argument("--link-rate", type=float, default=1000.0)
    parser.add_argument("--link-delay", type=float, default=0.001)
    parser.add_argument("--link-buffer", type=int, default=1)
    return parser


def main():
    args = configure_sweep(build_parser().parse_args())
    cases = tuple(build_cases(args))
    raw_path = raw_output_path(args)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    measurements = []
    with raw_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=RAW_CSV_FIELDS)
        writer.writeheader()
        for case_number, (window_size, send_max_try, seed) in enumerate(cases, 1):
            results = run_case(args, window_size, send_max_try, seed)
            measurements.extend(results)
            for result in results:
                write_result(writer, result)
            stream.flush()
            print(
                f"[{case_number}/{len(cases)}] checkpointed "
                f"w={window_size}, M={send_max_try}, seed={seed}",
                flush=True,
            )

    rows = aggregate_measurements(measurements, args)
    write_csv(rows, args.output)
    print(f"Wrote {len(measurements)} per-seed rows to {raw_path}")
    print(
        f"Wrote {len(rows)} graph-ready mean rows averaged over "
        f"{len(args.seeds)} seeds to {args.output}"
    )


if __name__ == "__main__":
    main()
