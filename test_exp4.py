import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from exp4 import (
    ATTEMPT_SWEEP_OUTPUT,
    CSV_FIELDS,
    DEFAULT_SEEDS,
    RAW_CSV_FIELDS,
    WINDOW_SWEEP_OUTPUT,
    aggregate_measurements,
    build_cases,
    build_parser,
    coefficient_of_variation,
    configure_sweep,
    raw_output_path,
    run_case,
    write_csv,
)


class MeasurementExportTests(unittest.TestCase):
    def setUp(self):
        self.args = SimpleNamespace(
            windows=(10,),
            seeds=(1, 2),
            send_max_try=5,
            requests=2,
            duration=10.0,
            accuracy=1000,
            nodes=20,
            edge_probability=0.1,
            memory_size=10,
            query_time=0.05,
            link_rate=1000.0,
            link_delay=0.001,
            link_buffer=1,
        )
        self.measurements = [
            self.sample("historical_only", 1, 10.0, 20.0, 200, 10, 2, 0.2),
            self.sample("historical_only", 2, 12.0, 24.0, 240, 8, 2, 0.4),
            self.sample("real_time_memory_aware", 1, 12.0, 24.0, 240, 5, 2, 0.1),
            self.sample("real_time_memory_aware", 2, 14.0, 28.0, 280, 4, 2, 0.3),
        ]

    @staticmethod
    def sample(algorithm, seed, throughput, edr, completed, dropped, in_flight, edr_cv):
        return {
            "window_size": 10,
            "algorithm": algorithm,
            "seed": seed,
            "mean_request_throughput_pairs_s": throughput,
            "total_edr_pairs_s": edr,
            "completed_pairs": completed,
            "dropped_pairs": dropped,
            "in_flight_pairs": in_flight,
            "edr_cv": edr_cv,
        }

    def test_build_cases_matches_the_shared_nested_sweep_pattern(self):
        self.args.windows = (10, 20)
        self.args.attempts = (1, 5)

        self.assertEqual(
            tuple(build_cases(self.args)),
            (
                (10, 1, 1),
                (10, 1, 2),
                (10, 5, 1),
                (10, 5, 2),
                (20, 1, 1),
                (20, 1, 2),
                (20, 5, 1),
                (20, 5, 2),
            ),
        )

    @patch("exp4.run_simulation")
    def test_run_case_executes_a_paired_identical_scenario(self, run_simulation):
        run_simulation.side_effect = [
            {"topology_signature": "abc", "request_pairs": "n1->n2"},
            {"topology_signature": "abc", "request_pairs": "n1->n2"},
        ]

        results = run_case(self.args, 10, 5, 1)

        self.assertEqual(len(results), 2)
        self.assertEqual(run_simulation.call_count, 2)

    def test_coefficient_of_variation(self):
        self.assertEqual(coefficient_of_variation([10, 10, 10]), 0.0)
        self.assertAlmostEqual(coefficient_of_variation([10, 0]), 1.0)
        self.assertEqual(coefficient_of_variation([0, 0]), 0.0)

    def test_default_uses_fixed_seeds_and_window_output(self):
        args = configure_sweep(build_parser().parse_args([]))
        self.assertEqual(args.output, WINDOW_SWEEP_OUTPUT)
        self.assertEqual(args.seeds, DEFAULT_SEEDS)
        self.assertEqual(args.seeds, (101, 202, 303))
        self.assertEqual(
            raw_output_path(args),
            Path("output/exp4/exp4_window_sweep_raw.csv"),
        )

    def test_explicit_raw_output_is_preserved(self):
        args = build_parser().parse_args(["--raw-output", "output/custom.csv"])
        self.assertEqual(raw_output_path(args), Path("output/custom.csv"))

    def test_attempt_sweep_preset(self):
        args = configure_sweep(build_parser().parse_args(["--sweep", "attempts"]))
        self.assertEqual(args.windows, (30,))
        self.assertEqual(args.attempts, tuple(range(1, 11)))
        self.assertEqual(args.seeds, DEFAULT_SEEDS)
        self.assertEqual(args.output, ATTEMPT_SWEEP_OUTPUT)
        self.assertEqual(
            raw_output_path(args),
            Path("output/exp4/exp4_attempt_sweep_raw.csv"),
        )

    def test_window_size_sweep_preset(self):
        args = configure_sweep(build_parser().parse_args(["--sweep", "window-size"]))
        self.assertEqual(args.windows, tuple(range(1, 31)))
        self.assertIsNone(args.attempts)
        self.assertEqual(args.send_max_try, 10)
        self.assertEqual(args.output, WINDOW_SWEEP_OUTPUT)

    def test_sweep_preset_preserves_explicit_output(self):
        args = configure_sweep(build_parser().parse_args([
            "--sweep", "attempts", "--output", "output/custom.csv",
        ]))
        self.assertEqual(args.output, "output/custom.csv")

    def test_aggregate_calculates_improvement_against_baseline(self):
        baseline, improved = aggregate_measurements(self.measurements, self.args)

        self.assertEqual(baseline["mean_request_throughput_pairs_s"], 11.0)
        self.assertEqual(baseline["total_edr_pairs_s"], 22.0)
        self.assertAlmostEqual(improved["mean_request_throughput_pairs_s"], 13.0)
        self.assertAlmostEqual(improved["total_edr_pairs_s"], 26.0)
        self.assertAlmostEqual(improved["throughput_change_pct_vs_historical"], 100 * 2 / 11)
        self.assertAlmostEqual(improved["edr_change_pct_vs_historical"], 100 * 4 / 22)
        self.assertAlmostEqual(baseline["mean_dropped_pairs"], 9.0)
        self.assertAlmostEqual(baseline["dropped_std_pairs"], 1.0)
        self.assertAlmostEqual(improved["mean_dropped_pairs"], 4.5)
        self.assertAlmostEqual(improved["dropped_std_pairs"], 0.5)
        self.assertAlmostEqual(baseline["mean_edr_cv"], 0.3)
        self.assertAlmostEqual(improved["mean_edr_cv"], 0.2)

    def test_csv_has_stable_graph_ready_schema(self):
        rows = aggregate_measurements(self.measurements, self.args)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "measurements.csv"
            write_csv(rows, output)
            with output.open(newline="", encoding="utf-8") as stream:
                exported = list(csv.DictReader(stream))

        self.assertEqual(tuple(exported[0]), CSV_FIELDS)
        self.assertEqual(len(exported), 2)
        self.assertEqual(exported[1]["algorithm"], "real_time_memory_aware")
        self.assertEqual(exported[1]["total_edr_pairs_s"], "26.000000")
        self.assertEqual(exported[1]["dropped_std_pairs"], "0.500000")
        self.assertIn("mean_edr_cv", exported[1])

    def test_raw_csv_preserves_each_seed_measurement(self):
        raw_rows = []
        for measurement in self.measurements:
            row = {field: "" for field in RAW_CSV_FIELDS}
            row.update(measurement)
            raw_rows.append(row)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "raw.csv"
            write_csv(raw_rows, output, RAW_CSV_FIELDS)
            with output.open(newline="", encoding="utf-8") as stream:
                exported = list(csv.DictReader(stream))

        self.assertEqual(tuple(exported[0]), RAW_CSV_FIELDS)
        self.assertEqual(len(exported), 4)
        self.assertEqual({row["seed"] for row in exported}, {"1", "2"})

    def test_aggregate_rejects_missing_seed(self):
        with self.assertRaisesRegex(ValueError, "cannot aggregate incomplete"):
            aggregate_measurements(self.measurements[:-1], self.args)


if __name__ == "__main__":
    unittest.main()
