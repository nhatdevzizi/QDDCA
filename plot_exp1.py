"""Plot the sending-window sweep produced by exp1.py.

The exp1 CSV is headerless and its stable leading columns are::

    seed,window_size,max_attempts,mode,completed,dropped,std,cv,...

exp1.py writes one row per seed; rows sharing a parameter point are averaged
before plotting, so each marker is the mean over the paired scenarios.

The trailing per-request list is written unquoted, so it spills over several
CSV fields; this reader consumes only the first eight columns.  Three panelled
figures are written, split by retry budget: total EDR, dropped qubits, and the
coefficient of variation of per-request EDR.

Three arms are drawn: `reactive` is Q-DDCA as published, `predictive` selects
hops by p/hops, and `predictive_cost` feeds the same predicted p into Y(v) so
the drop penalty still counts.  The `shortest` (SPA) rows are parsed but not
plotted.
"""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


DEFAULT_INPUT = "output/exp2-7.1.csv"
DEFAULT_OUTPUT_DIR = "output/plot"

# Draw order is baseline first so the proposed arms sit on top.
PLOT_MODES = ("reactive", "predictive", "predictive_cost")
MODE_LABELS = {
    "reactive": "Q-DDCA",
    "predictive": "Predictive Q-DDCA",
    "predictive_cost": "Predictive Q-DDCA (drop-priced)",
}
MODE_STYLES = {
    "reactive": {
        "color": "#4D4D4D",
        "marker": "o",
        "markerfacecolor": "white",
        "linestyle": "-",
    },
    "predictive": {
        "color": "#B8860B",
        "marker": "^",
        "markerfacecolor": "#B8860B",
        "linestyle": "-",
    },
    "predictive_cost": {
        "color": "#2C5F8A",
        "marker": "s",
        "markerfacecolor": "#2C5F8A",
        "linestyle": "-",
    },
}


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
            if len(fields) < 8:
                raise ValueError(
                    f"{path}:{line_number}: expected at least 8 columns, "
                    f"found {len(fields)}"
                )
            try:
                seed = int(fields[0])
                window_size = int(fields[1])
                max_attempts = int(fields[2])
                mode = fields[3].strip()
                completed = float(fields[4])
                dropped = float(fields[5])
                request_std = float(fields[6])
                cv = float(fields[7])
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            rows.append({
                "seed": seed,
                "window_size": window_size,
                "max_attempts": max_attempts,
                "mode": mode,
                "completed": completed,
                "total_edr": completed / duration,
                "dropped": dropped,
                # Raw drop counts scale with the traffic an arm managed to inject,
                # so the ratio is what actually compares two arms.
                "drop_ratio": (dropped / (completed + dropped)
                               if completed + dropped else float("nan")),
                "request_std": request_std,
                "cv": cv,
            })
    if not rows:
        raise ValueError(f"{path}: no experiment rows found")
    return rows


def validate_unique(rows, panel_field="max_attempts", x_field="window_size"):
    seen = set()
    for row in rows:
        key = (row["seed"], row[x_field], row[panel_field], row["mode"])
        if key in seen:
            raise ValueError(f"duplicate parameter row: {key}")
        seen.add(key)


def average_over_seeds(rows, panel_field="max_attempts", x_field="window_size"):
    """Collapse the per-seed rows into one mean row per (panel, x, arm).

    A non-finite value is left out of its own metric's mean rather than
    poisoning it: exp1 writes cv=inf whenever a scenario completed nothing, and
    that must not erase the seeds that did complete something.
    """
    metrics = [key for key, value in rows[0].items() if isinstance(value, float)]
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row[panel_field], row[x_field], row["mode"])].append(row)
    averaged = []
    for (panel_value, x_value, mode), samples in grouped.items():
        merged = {panel_field: panel_value, x_field: x_value, "mode": mode,
                  "seeds": len(samples)}
        for metric in metrics:
            finite = [row[metric] for row in samples if math.isfinite(row[metric])]
            merged[metric] = sum(finite) / len(finite) if finite else float("nan")
        averaged.append(merged)
    return averaged


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


def grouped_series(rows, panel_value, y_field, panel_field, x_field):
    """Rows of one panel, keyed by arm and sorted along the x axis.

    Non-finite values are dropped, which is what removes the cv=inf rows exp1
    writes whenever a panel produced no entanglement at all.
    """
    grouped = defaultdict(list)
    for row in rows:
        if row[panel_field] != panel_value:
            continue
        if math.isfinite(row[y_field]):
            grouped[row["mode"]].append(row)
    return {
        mode: sorted(samples, key=lambda row: row[x_field])
        for mode, samples in grouped.items()
    }


