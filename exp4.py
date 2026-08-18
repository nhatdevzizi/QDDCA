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

# Fifty deterministic seeds make the default experiment reproducible while
# still sampling fifty independently generated topology/request scenarios.
DEFAULT_SEEDS = tuple(range(1, 51))
DEFAULT_OUTPUT = "output/exp4/exp4.csv"
SEND_RATE_SWEEP_OUTPUT = "output/exp4/exp4_window_sweep.csv"
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
    "in_flight_pairs",
    "request_edrs_pairs_s",
    "edr_cv",
    "topology_signature",
    "request_pairs",
    "mean_signal_gap",
    "mean_abs_signal_gap",
)


def parse_int_list(value):
    """Parse a comma-separated list of integers for CLI sweep arguments."""
    values = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not values:
        raise argparse.ArgumentTypeError("expected at least one integer")
    return values


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

    completed_by_request = [len(source.sendedList) for source in network.s]
    completed = sum(completed_by_request)
    dropped = sum(len(source.dropList) for source in network.s)
    in_flight = sum(len(source.sendingList) for source in network.s)
    per_request_throughput = [count / args.duration for count in completed_by_request]
    signal_gaps = signal_gap_snapshot(network)

    return {
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
        "mean_request_throughput_pairs_s": statistics.fmean(per_request_throughput),
        "total_edr_pairs_s": completed / args.duration,
        "completed_pairs": completed,
        "dropped_pairs": dropped,
        "in_flight_pairs": in_flight,
        "request_edrs_pairs_s": ";".join(
            f"{throughput:.6f}" for throughput in per_request_throughput
        ),
        "edr_cv": coefficient_of_variation(per_request_throughput),
        "topology_signature": signature,
        "request_pairs": request_pairs,
        "mean_signal_gap": statistics.fmean(signal_gaps) if signal_gaps else 0.0,
        "mean_abs_signal_gap": statistics.fmean(abs(gap) for gap in signal_gaps) if signal_gaps else 0.0,
    }


def percent_change(value, baseline):
    """Return percentage change, or an empty value for a zero baseline."""
    if baseline == 0:
        return ""
    return (value - baseline) / baseline * 100.0


