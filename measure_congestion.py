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
    "throughput_change_pct_vs_historical",
    "edr_change_pct_vs_historical",
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


def run_simulation(args, seed, window_size, algorithm, history_weight):
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
        send_max_try=args.send_max_try,
        allow_reroute=True,
        rate=args.link_rate,
        delay=args.link_delay,
        buffer=args.link_buffer,
        congestion_history_weight=history_weight,
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

    return {
        "seed": seed,
        "window_size": window_size,
        "algorithm": algorithm,
        "congestion_history_weight": history_weight,
        "mean_request_throughput_pairs_s": statistics.fmean(per_request_throughput),
        "total_edr_pairs_s": completed / args.duration,
        "completed_pairs": completed,
        "dropped_pairs": dropped,
        "in_flight_pairs": in_flight,
        "topology_signature": signature,
        "request_pairs": request_pairs,
    }


def percent_change(value, baseline):
    """Return percentage change, or an empty value for a zero baseline."""
    if baseline == 0:
        return ""
    return (value - baseline) / baseline * 100.0


def aggregate_measurements(measurements, args):
    """Aggregate paired replicates into graph-ready rows."""
    rows = []
    for window_size in args.windows:
        grouped = {
            algorithm: [
                item
                for item in measurements
                if item["window_size"] == window_size and item["algorithm"] == algorithm
            ]
            for algorithm, _ in ALGORITHMS
        }
        baseline = grouped["historical_only"]
        baseline_throughput = statistics.fmean(
            item["mean_request_throughput_pairs_s"] for item in baseline
        )
        baseline_edr = statistics.fmean(item["total_edr_pairs_s"] for item in baseline)

        for algorithm, history_weight in ALGORITHMS:
            samples = grouped[algorithm]
            throughputs = [item["mean_request_throughput_pairs_s"] for item in samples]
            edrs = [item["total_edr_pairs_s"] for item in samples]
            mean_throughput = statistics.fmean(throughputs)
            mean_edr = statistics.fmean(edrs)
            rows.append({
                "window_size": window_size,
                "send_max_try": args.send_max_try,
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
                "mean_completed_pairs": statistics.fmean(item["completed_pairs"] for item in samples),
                "mean_dropped_pairs": statistics.fmean(item["dropped_pairs"] for item in samples),
                "mean_in_flight_pairs": statistics.fmean(item["in_flight_pairs"] for item in samples),
                "throughput_change_pct_vs_historical": percent_change(mean_throughput, baseline_throughput),
                "edr_change_pct_vs_historical": percent_change(mean_edr, baseline_edr),
            })
    return rows


def write_csv(rows, output_path):
    """Write aggregate experiment rows to a stable CSV schema."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: f"{value:.6f}" if isinstance(value, float) else value
                for key, value in row.items()
            })


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/real_time_congestion_measurements.csv")
    parser.add_argument("--windows", type=parse_int_list, default=(5, 10, 15, 20, 25, 30))
    parser.add_argument("--seeds", type=parse_int_list, default=(101, 202, 303))
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--accuracy", type=int, default=1000)
    parser.add_argument("--nodes", type=int, default=50)
    parser.add_argument("--edge-probability", type=float, default=0.1)
    parser.add_argument("--requests", type=int, default=5)
    parser.add_argument("--memory-size", type=int, default=10)
    parser.add_argument("--send-max-try", type=int, default=10)
    parser.add_argument("--query-time", type=float, default=0.05)
    parser.add_argument("--link-rate", type=float, default=1000.0)
    parser.add_argument("--link-delay", type=float, default=0.001)
    parser.add_argument("--link-buffer", type=int, default=1)
    return parser


def main():
    args = build_parser().parse_args()
    measurements = []
    for window_size in args.windows:
        for seed in args.seeds:
            paired_signatures = set()
            paired_requests = set()
            for algorithm, history_weight in ALGORITHMS:
                result = run_simulation(args, seed, window_size, algorithm, history_weight)
                measurements.append(result)
                paired_signatures.add(result["topology_signature"])
                paired_requests.add(result["request_pairs"])
            if len(paired_signatures) != 1 or len(paired_requests) != 1:
                raise RuntimeError("paired algorithms did not receive identical scenarios")

    rows = aggregate_measurements(measurements, args)
    write_csv(rows, args.output)
    print(f"Wrote {len(rows)} graph-ready rows to {args.output}")


if __name__ == "__main__":
    main()
