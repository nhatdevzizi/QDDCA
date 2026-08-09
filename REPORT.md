# Real-time Congestion Estimation: Results Report

## Objective

This experiment measures the incremental effect of replacing Q-DDCA's
historical-only neighbor acceptance estimate with the real-time memory-aware
estimate:

```text
q_hat = alpha * q_history + (1 - alpha) * (1 - memory_utilization)
```

The baseline uses `alpha = 1.0`, so routing depends only on historical query
outcomes. The improved version uses `alpha = 0.5`, giving equal weight to
historical acceptance and current free-memory ratio. Both versions retain
Q-DDCA rerouting; this is not a comparison against shortest-path routing.

## Method

`exp4.py` follows the simulation settings used by the existing experiment
scripts and the main paper: 50 random-topology nodes, edge probability 0.1,
five concurrent requests, ten memories per node, `M = 10`, 50 ms query time,
1000 pairs/s link rate, and a 10-second run. Window sizes are 5, 10, 15, 20,
25, and 30. Each point is the mean of seeds 101, 202, and 303.

The comparison is paired. For each seed and window size, the random generator
is reset before each algorithm, and the experiment verifies that both receive
the same topology and source-destination request pairs. The reported metrics
are:

- Mean request throughput: successful end-to-end pairs per second, averaged
  across the five requests.
- Total EDR: the sum of the five request throughputs.
- Dropped pairs: mean number of pairs dropped during the 10-second run.
- Standard deviation: population standard deviation across the three seeds.

## Results

| Window per hop | Historical EDR (pairs/s) | Real-time EDR (pairs/s) | EDR change | Historical drops | Real-time drops | Drop change |
|---:|---:|---:|---:|---:|---:|---:|
| 5  | 431.50 | 430.67 | -0.19% | 14.67 | 14.00 | -4.55% |
| 10 | 520.40 | 571.97 | +9.91% | 265.33 | 199.33 | -24.87% |
| 15 | 544.30 | 578.67 | +6.31% | 1,026.33 | 593.67 | -42.16% |
| 20 | 517.20 | 566.13 | +9.46% | 2,181.67 | 1,422.33 | -34.81% |
| 25 | 489.87 | 557.27 | +13.76% | 3,082.67 | 2,363.00 | -23.35% |
| 30 | 483.97 | 527.87 | +9.07% | 3,895.33 | 3,553.67 | -8.77% |

Across windows 10-30, where congestion is visible in the rising drop counts,
mean total EDR increases from 511.15 to 560.38 pairs/s, a 9.63% improvement.
Across the high-load windows 20-30, the average gain is 10.75%. The largest
relative increase occurs at window 25: +67.40 pairs/s or +13.76%, accompanied
by 719.67 fewer dropped pairs per run.

At window 5, the EDR difference is -0.19%, smaller than the between-seed
standard deviations (45.11 pairs/s for historical-only and 42.47 pairs/s for
real-time). This is effectively a neutral result: when memory pressure is low,
the live-memory signal has little useful congestion information to add.

The best observed total EDR is 578.67 pairs/s at window 15 for the real-time
estimator, compared with 544.30 pairs/s for historical-only Q-DDCA. EDR then
declines as the window grows, even with the improvement. Real-time state helps
choose less-congested neighbors, but it cannot remove network-wide overload.

Mean request throughput shows the same percentage changes as total EDR because
the experiment uses a fixed five-request count and total EDR is defined as the
sum of request throughputs.

## Comparison with the Paper

The paper reports the same qualitative congestion pattern. At low window
sizes, routing algorithms have similar EDR. As the window grows, congestion
causes shortest-path routing to saturate and drop more pairs, while Q-DDCA's
congestion-aware rerouting preserves higher EDR. In the paper's single-request
experiment at `M = 10`, `w = 30`, Q-DDCA reaches 329.5 pairs/s versus 191.4
pairs/s for SPA, a 72.15% gain. In the five-request experiment, Q-DDCA peaks
near `w = 12`; at that point it exceeds SPA by 62.42% for `M = 10`, then total
EDR falls under larger network-wide load.

The present experiment extends that result rather than reproducing the same
comparison. Both sides already use Q-DDCA rerouting. The only changed factor is
whether the acceptance estimate includes current memory utilization. Its
6.31%-13.76% gain across congested windows is therefore an incremental benefit
on top of the paper's congestion-aware algorithm, and is expected to be smaller
than the paper's full Q-DDCA-versus-SPA improvement.

The observed mechanism is also consistent with the paper: higher EDR appears
alongside fewer drops. The real-time signal reacts immediately when a neighbor
fills, while the historical-only estimate continues to favor that neighbor
until enough failed queries enter its history.

## Interpretation and Limitations

The results support three conclusions:

1. Real-time memory utilization is useful once the network begins to congest.
2. It improves efficiency rather than eliminating overload; EDR still falls at
   the largest windows.
3. A fixed 50/50 weight is not universally optimal. The neutral window-5 result
   motivates tuning `alpha` by load or making it adaptive.

The experiment uses only three seeds, so its standard deviations describe
replicate spread but do not establish statistical significance. It also uses
ten memories per node, while the paper's single-request experiment describes
20 memories per node. Absolute EDR values should therefore not be compared
directly with the paper. A stronger evaluation should add more paired seeds,
confidence intervals, an alpha sweep, and the paper's SPA baseline.

## Reproduction and Graphing

Run:

```bash
python exp4.py
```

The output is `output/exp4.csv`. For an EDR graph, use `window_size` on the
x-axis, `total_edr_pairs_s` on the y-axis, and `algorithm` as the series. Use
`edr_std_pairs_s` for error bars. For a per-request throughput graph, substitute
`mean_request_throughput_pairs_s` and `throughput_std_pairs_s`.

## Sources

- Chen, L. et al., "Q-DDCA: Decentralized Dynamic Congestion Avoid Routing in
  Large-Scale Quantum Networks," IEEE/ACM Transactions on Networking, 2024.
  https://doi.org/10.1109/TNET.2023.3285093
- Experiment data: `output/exp4.csv`.
