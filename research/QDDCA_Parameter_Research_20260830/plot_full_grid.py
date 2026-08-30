"""Plot the three-objective Q-DDCA parameter surface."""

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


DIRECTORY = Path(__file__).resolve().parent


def load_grid():
    arrays = {
        "EDR (pairs/s)": np.full((10, 30), np.nan),
        "Dropped pairs, log(1+x)": np.full((10, 30), np.nan),
        "EDR CV": np.full((10, 30), np.nan),
    }
    with (DIRECTORY / "full_grid.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["algorithm"] != "real_time_memory_aware":
                continue
            w = int(row["window_size"]) - 1
            m = int(row["send_max_try"]) - 1
            arrays["EDR (pairs/s)"][m, w] = float(row["total_edr_pairs_s"])
            arrays["Dropped pairs, log(1+x)"][m, w] = np.log1p(float(row["mean_dropped_pairs"]))
            arrays["EDR CV"][m, w] = float(row["mean_edr_cv"])
    return arrays


def main():
    arrays = load_grid()
    analysis = json.loads((DIRECTORY / "full_grid_analysis.json").read_text(encoding="utf-8"))
    reachable = np.array(analysis["reachable_cells"])

    fig, axes = plt.subplots(3, 1, figsize=(8.2, 8.6), constrained_layout=True)
    cmaps = ("viridis", "magma", "cividis")
    for axis, (title, values), cmap in zip(axes, arrays.items(), cmaps):
        image = axis.imshow(values, origin="lower", aspect="auto", cmap=cmap,
                            extent=(0.5, 30.5, 0.5, 10.5))
        axis.scatter(reachable[:, 0], reachable[:, 1], marker="s", facecolors="none",
                     edgecolors="white", linewidths=0.8, s=28,
                     label="Aggregate-monotone reachable")
        axis.scatter([2], [3], marker="*", c="#00ff88", edgecolors="black", s=150,
                     linewidths=0.6, label="Exact endpoint: w=2, M=3")
        axis.scatter([3], [4], marker="D", c="#57c7ff", edgecolors="black", s=45,
                     linewidths=0.6, label="Practical point: w=3, M=4")
        axis.set_title(title, fontsize=10)
        axis.set_ylabel("Maximum attempts M")
        axis.set_xticks([1, 5, 10, 15, 20, 25, 30])
        axis.set_yticks(range(1, 11))
        fig.colorbar(image, ax=axis, shrink=0.9)
    axes[-1].set_xlabel("Sending window w")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, fontsize=8)
    fig.suptitle("Real-time memory-aware Q-DDCA: full parameter grid", fontsize=12)
    fig.savefig(DIRECTORY / "full_grid_tradeoffs.png", dpi=220, bbox_inches="tight")
    fig.savefig(DIRECTORY / "full_grid_tradeoffs.pdf", bbox_inches="tight")


if __name__ == "__main__":
    main()
