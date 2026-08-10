"""Display an exp1/exp2 result CSV as pivot tables, or plot it.

    python3 show.py                      # tables; defaults to output/exp2-7.1.csv (exp1's output)
    python3 show.py output/exp1-4.csv
    python3 show.py --plot               # writes a PNG next to the CSV
"""
import sys
import pandas as pd

# The trailing field of each row is a list/Counter repr containing commas, so
# rows are split with a fixed maxsplit rather than parsed as real CSV.
EXP1 = ["w", "m", "mode", "sent", "dropped", "std", "cv", "ans_list"]
EXP2 = ["w", "m", "mode", "sent", "dropped", "paths", "routes"]
ARMS = ["shortest", "reactive", "predictive"]
LABEL = {"shortest": "SPA", "reactive": "Q-DDCA", "predictive": "Predictive Q-DDCA"}
STYLE = {"shortest": (":", "x"), "reactive": ("-", "s"), "predictive": ("-", "^")}
SIM_SEC = 10  # Simulator(0, 10, 1000) in exp1/exp2 -> sent qubits / 10s = EDR


def load(path):
    lines = [l.rstrip("\n") for l in open(path) if l.strip()]
    cols = EXP2 if '"Counter(' in lines[0] else EXP1
    df = pd.DataFrame([l.split(",", len(cols) - 1) for l in lines], columns=cols)
    for c in ("w", "m", "sent", "dropped", "std", "cv", "paths"):
        if c in df:
            df[c] = pd.to_numeric(df[c])
    return df


def table(g, x, metric):
    """One metric pivoted as x-vs-arm, plus predictive's gain over reactive."""
    p = g.pivot(index=x, columns="mode", values=metric)
    p = p[[a for a in ARMS if a in p]]
    if {"predictive", "reactive"} <= set(p.columns):
        p["gain%"] = (p["predictive"] / p["reactive"].replace(0, pd.NA) - 1) * 100
    return p.to_string(float_format=lambda v: f"{v:.4g}", na_rep="-")


def plot(df, key, x, path):
    """Two panels: throughput as EDR, and the fairness/diversity metric beside it."""
    import matplotlib
    matplotlib.use("Agg")  # ponytail: write a PNG, no display server needed
    import matplotlib.pyplot as plt

    df = df.assign(edr=df["sent"] / SIM_SEC)
    right = "cv" if "cv" in df else "paths"
    keys = sorted(df[key].unique())
    cmap = plt.get_cmap("tab10")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    for ax, metric, ylabel in ((axes[0], "edr", "Total EDR (qubit/s)"),
                               (axes[1], right, {"cv": "CV (Coefficient of Variation)",
                                                 "paths": "Distinct paths used"}[right])):
        for i, kv in enumerate(keys):
            for arm in ARMS:
                g = df[(df[key] == kv) & (df["mode"] == arm)].sort_values(x)
                if g.empty:
                    continue
                ls, mk = STYLE[arm]
                ax.plot(g[x], g[metric], ls, marker=mk, markersize=4, color=cmap(i),
                        label=f"{LABEL[arm]}, {key.upper()}={kv}")
        ax.set_xlabel(f"Send Rate ({x})" if x == "w" else f"Max retries ({x})")
        ax.set_ylabel(ylabel)
        ax.set_title(f"{ylabel.split(' (')[0]} vs {x}")
        ax.grid(True, ls=":", alpha=0.5)

    # One shared legend under both panels: 9 series inside an axes covers the curves.
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center",
               ncol=len(keys), fontsize=8)
    out = path.rsplit(".", 1)[0] + ".png"
    fig.tight_layout(rect=(0, 0.18, 1, 1))
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


def main(path, do_plot):
    df = load(path)
    # exp1 sweeps w inside each m; exp2 sweeps m inside each w.
    key, x = ("m", "w") if "cv" in df else ("w", "m")

    if do_plot:
        plot(df, key, x, path)
        return

    print(f"{path}  ({len(df)} runs, arms: {', '.join(df['mode'].unique())})")
    for kv, g in df.groupby(key):
        for metric in [c for c in ("sent", "dropped", "cv", "paths") if c in df]:
            print(f"\n=== {key}={kv} :: {metric} vs {x} ===")
            print(table(g, x, metric))

    print("\n=== totals ===")
    t = df.groupby("mode")[[c for c in ("sent", "dropped") if c in df]].sum()
    t["drop%"] = t["dropped"] / (t["sent"] + t["dropped"]) * 100
    print(t.reindex([a for a in ARMS if a in t.index]).to_string(float_format=lambda v: f"{v:.4g}"))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--plot"]
    main(args[0] if args else "output/exp2-7.1.csv", "--plot" in sys.argv)
