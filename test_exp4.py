import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from exp4 import (
    CSV_FIELDS,
    aggregate_measurements,
    build_parser,
    jain_fairness,
    parse_int_list,
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
            self.sample("historical_only", 1, 10.0, 20.0, 200, 10, 2),
            self.sample("historical_only", 2, 12.0, 24.0, 240, 8, 2),
            self.sample("real_time_memory_aware", 1, 12.0, 24.0, 240, 5, 2),
            self.sample("real_time_memory_aware", 2, 14.0, 28.0, 280, 4, 2),
        ]

    @staticmethod
    def sample(algorithm, seed, throughput, edr, completed, dropped, in_flight):
        return {
            "window_size": 10,
            "algorithm": algorithm,
            "seed": seed,
            "mean_request_throughput_pairs_s": throughput,
            "total_edr_pairs_s": edr,
            "completed_pairs": completed,
            "dropped_pairs": dropped,
            "in_flight_pairs": in_flight,
        }

    def test_parse_int_list(self):
        self.assertEqual(parse_int_list("5, 10,15"), (5, 10, 15))

    def test_jain_fairness(self):
        self.assertEqual(jain_fairness([10, 10, 10]), 1.0)
        self.assertAlmostEqual(jain_fairness([10, 0]), 0.5)
        self.assertEqual(jain_fairness([0, 0]), 0.0)

    def test_default_output_matches_project_experiment_template(self):
        self.assertEqual(build_parser().parse_args([]).output, "output/exp4/exp4.csv")

    def test_aggregate_calculates_improvement_against_baseline(self):
        baseline, improved = aggregate_measurements(self.measurements, self.args)

        self.assertEqual(baseline["mean_request_throughput_pairs_s"], 11.0)
        self.assertEqual(baseline["total_edr_pairs_s"], 22.0)
        self.assertAlmostEqual(improved["mean_request_throughput_pairs_s"], 13.0)
        self.assertAlmostEqual(improved["total_edr_pairs_s"], 26.0)
        self.assertAlmostEqual(improved["throughput_change_pct_vs_historical"], 100 * 2 / 11)
        self.assertAlmostEqual(improved["edr_change_pct_vs_historical"], 100 * 4 / 22)

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
        self.assertIn("mean_fairness_index", exported[1])


if __name__ == "__main__":
    unittest.main()
