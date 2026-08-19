"""Plot the window-size sweep produced by exp1.py.

The exp1 CSV is headerless and contains these stable leading columns::

    window_size,max_attempts,reroute,completed,dropped,std,cv,...

The final per-request list is not quoted by exp1.py and can therefore occupy
multiple CSV fields.  This reader intentionally consumes only the first seven
columns.  Three panelled figures are written by default: total EDR, dropped
qubits, and the coefficient of variation, each split by retry budget.
"""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


DEFAULT_INPUT = "output/exp1/exp2-7.1.csv"
DEFAULT_OUTPUT_DIR = "output/exp1/plot"

ROUTE_LABELS = {
    False: "Rerouting disabled",
    True: "Q-DDCA rerouting",
}
ROUTE_STYLES = {
    False: {
        "color": "#4D4D4D",
        "marker": "o",
        "markerfacecolor": "white",
        "linestyle": "-",
    },
    True: {
        "color": "#B8860B",
        "marker": "^",
        "markerfacecolor": "#B8860B",
        "linestyle": "-",
    },
}


def parse_bool(value):
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"invalid reroute value: {value!r}")


def read_results(path, duration=10.0):
    """Read exp1.py's headerless CSV and derive total EDR in qubits/s."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        for line_number, fields in enumerate(reader, start=1):
            if not fields or all(not field.strip() for field in fields):
                continue
            if len(fields) < 7:
                raise ValueError(
                    f"{path}:{line_number}: expected at least 7 columns, "
                    f"found {len(fields)}"
                )
            try:
                window_size = int(fields[0])
                max_attempts = int(fields[1])
                reroute = parse_bool(fields[2])
                completed = float(fields[3])
                dropped = float(fields[4])
                request_std = float(fields[5])
                cv = float(fields[6])
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            rows.append({
                "window_size": window_size,
                "max_attempts": max_attempts,
                "reroute": reroute,
                "completed": completed,
                "total_edr": completed / duration,
                "dropped": dropped,
                "request_std": request_std,
                "cv": cv,
            })
    if not rows:
        raise ValueError(f"{path}: no experiment rows found")
    return rows


def validate_unique(rows):
    seen = set()
    for row in rows:
        key = (row["window_size"], row["max_attempts"], row["reroute"])
        if key in seen:
            raise ValueError(f"duplicate exp1 parameter row: {key}")
        seen.add(key)


def apply_ieee_style(plt):
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": [
            "Times New Roman", "Times", "Liberation Serif", "Nimbus Roman",
            "Nimbus Roman No9 L", "DejaVu Serif",
        ],
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
        "legend.fontsize": 6.0,
        "lines.linewidth": 0.85,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
    })


def import_pyplot():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise SystemExit(
            "matplotlib is required; install it with "
            "'python -m pip install matplotlib'"
        ) from error
    return plt


def parse_formats(value):
    formats = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    supported = {"png", "pdf", "svg", "eps"}
    unsupported = set(formats) - supported
    if not formats or unsupported:
        raise argparse.ArgumentTypeError(
            "formats must be selected from: " + ", ".join(sorted(supported))
        )
    return formats


def grouped_series(rows, max_attempts, y_field):
    grouped = defaultdict(list)
    for row in rows:
        if row["max_attempts"] != max_attempts:
            continue
        value = row[y_field]
        if math.isfinite(value):
            grouped[row["reroute"]].append(row)
    return {
        reroute: sorted(samples, key=lambda row: row["window_size"])
        for reroute, samples in grouped.items()
    }


def draw_panel_figure(
    plt,
    rows,
    y_field,
    ylabel,
    title,
    output_base,
    formats,
    column_width,
):
    attempt_values = sorted({row["max_attempts"] for row in rows})
    if column_width == "double":
        figure, axes = plt.subplots(
            1, len(attempt_values), figsize=(7.16, 2.45), sharex=True, sharey=True
        )
    else:
        figure, axes = plt.subplots(
            len(attempt_values), 1, figsize=(3.5, 2.0 * len(attempt_values)),
            sharex=True, sharey=True,
        )
    if len(attempt_values) == 1:
        axes = [axes]
    legend_handles = None
    legend_labels = None
    for axis, max_attempts in zip(axes, attempt_values):
        grouped = grouped_series(rows, max_attempts, y_field)
        for reroute in (False, True):
            samples = grouped.get(reroute, [])
            if not samples:
                continue
            axis.plot(
                [row["window_size"] for row in samples],
                [row[y_field] for row in samples],
                markersize=3.1,
                markeredgewidth=0.55,
                label=ROUTE_LABELS[reroute],
                **ROUTE_STYLES[reroute],
            )
        axis.set_title(rf"$M={max_attempts}$", pad=3, fontweight="normal")
        axis.set_xlabel(r"Sending window size, $w$", labelpad=2)
        axis.tick_params(direction="out", pad=1.5)
        axis.grid(False)
        handles, labels = axis.get_legend_handles_labels()
        if handles:
            legend_handles, legend_labels = handles, labels
    axes[0].set_ylabel(ylabel, labelpad=2)
    if column_width == "single":
        for axis in axes[1:]:
            axis.set_ylabel(ylabel, labelpad=2)
    figure.suptitle(title, y=1.02, fontsize=8.0, fontweight="normal")
    if legend_handles:
        figure.legend(
            legend_handles,
            legend_labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.995),
            ncol=2,
            frameon=False,
            handlelength=2.2,
        )
    figure.tight_layout(rect=(0, 0, 1, 0.90))
    for output_format in formats:
        output_path = output_base.with_suffix(f".{output_format}")
        options = {"bbox_inches": "tight", "pad_inches": 0.025}
        if output_format == "png":
            options["dpi"] = 600
        figure.savefig(output_path, **options)
        print(f"Wrote {output_path}")
    plt.close(figure)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="simulation duration used to convert completed pairs to EDR",
    )
    parser.add_argument(
        "--formats",
        type=parse_formats,
        default=("pdf", "png"),
        help="comma-separated outputs (default: pdf,png)",
    )
    parser.add_argument(
        "--column-width",
        choices=("single", "double"),
        default="double",
        help="stack panels at single-column width or place them side by side",
    )
    return parser


def main():
    args = build_parser().parse_args()
    rows = read_results(args.input, args.duration)
    validate_unique(rows)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt = import_pyplot()
    apply_ieee_style(plt)
    specs = (
        (
            "total_edr",
            "Total EDR (qubits/s)",
            "Exp1: Total EDR vs. Sending Window",
            "01_edr_vs_window",
        ),
        (
            "dropped",
            "Dropped qubits",
            "Exp1: Dropped Qubits vs. Sending Window",
            "02_dropped_vs_window",
        ),
        (
            "cv",
            "Coefficient of variation (CV)",
            "Exp1: EDR Fairness vs. Sending Window",
            "03_cv_vs_window",
        ),
    )
    for y_field, ylabel, title, filename in specs:
        draw_panel_figure(
            plt,
            rows,
            y_field,
            ylabel,
            title,
            output_dir / filename,
            args.formats,
            args.column_width,
        )


if __name__ == "__main__":
    main()
