"""Plot the attempt-budget sweep produced by exp2.py.

The exp2 CSV is headerless with these columns::

    seed,window_size,max_attempts,mode,completed,dropped,route_count,"Counter(...)"

exp2.py writes one row per seed; rows sharing a parameter point are averaged
before plotting, so each marker is the mean over the paired scenarios.

The trailing Counter repr is quoted by exp2.py, so it stays a single field; it
is parsed away and unused.  Arms, palette and figure style come from plot_exp1.  Two panelled figures are written, split by sending
window: total EDR and dropped qubits, both against the retry budget M.

Style, palette and the panel renderer come from plot_exp1 so the two figure
sets stay identical in appearance.
"""

from pathlib import Path

from plot_exp1 import (DEFAULT_OUTPUT_DIR, apply_ieee_style, average_over_seeds,
                       build_parser, draw_panel_figure, import_pyplot,
                       validate_unique)

import csv

DEFAULT_INPUT = "output/exp1-4.csv"

PANEL_KWARGS = {
    "panel_field": "window_size",
    "panel_title": r"$w={}$",
    "x_field": "max_attempts",
    "xlabel": r"Maximum number of attempts, $M$",
    "integer_xticks": True,
}


def read_results(path, duration=10.0):
    """Read exp2.py's headerless CSV and derive total EDR in qubits/s."""
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
                seed = int(fields[0])
                window_size = int(fields[1])
                max_attempts = int(fields[2])
                mode = fields[3].strip()
                completed = float(fields[4])
                dropped = float(fields[5])
                route_count = int(fields[6])
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
                "drop_ratio": (dropped / (completed + dropped)
                               if completed + dropped else float("nan")),
                "route_count": route_count,
            })
    if not rows:
        raise ValueError(f"{path}: no experiment rows found")
    return rows


def demo():
    """Self-check for the exp2 reader; needs no matplotlib."""
    import tempfile

    from plot_exp1 import grouped_series

    text = (
        '101,12,1,reactive,100,5,1,"Counter({(n1, n2): 100})"\n'
        '202,12,1,reactive,140,7,1,"Counter({(n1, n2): 140})"\n'
        '101,12,2,reactive,150,9,2,"Counter({(n1, n2): 150})"\n'
        '101,12,2,predictive,180,4,2,"Counter({(n1, n3): 180})"\n'
        '101,20,1,shortest,90,0,1,"Counter({(n1, n2): 90})"\n'
        "\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
        handle.write(text)
        path = handle.name

    rows = read_results(path, duration=10.0)
    assert len(rows) == 5  # the quoted Counter stays one field; blank line skipped
    assert rows[0]["total_edr"] == 10.0
    assert rows[3]["mode"] == "predictive"
    validate_unique(rows, panel_field="window_size", x_field="max_attempts")

    means = average_over_seeds(rows, panel_field="window_size", x_field="max_attempts")
    point = next(row for row in means if row["window_size"] == 12
                 and row["max_attempts"] == 1 and row["mode"] == "reactive")
    assert point["seeds"] == 2
    assert point["total_edr"] == 12.0  # mean of 100 and 140 completed, over 10 s
    assert point["dropped"] == 6.0
    assert abs(point["drop_ratio"] - 0.0476) < 1e-4  # mean of 5/105 and 7/147

    grouped = grouped_series(means, 12, "total_edr", "window_size", "max_attempts")
    assert [row["max_attempts"] for row in grouped["reactive"]] == [1, 2]
    assert grouped["predictive"][0]["dropped"] == 4.0

    Path(path).unlink()
    print("self-check OK")


def main():
    args = build_parser(DEFAULT_INPUT).parse_args()
    if args.self_check:
        demo()
        return
    rows = read_results(args.input, args.duration)
    validate_unique(rows, panel_field="window_size", x_field="max_attempts")
    rows = average_over_seeds(rows, panel_field="window_size", x_field="max_attempts")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt = import_pyplot()
    apply_ieee_style(plt)
    specs = (
        ("total_edr", "Total EDR (qubits/s)",
         "Exp2: Total EDR vs. Number of Attempts", "02_edr_vs_attempts"),
        ("dropped", "Dropped qubits",
         "Exp2: Dropped Qubits vs. Number of Attempts", "03_dropped_vs_attempts"),
        ("drop_ratio", "Dropped-qubit ratio",
         "Exp2: Dropped-Qubit Ratio vs. Number of Attempts",
         "07_drop_ratio_vs_attempts"),
    )
    for y_field, ylabel, title, filename in specs:
        draw_panel_figure(plt, rows, y_field, ylabel, title,
                          output_dir / filename, args.formats, **PANEL_KWARGS)


if __name__ == "__main__":
    main()
