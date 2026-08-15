# Four-Graph Q-DDCA Comparison Report

Date: August 14, 2026

## 1. Objective

The objective was to run a reproducible comparison between:

- Historical Q-DDCA, using only historical congestion information
  (`congestion_history_weight = 1.0`).
- Real-time memory-aware Q-DDCA, combining historical information and current
  memory availability (`congestion_history_weight = 0.5`).

The experiment generated the data and IEEE-style figures for these four
scenarios:

1. Total EDR versus sending rate/window size `w`.
2. Total EDR versus maximum attempts `M`.
3. Dropped qubits versus maximum attempts `M`.
4. Jain resource-allocation fairness versus sending rate/window size `w`.

## 2. Experimental design

Two targeted sweeps were used instead of a full 30-by-10 Cartesian grid. The
targeted design supplies every point required by the four figures while avoiding
unnecessary simulations.

| Sweep | Variable | Fixed value | Values | Aggregate rows |
| --- | --- | --- | --- | ---: |
| Sending rate | `w` | `M = 10` | `1, ..., 30` | 60 |
| Attempt count | `M` | `w = 30` | `1, ..., 10` | 20 |

Each parameter value contains two aggregate rows, one for each algorithm. Each
row is the mean of the three paired seeds `101`, `202`, and `303`.

### Fixed simulation parameters

| Parameter | Value |
| --- | --- |
| Simulator | SimQN (`qns` 0.2.3) |
| Simulation duration | 10 s |
| Simulator accuracy | 1000 |
| Nodes | 50 |
| Independent edge probability | 0.1 |
| Concurrent requests | 5 |
| Memories per node | 10 |
| Query interval | 0.05 s |
| Link generation rate | 1000 pairs/s |
| Link delay | 0.001 s |
| Link buffer | 1 |
| Rerouting | Enabled for both algorithms |

The random generator is reset for each paired algorithm run. `exp4.py` verifies
that both versions receive identical topology signatures and source-destination
request pairs before accepting a result.

## 3. Commands executed

### 3.1 Sending-rate sweep

```powershell
.venv\Scripts\python.exe exp4.py --windows 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30 --send-max-try 10 --seeds 101,202,303 --output output\exp4_window_sweep.csv
```

The run executed 180 simulations:

```text
30 window values x 3 seeds x 2 algorithms = 180 simulations
```

It completed successfully and wrote 60 aggregate rows to
`output\exp4_window_sweep.csv`.

### 3.2 Attempt-count sweep

```powershell
.venv\Scripts\python.exe exp4.py --windows 30 --attempts 1,2,3,4,5,6,7,8,9,10 --seeds 101,202,303 --output output\exp4_attempt_sweep.csv
```

The run executed 60 simulations:

```text
10 attempt values x 3 seeds x 2 algorithms = 60 simulations
```

It completed successfully and wrote 20 aggregate rows to
`output\exp4_attempt_sweep.csv`.

### 3.3 Figure generation

```powershell
.venv\Scripts\python.exe plot_comparison.py --input output\exp4_window_sweep.csv output\exp4_attempt_sweep.csv --output-dir output\graphs\ieee --strict
```

The plotter merged the files using `(window_size, send_max_try, algorithm)` as
the unique key. `--strict` verified that both algorithms and at least two
distinct x-axis values were available for every graph.

## 4. Code modifications and reasons

### 4.1 `exp4.py`

The paired comparison experiment was extended in the following ways.

| Modification | Reason |
| --- | --- |
| Added the `--attempts` comma-separated sweep argument | The original experiment varied only `w`, so it could not produce EDR-versus-`M` or drops-versus-`M` figures. |
| Passed `send_max_try` into each simulation run | Each attempt-sweep point must configure its own maximum retry count instead of reusing one global value. |
| Aggregated results by both `window_size` and `send_max_try` | This preserves the parameter identity of every plotted point and supports targeted or full-grid experiments. |
| Added `jain_fairness()` | The requested resource-allocation fairness graph requires a bounded fairness metric computed from per-request completed allocations. |
| Exported `mean_fairness_index` and `fairness_std` | The graphing stage needs the mean and across-seed spread without rerunning or reconstructing request-level data. |
| Preserved paired topology/request validation | Algorithm differences should come from the congestion estimator, not from different random networks or request pairs. |
| Preserved `--send-max-try 10` as the default | Existing commands and the manuscript's `M = 10` sending-rate experiment remain backward compatible. |