def draw_panel_figure(plt, rows, y_field, ylabel, title, output_base, formats,
                      panel_field="max_attempts", panel_title=r"$M={}$",
                      x_field="window_size", xlabel=r"Sending window size, $w$",
                      integer_xticks=False):
    """One figure: a panel per fixed parameter value, two arms per panel."""
    panel_values = sorted({row[panel_field] for row in rows})
    if len(panel_values) == 1:
        # Single-column width; the 7.16 in double-column box is far too wide here.
        figure, axes = plt.subplots(1, 1, figsize=(3.5, 2.45))
        axes = [axes]
    else:
        figure, axes = plt.subplots(
            1, len(panel_values), figsize=(7.16, 2.45), sharex=True, sharey=True
        )
    legend_handles = None
    legend_labels = None
    for axis, panel_value in zip(axes, panel_values):
        grouped = grouped_series(rows, panel_value, y_field, panel_field, x_field)
        for mode in PLOT_MODES:
            samples = grouped.get(mode, [])
            if not samples:
                continue
            axis.plot(
                [row[x_field] for row in samples],
                [row[y_field] for row in samples],
                markersize=3.1,
                markeredgewidth=0.55,
                label=MODE_LABELS[mode],
                **MODE_STYLES[mode],
            )
        axis.set_title(panel_title.format(panel_value), pad=3, fontweight="normal")
        axis.set_xlabel(xlabel, labelpad=2)
        if integer_xticks:
            axis.set_xticks(sorted({row[x_field] for row in rows}))
        axis.tick_params(direction="out", pad=1.5)
        axis.grid(False)
        handles, labels = axis.get_legend_handles_labels()
        if handles:
            legend_handles, legend_labels = handles, labels
    axes[0].set_ylabel(ylabel, labelpad=2)
    figure.suptitle(title, y=1.02, fontsize=8.0, fontweight="normal")
    if legend_handles:
        figure.legend(
            legend_handles,
            legend_labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.995),
            ncol=min(len(legend_labels), 3),
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


def build_parser(default_input=DEFAULT_INPUT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=default_input)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="simulation duration used to convert completed qubits to EDR",
    )
    parser.add_argument(
        "--formats",
        type=parse_formats,
        default=("pdf", "png"),
        help="comma-separated outputs (default: pdf,png)",
    )
    parser.add_argument("--self-check", action="store_true",
                        help="run assertions and exit")
    return parser


def demo():
    """Self-check for the reader and the panel grouping; needs no matplotlib."""
    import tempfile

    text = (
        "101,1,10,shortest,90,0,0.0,0.0000,[18, 18, 18, 18, 18]\n"
        "101,1,10,reactive,100,5,1.0,0.0500,[20, 20, 20, 20, 20]\n"
        "202,1,10,reactive,140,5,1.0,inf,[28, 28, 28, 28, 28]\n"
        "101,2,10,reactive,200,9,2.0,0.1000,[40, 40, 40, 40, 40]\n"
        "101,2,10,predictive,240,4,1.0,0.0400,[48, 48, 48, 48, 48]\n"
        "101,1,1,reactive,0,7,0.0,inf,[0, 0, 0, 0, 0]\n"
        "101,1,1,predictive_cost,0,0,0.0,inf,[0, 0, 0, 0, 0]\n"
        "\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
        handle.write(text)
        path = handle.name

    rows = read_results(path, duration=10.0)
    assert len(rows) == 7  # the blank line is skipped
    assert rows[1]["total_edr"] == 10.0  # 100 completed / 10 s
    assert rows[0]["mode"] == "shortest"
    assert rows[2]["seed"] == 202
    validate_unique(rows)  # the same point under another seed is not a duplicate

    means = average_over_seeds(rows)
    point = next(row for row in means if row["window_size"] == 1
                 and row["max_attempts"] == 10 and row["mode"] == "reactive")
    assert point["seeds"] == 2
    assert point["total_edr"] == 12.0  # mean of 100 and 140 completed, over 10 s
    assert point["cv"] == 0.05  # the inf seed drops out of the cv mean only
    assert abs(point["drop_ratio"] - 0.0410) < 1e-4  # mean of 5/105 and 5/145

    assert "predictive_cost" in PLOT_MODES and "predictive_cost" in MODE_STYLES

    # A run that completed nothing has ratio 1.0; one with no traffic at all has
    # no ratio, so only the first of the two reaches the axes.
    at_m1 = grouped_series(means, 1, "drop_ratio", "max_attempts", "window_size")
    assert set(at_m1) == {"reactive"}
    assert at_m1["reactive"][0]["drop_ratio"] == 1.0

    grouped = grouped_series(means, 10, "total_edr", "max_attempts", "window_size")
    assert set(grouped) == {"shortest", "reactive", "predictive"}
    assert [row["window_size"] for row in grouped["reactive"]] == [1, 2]
    assert grouped["predictive"][0]["dropped"] == 4.0

    # A point whose every seed is non-finite must not reach the axes.
    assert grouped_series(means, 1, "cv", "max_attempts", "window_size") == {}
    assert set(grouped_series(means, 1, "dropped", "max_attempts", "window_size")) == {
        "reactive", "predictive_cost"}

    try:
        validate_unique(rows + [rows[0]])
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate parameter row was not rejected")

    try:
        read_results(path, duration=0)
    except ValueError:
        pass
    else:
        raise AssertionError("non-positive duration was not rejected")

    Path(path).unlink()
    print("self-check OK")


def main():
    args = build_parser().parse_args()
    if args.self_check:
        demo()
        return
    rows = read_results(args.input, args.duration)
    validate_unique(rows)
    rows = average_over_seeds(rows)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt = import_pyplot()
    apply_ieee_style(plt)
    specs = (
        ("total_edr", "Total EDR (qubits/s)",
         "Exp1: Total EDR vs. Sending Rate", "01_edr_vs_send_rate"),
        ("dropped", "Dropped qubits",
         "Exp1: Dropped Qubits vs. Sending Rate", "05_dropped_vs_send_rate"),
        ("cv", "Coefficient of variation (CV)",
         "Exp1: EDR Fairness vs. Sending Rate", "04_fairness_vs_send_rate"),
        ("drop_ratio", "Dropped-qubit ratio",
         "Exp1: Dropped-Qubit Ratio vs. Sending Rate", "06_drop_ratio_vs_send_rate"),
    )
    for y_field, ylabel, title, filename in specs:
        draw_panel_figure(plt, rows, y_field, ylabel, title,
                          output_dir / filename, args.formats)


if __name__ == "__main__":
    main()
