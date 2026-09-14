"""Plot the shrinkage-constant sweep produced by exp6.py.

The exp6 CSV is headerless with these stable leading columns::

    seed,config,window_size,max_attempts,mode,completed,dropped,std,cv,...

`config` is a label, not a number: "fix0.50" is a constant blend, "adapt_k5" is
the shrinkage weight beta(T) = k/(T+k).  Both live in one sweep so the adaptive
curve can be read against the fixed baselines it has to beat.

Two differences from the other plot scripts, both deliberate:

* One panel per routing rule, with the arms of a panel being configurations of
  that one rule -- so draw_panel_figure, which panels by a field value and
  separates series by mode, does not fit.  Only the style helpers are reused.
* Medians, not means.  The topology-to-topology spread (about +/-100 qubits/s)
  is larger than the effect being measured, and one scenario in the set drops
  over a million qubits, so a mean says more about that scenario than about k.
"""

import csv
import statistics
from pathlib import Path

from plot_exp1 import (DEFAULT_OUTPUT_DIR, MODE_LABELS, MODE_STYLES,
                       apply_ieee_style, build_parser, import_pyplot)

DEFAULT_INPUT = "output/exp6_adaptive.csv"

RULES = ("predictive", "predictive_cost")
FIXED = ("fix0.50", "fix0.70", "fix1.00")
FIXED_STYLES = {                      # grey -> dark, matching increasing beta
    "fix0.50": {"color": "#9A9A9A", "linestyle": ":"},
    "fix0.70": {"color": "#6E6E6E", "linestyle": "--"},
    "fix1.00": {"color": "#3A3A3A", "linestyle": "-."},
}


def read_results(path, duration=10.0):
    """Read exp6.py's headerless CSV into per-run rows."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as stream:
        for line_number, fields in enumerate(csv.reader(stream), start=1):
            if not fields or all(not field.strip() for field in fields):
                continue
            if len(fields) < 9:
                raise ValueError(
                    f"{path}:{line_number}: expected at least 9 columns, "
                    f"found {len(fields)}"
                )
            try:
                completed = float(fields[5])
                dropped = float(fields[6])
                row = {
                    "seed": int(fields[0]),
                    "config": fields[1].strip(),
                    "mode": fields[4].strip(),
                    "completed": completed,
                    "total_edr": completed / duration,
                    "dropped": dropped,
                    "drop_ratio": (dropped / (completed + dropped)
                                   if completed + dropped else float("nan")),
                    "cv": float(fields[8]),
                }
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            row["k"] = (int(row["config"][7:])
                        if row["config"].startswith("adapt_k") else None)
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no experiment rows found")
    return rows


def median_of(rows, mode, config, field):
    """Median of one metric over every seed at one (rule, configuration) point."""
    values = [row[field] for row in rows
              if row["mode"] == mode and row["config"] == config]
    if not values:
        raise ValueError(f"no rows for mode={mode} config={config}")
    return statistics.median(values)


def paired_wins(rows, mode, config, baseline, field, lower_is_better):
    """How many topologies `config` beats `baseline` on, compared seed by seed.

    This is the statistic that survives the topology spread: both arms ran the
    same topology and request list, so the difference is the configuration.
    """
    by_seed = {}
    for row in rows:
        if row["mode"] == mode and row["config"] in (config, baseline):
            by_seed.setdefault(row["seed"], {})[row["config"]] = row[field]
    wins = 0
    for values in by_seed.values():
        if config not in values or baseline not in values:
            continue
        wins += (values[config] < values[baseline] if lower_is_better
                 else values[config] > values[baseline])
    return wins, len(by_seed)


def draw(plt, rows, field, ylabel, title, output_base, formats):
    """One panel per rule: the adaptive curve over k against the fixed baselines."""
    ks = sorted({row["k"] for row in rows if row["k"] is not None})
    figure, axes = plt.subplots(1, len(RULES), figsize=(7.16, 2.65), sharey=True)
    for axis, mode in zip(axes, RULES):
        for config in FIXED:
            axis.axhline(median_of(rows, mode, config, field),
                         linewidth=0.9, label=config.replace("fix", r"fixed $\beta$="),
                         **FIXED_STYLES[config])
        style = dict(MODE_STYLES[mode])
        style.pop("linestyle", None)
        axis.plot(ks, [median_of(rows, mode, f"adapt_k{k}", field) for k in ks],
                  markersize=3.6, linewidth=1.3, label=r"adaptive $\beta(T)=k/(T{+}k)$",
                  **style)
        axis.set_xscale("log")
        axis.set_xticks(ks)
        axis.set_xticklabels([str(k) for k in ks])
        # The log locator would otherwise label 3x10^0, 4x10^0 ... between the ks.
        axis.xaxis.set_minor_locator(plt.NullLocator())
        axis.set_xlabel(r"Shrinkage constant, $k$")
        axis.set_title(MODE_LABELS[mode], fontsize=7.0)
        axis.grid(True, linewidth=0.3, alpha=0.4)
    axes[0].set_ylabel(ylabel)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", ncol=4, frameon=False,
                  bbox_to_anchor=(0.5, 1.13), fontsize=6.5)
    figure.suptitle(title, y=1.22, fontsize=8.0)
    figure.tight_layout()
    for suffix in formats:
        path = f"{output_base}.{suffix}"
        figure.savefig(path, dpi=600, bbox_inches="tight")
        print(f"Wrote {path}")
    plt.close(figure)


def print_table(rows):
    """Median metrics and paired win rates against each rule's best fixed beta."""
    configs = FIXED + tuple(f"adapt_k{k}" for k in
                            sorted({r["k"] for r in rows if r["k"] is not None}))
    for mode in RULES:
        best = max(FIXED, key=lambda c: median_of(rows, mode, c, "total_edr"))
        print(f"\n=== {MODE_LABELS[mode]} (baseline = best fixed = {best}) ===")
        print("  config    | med EDR | med drop% | EDR wins | drop wins")
        for config in configs:
            ew, n = paired_wins(rows, mode, config, best, "total_edr", False)
            dw, _ = paired_wins(rows, mode, config, best, "drop_ratio", True)
            print(f"  {config:9s} | {median_of(rows, mode, config, 'total_edr'):7.1f} "
                  f"| {100 * median_of(rows, mode, config, 'drop_ratio'):9.2f} "
                  f"| {ew:5d}/{n} | {dw:6d}/{n}")


