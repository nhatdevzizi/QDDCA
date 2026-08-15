"""Plot the exp6.py epsilon sweep, in the same style as the alpha sweep.

Everything is reused from plot_exp5.py; only the sweep-specific labels and the
baseline value differ. The baseline here is epsilon = 0.5, the constant the
estimator has always used, so the shaded area is what changing epsilon buys or
costs against the current implementation.
"""

from plot_exp5 import PlotSpec, run_cli


EPSILON = PlotSpec(
    column="epsilon",
    delta_col="delta_edr_vs_prev_epsilon",
    baseline=0.5,
    symbol=r"\epsilon",
    axis_label=r"Smoothing constant $\epsilon$",
    baseline_label=r"Q-DDCA ($\epsilon=0.5$)",
    swept_label=r"Q-DDCA ($\epsilon$ swept)",
    title_noun=r"Smoothing Constant $\epsilon$",
    captions=(
        r"\caption{Total EDR as the smoothing constant $\epsilon$ of "
        r"$q_v^{hist}=(A_v+\epsilon)/(T_v+\epsilon)$ is swept, with the history "
        r"weight held at $\alpha=1$ so that $\epsilon$ acts undiluted. The "
        r"baseline is the $\epsilon=0.5$ value the estimator has always used. "
        r"All $\epsilon$ run on the same seeded topologies, so the curves are "
        r"paired.}",
        r"\caption{Dropped qubits over the same sweep; lower is better. The "
        r"minimum sits at $\epsilon=DROPMIN$.}",
        r"\caption{Difference in total EDR. (a) Each $\epsilon$ against the "
        r"$\epsilon=0.5$ baseline. (b) Each $STEP$ step against the previous "
        r"$\epsilon$; the hatched bar is the largest single step, $PEAKSTEP$.}",
    ),
)


if __name__ == "__main__":
    run_cli(EPSILON, "output/exp6/exp6_epsilon_sweep.csv", "output/exp6/plot", "exp6")
