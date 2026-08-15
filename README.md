# Q-DDCA: Decentralized Dynamic Congestion  Avoid Routing in Large-Scale Quantum Networks

This is the minized prototype codes for implementing the Q-DDCA protocol. This code requires the [SimQN](https://github.com/QNLab-USTC/SimQN) Platform.

## How to Run

1. ``python3 exp1.py``
2. ``python3 exp2.py``
3. ``python3 exp3.py``
4. ``python3 exp4.py``

NOTE: They will create files to log the results.

## Details

run *exp1.py*, *exp2.py*, *exp3.py* or *exp4.py* for simulation, and modify the parameters to collect the complete set of results

- *exp1.py*

  Simulate the network's throughput, drop rate, and coefficient of variation in both single-request and multiple-request scenarios under different sending window sizes and specific maximum retry attempts.

- *exp2.py*

  Simulate the network's throughput and drop rate in a single-request scenario across different maximum retry attempts and multiple specific sending window sizes.

- *exp3.py*

  Simulate the memory occupancy of req1 and req2 at node u3 over time, under the given network topology.

- *exp4.py*

  Compare historical-only and real-time memory-aware Q-DDCA on paired random
  topologies, then export per-request throughput and total EDR for graphing.

## Real-time congestion estimation

When rerouting is enabled, Q-DDCA now scores each neighboring node with a
memory-aware acceptance estimate instead of relying only on past query results:

```text
q_hat = alpha * q_history + (1 - alpha) * (1 - memory_utilization)
```

`memory_utilization` is read when the route is selected, so a neighbor whose
memory suddenly fills is penalized immediately. Configure `alpha` with the
`Network(..., congestion_history_weight=0.5)` argument. A value of `1.0`
reproduces historical-only scoring; `0.0` uses only current memory availability.

For complete copy-paste commands that generate the paired CSV sweeps and all
four IEEE-ready figures, see [`GRAPHING_INSTRUCTIONS.md`](GRAPHING_INSTRUCTIONS.md).
The completed run, code-change rationale, measured results, and limitations are
documented in [`FULL_GRAPH_EXPERIMENT_REPORT.md`](FULL_GRAPH_EXPERIMENT_REPORT.md).

### Export throughput and EDR measurements

Run a paired baseline-versus-improved sweep and create graph-ready results:

```bash
python exp4.py --attempts 1,2,3,4,5,6,7,8,9,10
python plot_comparison.py
```

The default output is `output/exp4.csv`. Each
window size has two rows: historical-only Q-DDCA (`alpha=1.0`) and real-time
memory-aware Q-DDCA (`alpha=0.5`). Both use identical seeded topologies and
request pairs. `mean_request_throughput_pairs_s` is the average successful
distribution rate per request; `total_edr_pairs_s` is their sum, matching the
paper's definition of total network EDR. Standard deviations and percentage
changes versus the historical baseline are included for plotting and analysis,
along with all simulation parameters needed to reproduce the sweep. The optional
`--attempts` argument adds a maximum-attempt sweep while preserving the original
`--send-max-try 10` default when it is omitted. Fairness is exported as Jain's
fairness index over the completed qubits for each request.

`plot_comparison.py` writes IEEE single-column vector PDF and 600-dpi PNG
figures to `output/graphs/ieee/`:

1. EDR versus send rate/window size (`w`)
2. EDR versus maximum attempts (`M`)
3. Dropped qubits versus EDR
4. Dropped qubits versus maximum attempts (`M`)
5. Jain resource-allocation fairness versus send rate/window size (`w`)

The send-rate figures use the largest `M` in the CSV by default, and the
attempt-based figures use the largest `w`. Use `--fixed-attempts` and
`--fixed-window` to select different slices. Multiple CSVs can be merged at
plot time, for example:

```bash
python plot_comparison.py --input output/exp4.csv output/exp4_attempt_sweep.csv
```

The default style matches the supplied IEEE manuscript: Times-family text,
compact 3.5-inch width, thin rules, hollow circles for historical Q-DDCA,
orange triangles for real-time memory-aware Q-DDCA, no grid, and no error bars.
Use `--column-width double`, `--error-bars`, or `--formats pdf,png,svg,eps` when
needed. A graph is skipped when its CSV data has fewer than two distinct x-axis
values, avoiding misleading single-point attempt plots. Plotting requires
Matplotlib.

See `REPORT.md` for the comparison with the paper's published results and a
discussion of the measured effect.

## Note and Citation

- Please cite:"Chen L, Xue K, Li J, et al. Q-DDCA: Decentralized dynamic congestion avoid routing in large-scale quantum networks[J]. IEEE/ACM Transactions on Networking, 2023, 32(1): 368-381."[link](https://ieeexplore.ieee.org/abstract/document/10158747)
  
- Please add the following citation in your work if you use our open-source code.
```
@article{chen2023q,
  title={Q-DDCA: Decentralized dynamic congestion avoid routing in large-scale quantum networks},
  author={Chen, Lutong and Xue, Kaiping and Li, Jian and Li, Ruidong and Yu, Nenghai and Sun, Qibin and Lu, Jun},
  journal={IEEE/ACM Transactions on Networking},
  volume={32},
  number={1},
  pages={368--381},
  year={2023},
  publisher={IEEE}
}
```
