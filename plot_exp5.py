"""Plot the prediction-weight sweep produced by exp5.py.

The exp5 CSV is headerless with these stable leading columns::

    seed,blend,window_size,max_attempts,mode,completed,dropped,std,cv,...

The trailing per-request list is unquoted and spills over several CSV fields,
so this reader consumes only the first nine columns.

Everything except beta is fixed at the pilot point, so the reactive and shortest
arms are flat by construction: they never read `blend`.  A reactive line that is
not flat means the sweep plumbing is broken, not that beta matters.

Arms, palette and figure style come from plot_exp1.
"""

import csv
from pathlib import Path

from plot_exp1 import (DEFAULT_OUTPUT_DIR, PLOT_MODES, MODE_LABELS,
                       apply_ieee_style, average_over_seeds, build_parser,
                       draw_panel_figure, import_pyplot, validate_unique)

DEFAULT_INPUT = "output/exp5_blend.csv"

PANEL_KWARGS = {
    "panel_field": "max_attempts",       # constant at 10, so this yields one panel
    "panel_title": r"$n=50,\ w=12,\ M=10$",
    "x_field": "blend",
    "xlabel": r"Prediction weight, $\beta$",
}


def read_results(path, duration=10.0):
    """Read exp5.py's headerless CSV and derive the per-beta metrics."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        for line_number, fields in enumerate(reader, start=1):
            if not fields or all(not field.strip() for field in fields):
                continue
            if len(fields) < 9:
                raise ValueError(
                    f"{path}:{line_number}: expected at least 9 columns, "
                    f"found {len(fields)}"
                )
            try:
                seed = int(fields[0])
                blend = float(fields[1])
                window_size = int(fields[2])
                max_attempts = int(fields[3])
                mode = fields[4].strip()
                completed = float(fields[5])
                dropped = float(fields[6])
                request_std = float(fields[7])
                cv = float(fields[8])
                if not 0.0 <= blend <= 1.0:
                    raise ValueError(f"blend outside [0, 1]: {blend}")
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            rows.append({
                "seed": seed,
                "blend": blend,
                "window_size": window_size,
                "max_attempts": max_attempts,
                "mode": mode,
                "completed": completed,
                "total_edr": completed / duration,
                "dropped": dropped,
                "drop_ratio": (dropped / (completed + dropped)
                               if completed + dropped else float("nan")),
                "request_std": request_std,
                "cv": cv,
            })
    if not rows:
        raise ValueError(f"{path}: no experiment rows found")
    return rows


def print_table(rows):
    """Mean-over-seeds results as LaTeX booktabs rows, ready to paste."""
    print(r"\begin{tabular}{llrrr}")
    print(r"\toprule")
    print(r"$\beta$ & Method & EDR (transfers/s) & $d_\mathrm{res}$ (\%) & CV \\")
    print(r"\midrule")
    for blend in sorted({row["blend"] for row in rows}):
        for mode in PLOT_MODES:
            point = next((row for row in rows
                          if row["blend"] == blend and row["mode"] == mode), None)
            if point is None:
                continue
            print(f"{blend:.1f} & {MODE_LABELS[mode]} & {point['total_edr']:.1f} & "
                  f"{100 * point['drop_ratio']:.2f} & {point['cv']:.3f} " + r"\\")
        print(r"\addlinespace")
    print(r"\bottomrule")
    print(r"\end{tabular}")


def demo():
    """Self-check for the exp5 reader; needs no matplotlib."""
    import tempfile

    from plot_exp1 import grouped_series

    text = (
        "101,0.0,12,10,reactive,500,40,1.0,0.3000,[100, 100, 100, 100, 100]\n"
        "202,0.0,12,10,reactive,700,40,1.0,0.1000,[140, 140, 140, 140, 140]\n"
        "101,0.0,12,10,predictive_cost,500,40,1.0,0.3000,[100, 100, 100, 100, 100]\n"
        "101,0.7,12,10,reactive,500,40,1.0,0.3000,[100, 100, 100, 100, 100]\n"
        "101,0.7,12,10,predictive,620,180,2.0,0.2000,[124, 124, 124, 124, 124]\n"
        "101,0.7,12,10,shortest,460,110,3.0,0.6000,[92, 92, 92, 92, 92]\n"
        "\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
        handle.write(text)
        path = handle.name

    rows = read_results(path, duration=10.0)
    assert len(rows) == 6  # the blank line is skipped
    assert rows[0]["total_edr"] == 50.0
    assert abs(rows[4]["drop_ratio"] - 180 / 800) < 1e-12
    validate_unique(rows, panel_field="max_attempts", x_field="blend")

    means = average_over_seeds(rows, panel_field="max_attempts", x_field="blend")
    point = next(row for row in means
                 if row["blend"] == 0.0 and row["mode"] == "reactive")
    assert point["seeds"] == 2
    assert point["total_edr"] == 60.0  # mean of 50.0 and 70.0

    grouped = grouped_series(means, 10, "total_edr", "max_attempts", "blend")
    assert [row["blend"] for row in grouped["reactive"]] == [0.0, 0.7]
    # shortest is parsed and grouped, but PLOT_MODES leaves it out of the figure.
    assert "shortest" in grouped and "shortest" not in PLOT_MODES

    Path(path).unlink()
    print("self-check OK")


def main():
    parser = build_parser(DEFAULT_INPUT)
    parser.add_argument("--table", action="store_true",
                        help="print the mean results as LaTeX rows and exit")
    args = parser.parse_args()
    if args.self_check:
        demo()
        return
    rows = read_results(args.input, args.duration)
    validate_unique(rows, panel_field="max_attempts", x_field="blend")
    rows = average_over_seeds(rows, panel_field="max_attempts", x_field="blend")
    if args.table:
        print_table(rows)
        return
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt = import_pyplot()
    apply_ieee_style(plt)
    specs = (
        ("total_edr", "Total EDR (qubits/s)",
         r"Exp5: EDR vs. Prediction Weight $\beta$", "12_edr_vs_blend"),
        ("drop_ratio", "Dropped-qubit ratio",
         r"Exp5: Dropped-Qubit Ratio vs. Prediction Weight $\beta$",
         "13_drop_ratio_vs_blend"),
        ("cv", "Coefficient of variation (CV)",
         r"Exp5: EDR Fairness vs. Prediction Weight $\beta$",
         "14_fairness_vs_blend"),
    )
    for y_field, ylabel, title, filename in specs:
        draw_panel_figure(plt, rows, y_field, ylabel, title,
                          output_dir / filename, args.formats, **PANEL_KWARGS)


if __name__ == "__main__":
    main()
