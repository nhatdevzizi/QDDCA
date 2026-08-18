import csv
import tempfile
import unittest
from pathlib import Path

from plot_comparison import (
    build_parser,
    has_x_variation,
    parse_formats,
    read_result_files,
    read_results,
    select_rows,
)


class PlotComparisonTests(unittest.TestCase):
    def write_csv(self, path, include_cv=True):
        fields = [
            "window_size",
            "send_max_try",
            "algorithm",
            "total_edr_pairs_s",
            "edr_std_pairs_s",
            "mean_dropped_pairs",
        ]
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
                }
                if include_cv:
                    row.update({"mean_edr_cv": 0.2, "edr_cv_std": 0.01})
                writer.writerow(row)

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

    def test_default_input_is_aggregate_output(self):
        self.assertEqual(
            build_parser().parse_args([]).input,
            ("output/exp4/exp4.csv",),
        )

    def test_multiple_csvs_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.csv"
            second = Path(directory) / "second.csv"
            self.write_csv(first)
            self.write_csv(second)
            rows = read_result_files((first, second))

        self.assertEqual(len(rows), 2)

    def test_select_rejects_missing_slice(self):
        with self.assertRaisesRegex(ValueError, "no complete two-version data"):
            select_rows([], window_size=30)


if __name__ == "__main__":
    unittest.main()