Jain fairness is calculated for the completed allocations `x_i` of the five
requests:

```text
J = (sum(x_i))^2 / (n * sum(x_i^2))
```

It ranges from 0 to 1, with larger values indicating a more even allocation.
An all-zero allocation is reported as 0 because no useful resource was
allocated.

### 4.2 `plot_comparison.py`

A dedicated graphing program was created because the original project exported
CSV measurements but did not provide a reusable publication plotting workflow.

| Modification | Reason |
| --- | --- |
| Reads the stable `exp4.py` CSV schema | Figures use measured output rather than hard-coded or manually copied values. |
| Accepts and merges multiple CSV files | The efficient `w` and `M` sweeps can be run separately and combined without a large Cartesian experiment. |
| Validates required columns and both algorithms | Missing or incompatible data fails early with an actionable message. |
| Rejects/skips single-point x-axis series | A single `M = 10` point is not a meaningful attempt-count curve. |
| Selects fixed `M` and fixed `w` slices | Sending-rate figures use one attempt budget, while attempt figures use one sending rate. |
| Added four explicit graph specifications | File names, axes, units, and metrics remain consistent between runs. |
| Added IEEE single-column and double-column sizes | Figures can be inserted into one- or two-column paper layouts without manual resizing. |
| Added Times-family fonts, thin strokes, hollow circles, orange triangles, and no grid | This matches the visual pattern in `real_time_memory_aware_qddca_math_fixed.pdf` and remains distinguishable in grayscale. |
| Exports vector PDF and 600-dpi PNG by default | PDF is suitable for the paper; PNG supports preview and systems that require raster images. |
| Added optional SVG/EPS and error bars | Alternate publisher formats and variability visualization can be enabled without changing code. |
| Embedded TrueType text in PDF output | Text and mathematical labels remain sharp and portable in the manuscript. |

No error bars were drawn in the delivered figures because the supplied paper
pattern plots the three-seed means as clean lines. The CSV retains population
standard deviations, and `--error-bars` can display them.

### 4.3 Tests and documentation

| File | Modification and reason |
| --- | --- |
| `test_exp4.py` | Added Jain fairness checks and confirmed the expanded CSV schema remains stable. |
| `test_plot_comparison.py` | Added CSV parsing, two-version slice, format parsing, variation, and multi-file deduplication tests. |
| `GRAPHING_INSTRUCTIONS.md` | Added complete copy-paste instructions for environment setup, both sweeps, plotting, validation, and troubleshooting. |
| `README.md` | Linked the complete graph guide and summarized the attempt sweep, fairness export, and IEEE output behavior. |

## 5. Generated data and figures

### Data

- `output\exp4_window_sweep.csv`: 60 aggregate rows covering `w = 1, ..., 30`
  at `M = 10`.
- `output\exp4_attempt_sweep.csv`: 20 aggregate rows covering `M = 1, ..., 10`
  at `w = 30`.

### IEEE figures

