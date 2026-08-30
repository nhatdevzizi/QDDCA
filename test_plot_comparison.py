import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import plot_exp4
from plot_exp4 import (
    DEFAULT_INPUTS,
    build_parser,
    has_x_variation,
    parse_formats,
    read_result_files,
    read_results,
    select_rows,
)


class PlotComparisonTests(unittest.TestCase):
    def write_csv(self, path, include_cv=True, include_dropped_std=True):
        fields = [
            "window_size",
            "send_max_try",
            "algorithm",
            "total_edr_pairs_s",
            "edr_std_pairs_s",
            "mean_dropped_pairs",
            "mean_drop_ratio",
        ]
        if include_dropped_std:
            fields.append("dropped_std_pairs")
        if include_cv:
            fields.extend(("mean_edr_cv", "edr_cv_std"))
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for algorithm in ("historical_only", "real_time_memory_aware"):
                row = {
                    "window_size": 10,
                    "send_max_try": 5,
                    "algorithm": algorithm,
                    "total_edr_pairs_s": 12.5,
                    "edr_std_pairs_s": 0.5,
                    "mean_dropped_pairs": 3,
                    "mean_drop_ratio": 0.1,
                }
                if include_dropped_std:
                    row["dropped_std_pairs"] = 0.25
                if include_cv:
                    row.update({"mean_edr_cv": 0.2, "edr_cv_std": 0.01})
                writer.writerow(row)

    def write_window_sweep_csv(self, path):
        fields = [
            "window_size",
            "send_max_try",
            "algorithm",
            "total_edr_pairs_s",
            "edr_std_pairs_s",
            "mean_dropped_pairs",
            "dropped_std_pairs",
            "mean_drop_ratio",
            "drop_ratio_std",
            "mean_edr_cv",
            "edr_cv_std",
        ]
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for window_size in (5, 10):
                for algorithm in ("historical_only", "real_time_memory_aware"):
                    writer.writerow({
                        "window_size": window_size,
                        "send_max_try": 10,
                        "algorithm": algorithm,
                        "total_edr_pairs_s": 100 + window_size,
                        "edr_std_pairs_s": 2.0,
                        "mean_dropped_pairs": window_size * 3,
                        "dropped_std_pairs": 0.5,
                        "mean_drop_ratio": window_size / 100,
                        "drop_ratio_std": 0.01,
                        "mean_edr_cv": 0.2,
                        "edr_cv_std": 0.01,
                    })

    def test_read_and_select_complete_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            self.write_csv(path)
            rows = read_results(path)

        selected = select_rows(rows, window_size=10, send_max_try=5)
        self.assertEqual(len(selected), 2)
        self.assertIsInstance(selected[0]["total_edr_pairs_s"], float)
        self.assertFalse(has_x_variation(selected, "window_size"))

    def test_parse_publication_formats(self):
        self.assertEqual(parse_formats("pdf, png,svg"), ("pdf", "png", "svg"))

    def test_legacy_attempt_results_without_cv_remain_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.csv"
            self.write_csv(path, include_cv=False)
            rows = read_results(path)

        self.assertEqual(len(rows), 2)
        self.assertNotIn("mean_edr_cv", rows[0])

    def test_legacy_results_without_dropped_std_remain_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.csv"
            self.write_csv(path, include_dropped_std=False)
            rows = read_results(path)

        self.assertEqual(len(rows), 2)
        self.assertNotIn("dropped_std_pairs", rows[0])

    def test_default_inputs_cover_both_targeted_sweeps(self):
        self.assertEqual(build_parser().parse_args([]).input, DEFAULT_INPUTS)

    def test_multiple_csvs_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.csv"
            second = Path(directory) / "second.csv"
            self.write_csv(first)
            self.write_csv(second)
            rows = read_result_files((first, second))

        self.assertEqual(len(rows), 2)

    def test_duplicate_merge_keeps_cv_schema_regardless_of_input_order(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            rich = directory / "window.csv"
            legacy = directory / "attempt.csv"
            self.write_csv(rich, include_cv=True)
            self.write_csv(legacy, include_cv=False)

            rows = read_result_files((rich, legacy))

        self.assertEqual(len(rows), 2)
        self.assertTrue(all("mean_edr_cv" in row for row in rows))

    def test_main_draws_aggregate_drops_vs_send_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            input_path = directory / "window.csv"
            output_dir = directory / "plots"
            self.write_window_sweep_csv(input_path)
            argv = [
                "plot_exp4.py",
                "--input", str(input_path),
                "--output-dir", str(output_dir),
                "--format", "png",
            ]

            with patch.object(sys, "argv", argv):
                plot_exp4.main()

            graph = output_dir / "05_dropped_vs_send_rate.png"
            self.assertTrue(graph.is_file())
            self.assertGreater(graph.stat().st_size, 0)

    def test_select_rejects_missing_slice(self):
        with self.assertRaisesRegex(ValueError, "no complete two-version data"):
            select_rows([], window_size=30)


if __name__ == "__main__":
    unittest.main()
