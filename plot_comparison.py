"""Draw four IEEE-ready historical-versus-real-time Q-DDCA graphs.

Generate the input with an attempt sweep first, for example::

    python exp4.py --attempts 1,2,3,4,5,6,7,8,9,10
    python plot_comparison.py
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


ALGORITHM_LABELS = {
    "historical_only": "Historical Q-DDCA",
    "real_time_memory_aware": "Real-time memory-aware Q-DDCA",
}
ALGORITHM_STYLES = {
    "historical_only": {
        "color": "#4D4D4D",
        "marker": "o",
        "markerfacecolor": "white",
        "linestyle": "-",
    },
    "real_time_memory_aware": {
        "color": "#b8860b",
        "marker": "^",
        "markerfacecolor": "#b8860b",
        "linestyle": "-",
    },
}
NUMERIC_FIELDS = {
    "window_size": int,
    "send_max_try": int,
    "total_edr_pairs_s": float,
    "edr_std_pairs_s": float,
    "mean_dropped_pairs": float,
    "mean_fairness_index": float,
    "fairness_std": float,
}


def read_results(path):
    """Read and validate aggregate results produced by exp4.py."""
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        missing = set(NUMERIC_FIELDS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                "input is missing required columns: " + ", ".join(sorted(missing))
            )
        rows = []
        for csv_row in reader:
            row = dict(csv_row)
            for field, converter in NUMERIC_FIELDS.items():
                row[field] = converter(row[field])
            rows.append(row)
    if not rows:
        raise ValueError("input CSV contains no result rows")
    return rows


def read_result_files(paths):
    """Merge result CSVs, with later files replacing duplicate parameter rows."""
    merged = {}
    for path in paths:
        for row in read_results(path):
            key = (row["window_size"], row["send_max_try"], row["algorithm"])
            merged[key] = row
    return list(merged.values())


def select_rows(rows, *, window_size=None, send_max_try=None):
    """Select one plotting slice and ensure that both algorithms are present."""
    selected = [
        row
        for row in rows
        if (window_size is None or row["window_size"] == window_size)
        and (send_max_try is None or row["send_max_try"] == send_max_try)
    ]
    algorithms = {row["algorithm"] for row in selected}
    missing = set(ALGORITHM_LABELS) - algorithms
    if missing:
        filters = f"window_size={window_size}, send_max_try={send_max_try}"
        raise ValueError(
            f"no complete two-version data slice for {filters}; missing: "
            + ", ".join(sorted(missing))
        )
    return selected


def grouped_by_algorithm(rows, sort_field):
    """Group rows into deterministically sorted algorithm series."""
    grouped = defaultdict(list)
    for row in rows:
        if row["algorithm"] in ALGORITHM_LABELS:
            grouped[row["algorithm"]].append(row)
    return {
        algorithm: sorted(samples, key=lambda row: row[sort_field])
        for algorithm, samples in grouped.items()
    }


def has_x_variation(rows, x_field):
    """Return whether every algorithm has at least two distinct x values."""
    grouped = grouped_by_algorithm(rows, x_field)
    return all(
        len({row[x_field] for row in samples}) >= 2
        for samples in grouped.values()
    )


def apply_ieee_style(plt):
    """Apply the compact serif style used by the supplied IEEE manuscript."""
    plt.rcParams.update({
        "font.family": "serif",
        # Liberation Serif and Nimbus Roman are metric-compatible with Times and
        # are what Linux distributions actually ship.
        "font.serif": ["Times New Roman", "Times", "Liberation Serif",
                       "Nimbus Roman", "Nimbus Roman No9 L", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 7.0,
        "axes.titlesize": 7.2,
        "axes.labelsize": 7.0,
        "axes.linewidth": 0.55,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "xtick.major.width": 0.55,
        "ytick.major.width": 0.55,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "legend.fontsize": 5.5,
        "lines.linewidth": 0.85,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
    })


def draw_graph(
    plt,
    rows,
    x_field,
    y_field,
    xlabel,
    ylabel,
    title,
    output_base,
    formats,
    width,
    show_error_bars=False,
    yerr=None,
):
    """Draw and save one compact, paper-ready two-version graph."""
    figure, axis = plt.subplots(figsize=(width, width / 1.48))
    for algorithm, samples in grouped_by_algorithm(rows, x_field).items():
        x_values = [row[x_field] for row in samples]
        y_values = [row[y_field] for row in samples]
        errors = [row[yerr] for row in samples] if show_error_bars and yerr else None
        style = dict(ALGORITHM_STYLES[algorithm])
        axis.errorbar(
            x_values,
            y_values,
            yerr=errors,
            markersize=3.1,
            markeredgewidth=0.55,
            capsize=1.5 if errors else 0,
            elinewidth=0.55,
            label=ALGORITHM_LABELS[algorithm],
            **style,
        )
    axis.set_xlabel(xlabel, labelpad=2)
    axis.set_ylabel(ylabel, labelpad=2)
    axis.set_title(title, pad=4, fontweight="normal")
    axis.grid(False)
    axis.tick_params(direction="out", pad=1.5)
    axis.legend(frameon=False, loc="best", handlelength=2.2, borderaxespad=0.25)
    if y_field == "mean_fairness_index":
        lower = min(row[y_field] for row in rows)
        axis.set_ylim(max(0.0, lower - 0.05), 1.01)
    figure.subplots_adjust(left=0.17, right=0.985, bottom=0.19, top=0.89)
    for output_format in formats:
        output_path = output_base.with_suffix(f".{output_format}")
        save_options = {"bbox_inches": "tight", "pad_inches": 0.025}
        if output_format == "png":
            save_options["dpi"] = 600
        figure.savefig(output_path, **save_options)
        print(f"Wrote {output_path}")
    plt.close(figure)


def import_pyplot():
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise SystemExit(
            "matplotlib is required for plotting; install it with "
            "'python -m pip install matplotlib'"
        ) from error
    return plt


def parse_formats(value):
    """Parse a comma-separated list of publication output formats."""
    formats = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    supported = {"png", "pdf", "svg", "eps"}
    unsupported = set(formats) - supported
    if not formats or unsupported:
        choices = ", ".join(sorted(supported))
        raise argparse.ArgumentTypeError(f"formats must be selected from: {choices}")
    return formats


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        nargs="+",
        default=("output/exp4.csv",),
        help="one or more exp4 CSV files to merge for plotting",
    )
    parser.add_argument("--output-dir", default="output/exp4/plot")
    parser.add_argument(
        "--fixed-window",
        type=int,
        help="window size used in attempt-based graphs (default: largest in CSV)",
    )
    parser.add_argument(
        "--fixed-attempts",
        type=int,
        help="attempt count used in send-rate graphs (default: largest in CSV)",
    )
    parser.add_argument(
        "--formats",
        type=parse_formats,
        default=("pdf", "png"),
        help="comma-separated outputs (default: pdf,png)",
    )
    parser.add_argument(
        "--format",
        choices=("png", "pdf", "svg", "eps"),
        help="write one format; overrides --formats (backward-compatible option)",
    )
    parser.add_argument(
        "--column-width",
        choices=("single", "double"),
        default="single",
        help="IEEE single-column (3.5 in) or double-column (7.16 in) figure",
    )
    parser.add_argument(
        "--error-bars",
        action="store_true",
        help="show population-standard-deviation bars (off to match supplied PDF)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail instead of skipping graphs with fewer than two x values",
    )
    return parser


def main():
    args = build_parser().parse_args()
    rows = read_result_files(args.input)
    fixed_window = args.fixed_window or max(row["window_size"] for row in rows)
    fixed_attempts = args.fixed_attempts or max(row["send_max_try"] for row in rows)
    by_send_rate = select_rows(rows, send_max_try=fixed_attempts)
    by_attempts = select_rows(rows, window_size=fixed_window)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt = import_pyplot()
    apply_ieee_style(plt)
    formats = (args.format,) if args.format else args.formats
    width = 3.5 if args.column_width == "single" else 7.16
    graph_specs = (
        (
            by_send_rate,
            "window_size",
            "total_edr_pairs_s",
            r"Sending rate, $w$",
            "Total EDR (qubits/s)",
            rf"Total EDR vs. Sending Rate ($M={fixed_attempts}$)",
            "01_edr_vs_send_rate",
            "edr_std_pairs_s",
        ),
        (
            by_attempts,
            "send_max_try",
            "total_edr_pairs_s",
            r"Maximum number of attempts, $M$",
            "Total EDR (qubits/s)",
            rf"Total EDR vs. Number of Attempts ($w={fixed_window}$)",
            "02_edr_vs_attempts",
            "edr_std_pairs_s",
        ),
        (
            by_attempts,
            "send_max_try",
            "mean_dropped_pairs",
            r"Maximum number of attempts, $M$",
            "Mean dropped qubits",
            rf"Dropped Qubits vs. Number of Attempts ($w={fixed_window}$)",
            "03_dropped_vs_attempts",
            None,
        ),
        (
            by_send_rate,
            "window_size",
            "mean_fairness_index",
            r"Sending rate, $w$",
            "Jain fairness index",
            rf"Resource Fairness vs. Sending Rate ($M={fixed_attempts}$)",
            "04_fairness_vs_send_rate",
            "fairness_std",
        ),
    )
    for spec in graph_specs:
        *draw_args, filename, yerr = spec
        rows_for_graph, x_field = draw_args[:2]
        if not has_x_variation(rows_for_graph, x_field):
            message = (
                f"Skipping {filename}: the CSV needs at least two distinct "
                f"{x_field} values for each algorithm"
            )
            if args.strict:
                raise ValueError(message)
            print(message)
            continue
        draw_graph(
            plt,
            *draw_args,
            output_dir / filename,
            formats,
            width,
            show_error_bars=args.error_bars,
            yerr=yerr,
        )


if __name__ == "__main__":
    main()