Each graph has a vector PDF and a 600-dpi PNG under
`output\graphs\ieee\`:

1. `01_edr_vs_send_rate.pdf` and `.png`
2. `02_edr_vs_attempts.pdf` and `.png`
3. `03_dropped_vs_attempts.pdf` and `.png`
4. `04_fairness_vs_send_rate.pdf` and `.png`

## 6. Results summary

### 6.1 Sending-rate sweep (`w = 1, ..., 30`, `M = 10`)

| Range | Historical mean EDR | Real-time mean EDR | EDR change | Historical mean drops | Real-time mean drops | Drop reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `w = 1..5` | 274.653 | 275.893 | +0.451% | 3.000 | 2.800 | 6.667% |
| `w = 10..30` | 516.038 | 563.505 | +9.198% | 2049.032 | 1561.635 | 23.787% |
| `w = 20..30` | 493.370 | 552.673 | +12.020% | 3079.152 | 2424.909 | 21.247% |

Across all 30 sending rates:

- Historical mean total EDR: 469.991 qubits/s.
- Real-time mean total EDR: 508.068 qubits/s.
- Historical mean dropped qubits: 1458.989.
- Real-time mean dropped qubits: 1106.844.
- Historical mean Jain fairness: 0.8660.
- Real-time mean Jain fairness: 0.8678.
- Historical peak EDR: 559.500 qubits/s at `w = 16`.
- Real-time peak EDR: 583.600 qubits/s at `w = 12`.

At `w = 30`, real-time memory-aware Q-DDCA increased EDR from 483.967 to
527.867 qubits/s and reduced mean drops from 3895.333 to 3553.667.

### 6.2 Attempt-count sweep (`M = 1, ..., 10`, `w = 30`)

Across the ten attempt budgets:

- Historical mean total EDR: 482.677 qubits/s.
- Real-time mean total EDR: 522.620 qubits/s.
- Historical mean dropped qubits: 13469.367.
- Real-time mean dropped qubits: 12293.967.
- Historical peak EDR: 517.133 qubits/s at `M = 2`.
- Real-time peak EDR: 535.800 qubits/s at `M = 4`.

The mean paired EDR improvement over the ten `M` values was 8.291%. The mean
paired drop reduction was 12.129%. Both algorithms dropped far fewer qubits as
the retry budget increased, which is visible in the fourth figure.

## 7. Interpretation

At low sending rates, current memory availability adds little discrimination
because the network is not strongly congested; both algorithms therefore have
nearly identical EDR. The benefit becomes clear once larger sending windows
create memory pressure. The real-time estimator can penalize a currently full
neighbor before enough rejection history accumulates, producing higher EDR and
fewer exhausted retries in the congested region.

The attempt sweep shows that increasing `M` sharply reduces drops for both
versions. Real-time memory-aware Q-DDCA remains above the historical baseline
in EDR across the measured attempt budgets, but EDR is not monotonic in `M`.
More attempts reduce premature drops while also allowing a qubit to spend more
time retrying a congested route, so the best measured EDR does not necessarily
occur at the largest retry budget. The algorithms tie at `M = 1`; real-time
memory-aware Q-DDCA has higher EDR for every measured value from `M = 2` through
`M = 10`.

Fairness remains close between the algorithms. The real-time estimator improves
aggregate throughput and congestion behavior, but the current experiment does
not demonstrate a large systematic fairness improvement.

## 8. Verification performed

- Confirmed `.venv` contains `qns` 0.2.3, NumPy 2.5.2, and Matplotlib 3.11.1.
- Confirmed 60 sending-rate rows with `w = 1, ..., 30`.
- Confirmed 20 attempt rows with `M = 1, ..., 10`.
- Generated all four PDF and all four PNG figures with `--strict` enabled.
- Ran the complete automated test suite: 15 tests passed.
- Checked the Git diff for whitespace errors.
- Rendered every final PDF and visually checked axes, titles, legends, markers,
  typography, and clipping.

## 9. Limitations and reporting cautions

- Three paired seeds support a descriptive comparison but are insufficient for
  a strong statistical-significance claim.
- `M` changes while the per-query interval remains fixed at 0.05 s. The attempt
  graph therefore measures retry-budget behavior at a fixed query interval, not
  at a fixed total retry-time budget.
- The attempt graph is an extension experiment, not a reproduction of Fig. 4(c)
  in the original Q-DDCA paper. The paper uses one request, 20 memories per node,
  `queryTime = 0.5/M`, and compares SPA with Q-DDCA. This project graph uses five
  requests, 10 memories per node, fixed `queryTime = 0.05`, and compares
  historical-only Q-DDCA with real-time memory-aware Q-DDCA.
- The topology family, request count, memory size, link model, and real-time
  history weight are fixed. The conclusions should not be generalized beyond
  those settings without additional sweeps.
- The program operationally computes EDR as completed end-to-end entangled pairs
  divided by the 10 s duration. Figure labels use `qubits/s` to follow the
  requested graph notation; in the simulator this quantity is completed
  entangled pairs per second.
- Dropped-qubit values are mean counts per 10 s simulation, not rates.
- The fairness index measures equality of completed allocations, not fairness of
  memory occupancy, waiting time, or route access.
- The original paper reports fairness using coefficient of variation (CV), where
  lower is fairer. This extension uses Jain's index, where higher is fairer, so
  the numerical curves should not be compared directly.

## 10. Reproduction

The complete reusable command sequence and troubleshooting instructions are in
`GRAPHING_INSTRUCTIONS.md`.
