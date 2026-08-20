"""Plot a parameter sweep in the paper's figure style.

Three IEEE single-column figures:

    Fig. 1  Total EDR vs the swept parameter
    Fig. 2  Dropped qubits vs the swept parameter
    Fig. 3  (a) difference against the baseline value
            (b) difference between consecutive values

Figures 1 and 2 keep the two-series look of the existing paper figures: the
baseline configuration is a constant, drawn as the black open-circle series, and
the swept parameter is the gold filled-triangle series. The vertical distance
between them is what the parameter buys. Identity is carried by marker shape as
well as colour, so the figures survive black-and-white printing.

Running this module plots the alpha sweep from exp5.py. `plot_exp6.py` reuses
everything here with an epsilon PlotSpec.
"""

import argparse
import csv
import math
from collections import namedtuple
from pathlib import Path


COLUMN_WIDTH = 3.5  # inches — IEEE single column (88 mm)
HISTORICAL = "#000000"
REALTIME = "#b8860b"  # darkgoldenrod; clears 3:1 on white, unlike plain goldenrod
GAP_FILL = "#d9d9d9"
TICK_MAJOR = None     # labelled tick spacing; None derives one from the range
TICK_MINOR = None     # unlabelled tick spacing; None follows the CSV's own step


PlotSpec = namedtuple(
    "PlotSpec",
    "column delta_col baseline symbol axis_label baseline_label swept_label "
    "title_noun captions")


ALPHA = PlotSpec(
    column="alpha",
    delta_col="delta_edr_vs_prev_alpha",
    baseline=1.0,
    symbol=r"\alpha",
    axis_label=r"History weight $\alpha$",
    baseline_label=r"Historical Q-DDCA ($\alpha=1$)",
    swept_label=r"Real-Time Q-DDCA ($\alpha$ swept)",
    title_noun=r"History Weight $\alpha$",
    captions=(
        r"\caption{Total EDR as the history weight $\alpha$ of "
        r"$\hat{q}_v=\alpha q_v^{hist}+(1-\alpha)(1-\rho_v)$ is swept. The "
        r"historical-only algorithm is the $\alpha=1$ case and is therefore "
        r"constant; the shaded area is the gain of the real-time estimator. All "
        r"$\alpha$ run on the same seeded topologies, so the curves are paired.}",
        r"\caption{Dropped qubits over the same sweep; lower is better. The "
        r"minimum sits at $\alpha=DROPMIN$, away from the EDR optimum, so "
        r"throughput and wasted attempts are not optimised by the same weight.}",
        r"\caption{Difference in total EDR. (a) Each $\alpha$ against the "
        r"$\alpha=1$ baseline. (b) Each $STEP$ step against the previous "
        r"$\alpha$; the hatched bar is the largest single step, $PEAKSTEP$.}",
    ),
)


def to_float(value):
    """Parse a CSV cell, returning None for the empty cells the sweeps write."""
    value = value.strip()
    return float(value) if value else None


