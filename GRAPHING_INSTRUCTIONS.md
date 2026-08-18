# Running the Simulations and Drawing All Four IEEE Graphs

This guide generates the complete historical Q-DDCA versus real-time
memory-aware Q-DDCA comparison used by `plot_comparison.py`.

The recommended workflow uses two paired sweeps:

- `w = 1, ..., 30` with `M = 10` for the sending-rate graphs.
- `M = 1, ..., 10` with `w = 30` for the attempt-count graphs.

The plotter merges the two CSV files. This produces all four graphs without
running the much larger Cartesian product of every `w` with every `M`.

By default, every parameter point is run for the 50 reproducible seeds `1`
through `50`. `exp4.py` writes every individual run to a `*_raw.csv` file,
then calculates the mean and population standard deviation across all 50 seeds
in the graph-ready CSV. The plotter reads only the graph-ready mean CSVs.

## 1. Open PowerShell in the project

```powershell
cd D:\QDDCA
```

## 2. Create the Python environment

If `.venv` already exists and the dependency check below succeeds, skip the
creation and installation commands.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install qns==0.2.3 numpy matplotlib
```

Verify the required packages:

```powershell
.venv\Scripts\python.exe -c "import qns, numpy, matplotlib; print('Dependencies are ready')"
```

## 3. Run the full sending-rate sweep

This creates the data for:

- Total EDR versus sending rate `w`.
- EDR coefficient of variation versus sending rate `w` (lower is fairer).

```powershell
.venv\Scripts\python.exe exp4.py --sweep send-rate
```

This runs `30 windows x 50 seeds x 2 algorithms = 3000` simulations and writes:

- `exp4_window_sweep_raw.csv`: all 3000 individual measurements.
- `exp4_window_sweep.csv`: 60 rows containing the 50-seed means and standard deviations.

## 4. Run the full attempt-count sweep

This creates the data for:

- Total EDR versus maximum attempts `M`.
- Dropped qubits versus maximum attempts `M`.

```powershell
.venv\Scripts\python.exe exp4.py --sweep attempts
```

This runs `10 attempt values x 50 seeds x 2 algorithms = 1000` simulations and
writes both `exp4_attempt_sweep_raw.csv` and the averaged
`exp4_attempt_sweep.csv`.

During either long sweep, `exp4.py` prints progress after each paired scenario
and rewrites the raw CSV as a checkpoint. If the process is interrupted, all
fully completed historical/real-time pairs up to the latest progress message
remain available in the raw file. The aggregate CSV is written only after all
50 seeds are complete for every parameter value.

Both algorithms use the same topology, request pairs, and seed for each paired
scenario. Do not change the seed list between the two sweeps if the figures are
intended for the same paper evaluation. Use `--seeds` only when intentionally
overriding the reproducible 50-seed default.

## 5. Draw all four IEEE figures

```powershell
.venv\Scripts\python.exe plot_comparison.py --input output\exp4\exp4_window_sweep.csv output\exp4\exp4_attempt_sweep.csv --output-dir output\exp4\plot --strict
```

`--strict` makes the command fail if either CSV is missing the data variation
needed for a graph. A successful run prints eight `Wrote` messages: one vector PDF
and one 600-dpi PNG for each graph.

## 6. Output files

### Measurement data

| Sweep | Individual seed data | 50-seed means used by plots |
| --- | --- | --- |
| Sending rate | `exp4_window_sweep_raw.csv` | `exp4_window_sweep.csv` |
| Attempts | `exp4_attempt_sweep_raw.csv` | `exp4_attempt_sweep.csv` |

The plot command must receive the mean files, not the `*_raw.csv` files.

### Figures

The following files are created under `output\exp4\plot\`:

| Graph | PDF for the paper | PNG preview |
| --- | --- | --- |
| EDR vs. sending rate | `01_edr_vs_send_rate.pdf` | `01_edr_vs_send_rate.png` |
| EDR vs. attempts | `02_edr_vs_attempts.pdf` | `02_edr_vs_attempts.png` |
| Dropped qubits vs. attempts | `03_dropped_vs_attempts.pdf` | `03_dropped_vs_attempts.png` |
| Fairness vs. sending rate | `04_fairness_vs_send_rate.pdf` | `04_fairness_vs_send_rate.png` |

Use the PDF files in IEEE LaTeX or Word submissions because they preserve
vector lines and embedded text. The PNG files are intended for previewing or
systems that cannot accept PDF figures.

## 7. Optional plotting controls

Generate additional vector formats:

```powershell
.venv\Scripts\python.exe plot_comparison.py --input output\exp4\exp4_window_sweep.csv output\exp4\exp4_attempt_sweep.csv --formats pdf,png,svg,eps
```

Generate double-column figures:

```powershell
.venv\Scripts\python.exe plot_comparison.py --input output\exp4\exp4_window_sweep.csv output\exp4\exp4_attempt_sweep.csv --column-width double
```

Show population-standard-deviation error bars:

```powershell
.venv\Scripts\python.exe plot_comparison.py --input output\exp4\exp4_window_sweep.csv output\exp4\exp4_attempt_sweep.csv --error-bars
```

The default has no error bars because it follows the figure pattern in
`output\pdf\real_time_memory_aware_qddca_math_fixed.pdf`.

Select different fixed slices when the CSV contains a larger parameter grid:

```powershell
.venv\Scripts\python.exe plot_comparison.py --input output\exp4\full_grid.csv --fixed-window 20 --fixed-attempts 5
```

## 8. Validate the project

Run the automated tests:

```powershell
.venv\Scripts\python.exe -m unittest discover
```

Check that the expected parameter values exist in the CSV files:

```powershell
Import-Csv output\exp4\exp4_window_sweep.csv | Select-Object -ExpandProperty window_size -Unique
Import-Csv output\exp4\exp4_attempt_sweep.csv | Select-Object -ExpandProperty send_max_try -Unique
```

The first command should list `1` through `30`; the second should list `1`
through `10`.

Confirm that every aggregate row is based on 50 seeds and that raw rows were
preserved:

```powershell
Import-Csv output\exp4\exp4_window_sweep.csv | Select-Object -ExpandProperty repetitions -Unique
(Import-Csv output\exp4\exp4_window_sweep_raw.csv).Count
(Import-Csv output\exp4\exp4_attempt_sweep_raw.csv).Count
```

The outputs should be `50`, `3000`, and `1000`, respectively.

## Troubleshooting

### `ModuleNotFoundError: No module named 'qns'`

Run the commands with `.venv\Scripts\python.exe`, or install `qns` into the
Python interpreter being used.

### `matplotlib is required for plotting`

```powershell
.venv\Scripts\python.exe -m pip install matplotlib
```

### Attempt graphs are skipped

The input has only one `send_max_try` value. Run the attempt-count sweep in
step 4 and pass both CSV files to `--input`.

### Sending-rate graphs have too few points

Run the complete `w = 1, ..., 30` command in step 3. A shorter CSV such as
`output\exp4\exp4.csv` may contain only selected windows and will therefore produce
a shorter curve.

### Reproduce the manuscript style

Use the default plotting options. They apply single-column IEEE dimensions,
Times-family typography, thin rules, hollow circles for historical Q-DDCA,
orange triangles for real-time memory-aware Q-DDCA, and no grid or error bars.
