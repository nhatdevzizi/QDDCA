"""Run a small paired Q-DDCA grid around the monotonicity breakpoint.

This analysis intentionally reuses exp4.py's simulation and aggregation
functions so its measurements are directly comparable with the published
window-size and retry sweeps.
"""

import argparse
import csv
from pathlib import Path
import sys

OUTPUT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = OUTPUT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

import exp4


RAW_OUTPUT = OUTPUT_DIR / "joint_grid_raw.csv"
AGGREGATE_OUTPUT = OUTPUT_DIR / "joint_grid.csv"


def arguments():
    return argparse.Namespace(
        duration=10.0,
        accuracy=1000,
        nodes=50,
        edge_probability=0.1,
        requests=5,
        memory_size=10,
        query_time=0.05,
        link_rate=1000.0,
        link_delay=0.001,
        link_buffer=1,
        seeds=(101, 202, 303),
        windows=(1, 2, 3),
        attempts=(1, 2, 3),
        send_max_try=3,
    )


def main():
    args = arguments()
    cases = tuple(exp4.build_cases(args))
    measurements = []

    with RAW_OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=exp4.RAW_CSV_FIELDS)
        writer.writeheader()
        for index, (window_size, send_max_try, seed) in enumerate(cases, 1):
            results = exp4.run_case(args, window_size, send_max_try, seed)
            measurements.extend(results)
            for result in results:
                exp4.write_result(writer, result)
            stream.flush()
            print(
                f"[{index}/{len(cases)}] w={window_size}, "
                f"M={send_max_try}, seed={seed}",
                flush=True,
            )

    rows = exp4.aggregate_measurements(measurements, args)
    exp4.write_csv(rows, AGGREGATE_OUTPUT)
    print(f"Wrote {RAW_OUTPUT}")
    print(f"Wrote {AGGREGATE_OUTPUT}")


if __name__ == "__main__":
    main()