def read_rows(path, spec):
    """Read the sweep CSV sorted by the swept parameter."""
    with open(path, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise SystemExit(f"{path} has no data rows")
    if spec.column not in rows[0]:
        raise SystemExit(f"{path} has no '{spec.column}' column — wrong sweep file?")
    return sorted(rows, key=lambda row: float(row[spec.column]))


def grid_step(values):
    """Grid spacing of the sweep; bar widths and marker density follow from it."""
    return values[1] - values[0] if len(values) > 1 else 0.1


def nice_step(span, target=10):
    """Round span/target up to a 1-2-5 style number so tick labels stay readable.

    A sweep over [0, 1] lands on 0.1 and one over [0.1, 10] lands on 1, so the
    axis carries about ten labels whatever the parameter's range happens to be.
    """
    raw = span / target
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiple in (1, 2, 2.5, 5):
        if raw <= multiple * magnitude:
            return multiple * magnitude
    return 10 * magnitude


def major_step(values):
    """Labelled tick spacing: the override if given, otherwise derived."""
    return TICK_MAJOR or nice_step(values[-1] - values[0])


def marker_every(values):
    """Thin markers so a fine grid does not turn the line into a solid band."""
    return max(1, round(major_step(values) / grid_step(values)))


def set_param_axis(axes, values):
    """Tick the parameter axis, by default down to the sweep's own resolution.

    Major ticks carry the labels; minor ticks default to the actual grid, so
    every simulated point is readable off the axis. Both are overridable with
    --tick-major / --tick-minor.
    """
    from matplotlib.ticker import AutoMinorLocator, MultipleLocator

    span = values[-1] - values[0]
    axes.set_xlim(values[0] - 0.02 * span, values[-1] + 0.02 * span)
    axes.xaxis.set_major_locator(MultipleLocator(major_step(values)))
    axes.xaxis.set_minor_locator(MultipleLocator(TICK_MINOR or grid_step(values)))
    axes.yaxis.set_minor_locator(AutoMinorLocator(2))


def baseline_row(rows, spec):
    """Return the row holding the baseline configuration."""
    for row in rows:
        if float(row[spec.column]) == spec.baseline:
            return row
    raise SystemExit(
        f"no {spec.column}={spec.baseline} row to use as the baseline")


def apply_style(matplotlib):
    """Match the paper's figures: serif type, framed axes, no grid."""
    matplotlib.rcParams.update({
        "font.family": "serif",
        # Liberation Serif and Nimbus Roman are metric-compatible with Times.
        "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 8.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 6.8,
        "legend.frameon": True,
        "legend.edgecolor": "#000000",
        "legend.framealpha": 1.0,
        "legend.borderpad": 0.35,
        "legend.handlelength": 2.0,
        "axes.linewidth": 0.7,
        "axes.grid": False,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "xtick.minor.width": 0.5,
        "ytick.minor.width": 0.5,
        "lines.linewidth": 1.0,
        "figure.dpi": 150,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,  # embed TrueType so the PDF stays editable/searchable
        "ps.fonttype": 42,
    })


def comparison_figure(rows, plt, spec, column, ylabel, title):
    """Draw one two-series comparison: constant baseline vs each swept value.

    No error bars: every value runs on the same seeded topologies, so the paired
    difference between the curves is the meaningful quantity, and the marginal
    seed-to-seed spread would overstate the uncertainty of that difference.
    """
    params = [float(row[spec.column]) for row in rows]
    values = [float(row[column]) for row in rows]
    baseline = float(baseline_row(rows, spec)[column])

    figure, axes = plt.subplots(figsize=(COLUMN_WIDTH, COLUMN_WIDTH / 1.5))

    axes.fill_between(params, [baseline] * len(params), values,
                      color=GAP_FILL, linewidth=0, zorder=1)
    every = marker_every(params)
    axes.plot(params, [baseline] * len(params), color=HISTORICAL, marker="o",
              markersize=3.6, markerfacecolor="none", markeredgewidth=0.8,
              markevery=every, label=spec.baseline_label, zorder=3)
    axes.plot(params, values, color=REALTIME, marker="^", markersize=3.8,
              markerfacecolor=REALTIME, markevery=every,
              label=spec.swept_label, zorder=4)

    axes.set_title(title)
    axes.set_xlabel(spec.axis_label)
    axes.set_ylabel(ylabel)
    set_param_axis(axes, params)
    axes.set_ylim(0, max(values + [baseline]) * 1.18)
    axes.legend(loc="lower right")
    return figure


def delta_figure(rows, plt, spec):
    """Both readings of 'difference': against the baseline, and step to step."""
    params = [float(row[spec.column]) for row in rows]
    baseline = float(baseline_row(rows, spec)["total_edr_pairs_s"])
    versus_baseline = [float(row["total_edr_pairs_s"]) - baseline for row in rows]
    step_delta = [to_float(row[spec.delta_col]) for row in rows]

    figure, (ax_base, ax_step) = plt.subplots(
        2, 1, figsize=(COLUMN_WIDTH, 2 * COLUMN_WIDTH / 1.7), sharex=True,
        gridspec_kw={"hspace": 0.15})

    step = grid_step(params)
    edge = 0.5 if step > 0.05 else 0.0
    ax_base.bar(params, versus_baseline, width=step * 0.8, color=REALTIME,
                edgecolor=HISTORICAL, linewidth=edge, zorder=3)
    ax_base.axhline(0, color=HISTORICAL, linewidth=0.7, zorder=4)
    ax_base.set_ylabel(rf"EDR$({spec.symbol})$ $-$ EDR$({spec.baseline:g})$")
    ax_base.set_ylim(min(0, min(versus_baseline) * 1.3), max(versus_baseline) * 1.30)
    ax_base.text(0.03, 0.93, "(a)", transform=ax_base.transAxes, va="top", fontsize=8)

    # Each bar spans the step it was computed over, hence the midpoint x.
    steps = [(a, prev, d) for a, prev, d in
             zip(params[1:], params[:-1], step_delta[1:]) if d is not None]
    centres = [(a + prev) / 2 for a, prev, _ in steps]
    values = [d for _, _, d in steps]
    bars = ax_step.bar(centres, values, width=step * 0.9, color=REALTIME,
                       edgecolor=HISTORICAL, linewidth=edge, zorder=3)
    # Mark the largest single step, wherever it falls — for alpha that is the
    # collapse at the top end, for epsilon it sits in the middle.
    peak = max(range(len(values)), key=lambda i: abs(values[i]))
    bars[peak].set_hatch("///")
    ax_step.axhline(0, color=HISTORICAL, linewidth=0.7, zorder=4)
    ax_step.set_ylim(min(values) * 1.30, max(values) * 3.2)
    ax_step.annotate(f"{values[peak]:.1f}", xy=(centres[peak], values[peak]),
                     xytext=(-13, 2), textcoords="offset points", ha="right",
                     va="bottom" if values[peak] < 0 else "top", fontsize=7)
    ax_step.set_ylabel(
        rf"EDR$({spec.symbol})$ $-$ EDR$({spec.symbol}-{step:g})$")
    ax_step.set_xlabel(spec.axis_label)
    set_param_axis(ax_base, params)
    set_param_axis(ax_step, params)
    ax_step.text(0.03, 0.93, "(b)", transform=ax_step.transAxes, va="top", fontsize=8)

    return figure


def build_figures(rows, plt, spec):
    """Return (filename stem, figure) for each figure in the set."""
    requests = rows[0]["request_count"]
    yield "fig1_edr", comparison_figure(
        rows, plt, spec, "total_edr_pairs_s", "EDR (qubit/s)",
        f"Total EDR vs. {spec.title_noun} ({requests} Requests)")
    yield "fig2_drop", comparison_figure(
        rows, plt, spec, "mean_dropped_pairs", "dropped qubits",
        f"Number of Dropped Qubits vs. {spec.title_noun} ({requests} Requests)")
    yield "fig3_delta", delta_figure(rows, plt, spec)


def captions(rows, spec):
    """LaTeX captions, with the sweep's own grid spacing filled in.

    Substitution is by replace, not str.format — the templates are full of
    LaTeX braces.
    """
    params = [float(row[spec.column]) for row in rows]
    best_drop = min(rows, key=lambda row: float(row["mean_dropped_pairs"]))
    # The hatched bar in Fig. 3(b) is the largest single step, wherever it falls.
    deltas = [(abs(to_float(row[spec.delta_col]) or 0.0), index)
              for index, row in enumerate(rows)]
    peak = max(deltas)[1]
    fields = {  # PEAKSTEP before STEP — the shorter key is a substring of the longer
        "PEAKSTEP": rf"{params[peak - 1]:g}\rightarrow{params[peak]:g}",
        "DROPMIN": f"{float(best_drop[spec.column]):g}",
        "STEP": f"{grid_step(params):g}",
    }
    result = []
    for text in spec.captions:
        for key, value in fields.items():
            text = text.replace(key, value)
        result.append(text)
    return tuple(result)


def demo(spec=ALPHA):
    """Self-check for CSV parsing and baseline lookup; needs no matplotlib."""
    assert to_float("") is None
    assert to_float("  ") is None
    assert to_float("1.5") == 1.5
    assert to_float("-575.000000") == -575.0
    assert abs(grid_step([0.0, 0.02, 0.04]) - 0.02) < 1e-12
    # A [0, 1] sweep keeps the historical 0.1 tick; [0.1, 10] widens to 1.
    assert abs(nice_step(1.0) - 0.1) < 1e-12
    assert abs(nice_step(9.9) - 1.0) < 1e-12
    assert abs(nice_step(0.5) - 0.05) < 1e-12
    assert marker_every([round(i * 0.02, 4) for i in range(51)]) == 5
    assert marker_every([round(0.1 + i * 0.1, 4) for i in range(100)]) == 10

    rows = [{spec.column: "0.000000", "total_edr_pairs_s": "10"},
            {spec.column: f"{spec.baseline:.6f}", "total_edr_pairs_s": "8"}]
    assert baseline_row(rows, spec)["total_edr_pairs_s"] == "8"
    print("self-check OK")


def run_cli(spec, default_input, default_outdir, default_stem):
    """Shared entry point: parse arguments, render the three figures."""
    global TICK_MAJOR, TICK_MINOR

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=default_input)
    parser.add_argument("--outdir", default=default_outdir)
    parser.add_argument("--stem", default=default_stem)
    parser.add_argument("--formats", default="pdf,png",
                        help="comma-separated extensions, e.g. pdf,png,eps")
    parser.add_argument("--tick-major", type=float, default=None,
                        help="labelled tick spacing; default derives one from the range")
    parser.add_argument("--tick-minor", type=float, default=None,
                        help="unlabelled tick spacing; default follows the CSV's own step")
    parser.add_argument("--self-check", action="store_true", help="run assertions and exit")
    args = parser.parse_args()

    if args.self_check:
        demo(spec)
        return

    for name, value in (("--tick-major", args.tick_major), ("--tick-minor", args.tick_minor)):
        if value is not None and value <= 0:
            parser.error(f"{name} must be positive")

    TICK_MAJOR = args.tick_major
    TICK_MINOR = args.tick_minor

    import matplotlib
    matplotlib.use("Agg")
    apply_style(matplotlib)
    import matplotlib.pyplot as plt

    rows = read_rows(args.input, spec)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    extensions = [item.strip() for item in args.formats.split(",") if item.strip()]

    for name, figure in build_figures(rows, plt, spec):
        for extension in extensions:
            path = outdir / f"{args.stem}_{name}.{extension}"
            figure.savefig(path)
            print(f"Wrote {path}")
        plt.close(figure)

    print("\nSuggested LaTeX captions:")
    for index, caption in enumerate(captions(rows, spec), start=1):
        print(f"% Fig. {index}\n{caption}\n")


if __name__ == "__main__":
    run_cli(ALPHA, "output/exp5/exp5_alpha_sweep.csv", "output/exp5/plot", "exp5")