def aggregate_measurements(measurements, args):
    """Aggregate paired replicates into graph-ready rows."""
    rows = []
    attempt_values = getattr(args, "attempts", None) or (args.send_max_try,)
    for window_size in args.windows:
        for send_max_try in attempt_values:
            grouped = {
                algorithm: [
                    item
                    for item in measurements
                    if item["window_size"] == window_size
                    and item.get("send_max_try", args.send_max_try) == send_max_try
                    and item["algorithm"] == algorithm
                ]
                for algorithm, _ in ALGORITHMS
            }
            expected_seeds = set(args.seeds)
            for algorithm, samples in grouped.items():
                observed_seeds = {item["seed"] for item in samples}
                if observed_seeds != expected_seeds or len(samples) != len(args.seeds):
                    raise ValueError(
                        "cannot aggregate incomplete or duplicate seed data for "
                        f"window_size={window_size}, send_max_try={send_max_try}, "
                        f"algorithm={algorithm}: expected {sorted(expected_seeds)}, "
                        f"observed {sorted(observed_seeds)}"
                    )
            baseline = grouped["historical_only"]
            baseline_throughput = statistics.fmean(
                item["mean_request_throughput_pairs_s"] for item in baseline
            )
            baseline_edr = statistics.fmean(item["total_edr_pairs_s"] for item in baseline)

            for algorithm, history_weight in ALGORITHMS:
                samples = grouped[algorithm]
                throughputs = [item["mean_request_throughput_pairs_s"] for item in samples]
                edrs = [item["total_edr_pairs_s"] for item in samples]
                edr_cvs = [item["edr_cv"] for item in samples]
                mean_throughput = statistics.fmean(throughputs)
                mean_edr = statistics.fmean(edrs)
                rows.append({
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
                    "algorithm": algorithm,
                    "congestion_history_weight": history_weight,
                    "mean_request_throughput_pairs_s": mean_throughput,
                    "throughput_std_pairs_s": statistics.pstdev(throughputs),
                    "total_edr_pairs_s": mean_edr,
                    "edr_std_pairs_s": statistics.pstdev(edrs),
                    "mean_completed_pairs": statistics.fmean(
                        item["completed_pairs"] for item in samples
                    ),
                    "mean_dropped_pairs": statistics.fmean(
                        item["dropped_pairs"] for item in samples
                    ),
                    "mean_in_flight_pairs": statistics.fmean(
                        item["in_flight_pairs"] for item in samples
                    ),
                    "mean_edr_cv": statistics.fmean(edr_cvs),
                    "edr_cv_std": statistics.pstdev(edr_cvs),
                    "throughput_change_pct_vs_historical": percent_change(
                        mean_throughput, baseline_throughput
                    ),
                    "edr_change_pct_vs_historical": percent_change(
                        mean_edr, baseline_edr
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
    if args.sweep == "send-rate":
        args.windows = tuple(range(1, 31))
        args.attempts = None
        args.send_max_try = 10
        if args.output == DEFAULT_OUTPUT:
            args.output = SEND_RATE_SWEEP_OUTPUT
    elif args.sweep == "attempts":
        args.windows = (30,)
        args.attempts = tuple(range(1, 11))
        if args.output == DEFAULT_OUTPUT:
            args.output = ATTEMPT_SWEEP_OUTPUT
    return args


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--raw-output",
        help="per-seed CSV path (default: <output stem>_raw.csv)",
    )
    parser.add_argument("--windows", type=parse_int_list, default=(5, 10, 15, 20, 25, 30))
    parser.add_argument(
        "--sweep",
        choices=("custom", "send-rate", "attempts"),
        default="custom",
        help=(
            "targeted sweep preset: send-rate uses w=1..30 at M=10; "
            "attempts uses M=1..10 at w=30"
        ),
    )
    parser.add_argument(
        "--seeds",
        type=parse_int_list,
        default=DEFAULT_SEEDS,
        help="comma-separated seeds (default: 1 through 50)",
    )
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--accuracy", type=int, default=1000)
    parser.add_argument("--nodes", type=int, default=50)
    parser.add_argument("--edge-probability", type=float, default=0.1)
    parser.add_argument("--requests", type=int, default=5)
    parser.add_argument("--memory-size", type=int, default=10)
    parser.add_argument("--send-max-try", type=int, default=10)
    parser.add_argument(
        "--attempts",
        type=parse_int_list,
        help="comma-separated maximum-attempt sweep; defaults to --send-max-try",
    )
    parser.add_argument("--query-time", type=float, default=0.05)
    parser.add_argument("--link-rate", type=float, default=1000.0)
    parser.add_argument("--link-delay", type=float, default=0.001)
    parser.add_argument("--link-buffer", type=int, default=1)
    return parser


def main():
    args = configure_sweep(build_parser().parse_args())
    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("--seeds must not contain duplicates")
    attempt_values = args.attempts or (args.send_max_try,)
    raw_path = raw_output_path(args)
    write_csv([], raw_path, RAW_CSV_FIELDS)
    total_pairs = len(args.windows) * len(attempt_values) * len(args.seeds)
    completed_pairs = 0
    measurements = []
    for window_size in args.windows:
        for send_max_try in attempt_values:
            for seed in args.seeds:
                paired_signatures = set()
                paired_requests = set()
                for algorithm, history_weight in ALGORITHMS:
                    result = run_simulation(
                        args,
                        seed,
                        window_size,
                        send_max_try,
                        algorithm,
                        history_weight,
                    )
                    measurements.append(result)
                    paired_signatures.add(result["topology_signature"])
                    paired_requests.add(result["request_pairs"])
                if len(paired_signatures) != 1 or len(paired_requests) != 1:
                    raise RuntimeError("paired algorithms did not receive identical scenarios")
                completed_pairs += 1
                write_csv(measurements, raw_path, RAW_CSV_FIELDS)
                print(
                    f"[{completed_pairs}/{total_pairs}] checkpointed "
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
