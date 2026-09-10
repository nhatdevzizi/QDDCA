"""Plot the topology-size sweep produced by exp4.py.

The exp4 CSV is headerless with these stable leading columns::

    seed,node_count,request_count,window_size,max_attempts,mode,completed,dropped,std,cv,...

The trailing per-request list is unquoted and spills over several CSV fields,
so this reader consumes only the first ten columns.  One row per seed is
written; rows sharing a parameter point are averaged before plotting.

Because the request count grows with n, total EDR rises mechanically with the
network size; `edr_per_request` is the quantity that compares across sizes.

Arms, palette and figure style come from plot_exp1.
"""

import csv
from pathlib import Path

from plot_exp1 import (DEFAULT_OUTPUT_DIR, apply_ieee_style, average_over_seeds,
                       build_parser, draw_panel_figure, import_pyplot,
                       validate_unique)

DEFAULT_INPUT = "output/exp4_scale.csv"

PANEL_KWARGS = {
    "panel_field": "max_attempts",       # constant at 10, so this yields one panel
    "panel_title": r"$w=12,\ M=10$",
    "x_field": "node_count",
    "xlabel": r"Number of nodes, $n$",
    "integer_xticks": True,
}


def read_results(path, duration=10.0):
    """Read exp4.py's headerless CSV and derive the per-size EDR metrics."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        for line_number, fields in enumerate(reader, start=1):
            if not fields or all(not field.strip() for field in fields):
                continue
            if len(fields) < 10:
                raise ValueError(
                    f"{path}:{line_number}: expected at least 10 columns, "
                    f"found {len(fields)}"
                )
            try:
                seed = int(fields[0])
                node_count = int(fields[1])
                request_count = int(fields[2])
                window_size = int(fields[3])
                max_attempts = int(fields[4])
                mode = fields[5].strip()
                completed = float(fields[6])
                dropped = float(fields[7])
                request_std = float(fields[8])
                cv = float(fields[9])
                if request_count <= 0:
                    raise ValueError(f"invalid request count: {request_count}")
            except ValueError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            rows.append({
                "seed": seed,
                "node_count": node_count,
                "request_count": request_count,
                "window_size": window_size,
                "max_attempts": max_attempts,
                "mode": mode,
                "completed": completed,
                "total_edr": completed / duration,
                # Requests scale with n, so only the per-request rate compares sizes.
                "edr_per_request": completed / duration / request_count,
                "dropped": dropped,
                "drop_ratio": (dropped / (completed + dropped)
                               if completed + dropped else float("nan")),
                "request_std": request_std,
                "cv": cv,
            })
    if not rows:
        raise ValueError(f"{path}: no experiment rows found")
    return rows


def demo():
    """Self-check for the exp4 reader; needs no matplotlib."""
    import math
    import tempfile

    from plot_exp1 import grouped_series

    text = (
        "101,25,2,12,10,reactive,100,5,1.0,0.0500,[50, 50]\n"
        "202,25,2,12,10,reactive,140,5,1.0,inf,[70, 70]\n"
        "101,25,2,12,10,predictive,120,4,1.0,0.0400,[60, 60]\n"
        "101,50,5,12,10,reactive,200,9,2.0,0.1000,[40, 40, 40, 40, 40]\n"
        "101,50,5,12,10,predictive_cost,250,3,1.0,0.0300,[50, 50, 50, 50, 50]\n"
        "101,50,5,12,10,shortest,0,0,0.0,inf,[0, 0, 0, 0, 0]\n"
        "\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
        handle.write(text)
        path = handle.name

    rows = read_results(path, duration=10.0)
    assert len(rows) == 6  # the blank line is skipped
    assert rows[0]["total_edr"] == 10.0
    assert rows[0]["edr_per_request"] == 5.0  # 100 completed / 10 s / 2 requests
    assert rows[3]["edr_per_request"] == 4.0  # 200 / 10 s / 5 requests
    validate_unique(rows, panel_field="max_attempts", x_field="node_count")

    means = average_over_seeds(rows, panel_field="max_attempts", x_field="node_count")
    point = next(row for row in means if row["node_count"] == 25
                 and row["mode"] == "reactive")
    assert point["seeds"] == 2
    assert point["edr_per_request"] == 6.0  # mean of 5.0 and 7.0
    assert point["cv"] == 0.05  # the inf seed drops out of the cv mean only

    grouped = grouped_series(means, 10, "cv", "max_attempts", "node_count")
    assert [row["node_count"] for row in grouped["reactive"]] == [25, 50]
    # A run that completed nothing has no CV to plot but still has a drop ratio.
    assert "shortest" not in grouped
    # Averaging leaves nan, not inf: every seed of that point was non-finite.
    empty = next(row for row in means if row["mode"] == "shortest")
    assert math.isnan(empty["drop_ratio"]) and math.isnan(empty["cv"])

    Path(path).unlink()
    print("self-check OK")


def main():
    args = build_parser(DEFAULT_INPUT).parse_args()
    if args.self_check:
        demo()
        return
    rows = read_results(args.input, args.duration)
    validate_unique(rows, panel_field="max_attempts", x_field="node_count")
    rows = average_over_seeds(rows, panel_field="max_attempts", x_field="node_count")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt = import_pyplot()
    apply_ieee_style(plt)
    specs = (
        ("cv", "Coefficient of variation (CV)",
         "Exp4: EDR Fairness vs. Topology Size", "08_fairness_vs_topology_size"),
        ("edr_per_request", "EDR per request (qubits/s)",
         "Exp4: Per-Request EDR vs. Topology Size",
         "09_edr_per_request_vs_topology_size"),
        ("drop_ratio", "Dropped-qubit ratio",
         "Exp4: Dropped-Qubit Ratio vs. Topology Size",
         "10_drop_ratio_vs_topology_size"),
        ("total_edr", "Total EDR (qubits/s)",
         "Exp4: Total EDR vs. Topology Size (load grows with n)",
         "11_edr_vs_topology_size"),
    )
    for y_field, ylabel, title, filename in specs:
        draw_panel_figure(plt, rows, y_field, ylabel, title,
                          output_dir / filename, args.formats, **PANEL_KWARGS)


if __name__ == "__main__":
    main()