def demo():
    """Self-check for the exp6 reader and aggregation; needs no matplotlib."""
    import tempfile

    text = (
        "101,fix0.50,12,10,predictive,5000,1000,1.0,0.3000,[1000]\n"
        "202,fix0.50,12,10,predictive,6000,1000,1.0,0.3000,[1200]\n"
        "101,adapt_k5,12,10,predictive,5200,400,1.0,0.3000,[1040]\n"
        "202,adapt_k5,12,10,predictive,5800,600,1.0,0.3000,[1160]\n"
        "\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
        handle.write(text)
        path = handle.name

    rows = read_results(path, duration=10.0)
    assert len(rows) == 4  # the blank line is skipped
    assert rows[0]["total_edr"] == 500.0
    assert abs(rows[0]["drop_ratio"] - 1000 / 6000) < 1e-12
    assert rows[2]["k"] == 5 and rows[0]["k"] is None  # only adapt_* carry a k

    # Medians, not means: 500 and 600 -> 550.
    assert median_of(rows, "predictive", "fix0.50", "total_edr") == 550.0
    assert median_of(rows, "predictive", "adapt_k5", "total_edr") == 550.0

    # Paired: adaptive loses EDR on seed 202 and wins on 101, but wins drops on both.
    assert paired_wins(rows, "predictive", "adapt_k5", "fix0.50", "total_edr", False) == (1, 2)
    assert paired_wins(rows, "predictive", "adapt_k5", "fix0.50", "drop_ratio", True) == (2, 2)

    Path(path).unlink()
    print("self-check OK")


def main():
    parser = build_parser(DEFAULT_INPUT)
    parser.add_argument("--table", action="store_true",
                        help="print median metrics and paired win rates, then exit")
    args = parser.parse_args()
    if args.self_check:
        demo()
        return
    rows = read_results(args.input, args.duration)
    if args.table:
        print_table(rows)
        return
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt = import_pyplot()
    apply_ieee_style(plt)
    specs = (
        ("total_edr", "Median total EDR (qubits/s)",
         r"Exp6: EDR vs. Shrinkage Constant $k$", "15_edr_vs_k"),
        ("drop_ratio", "Median dropped-qubit ratio",
         r"Exp6: Dropped-Qubit Ratio vs. Shrinkage Constant $k$", "16_drop_ratio_vs_k"),
    )
    for field, ylabel, title, filename in specs:
        draw(plt, rows, field, ylabel, title, output_dir / filename, args.formats)


if __name__ == "__main__":
    main()
