# Threshold Sensitivity: Solo Runs

> For the full paper-artifact workflow, see [Paper Artifact Workflow](../PAPER_ARTIFACT_WORKFLOW.md).

The solo workflow runs each workload alone, waits for time-to-first-kernel (TTFK), and records GPU metric summaries for several post-TTFK windows from the same workload execution.

## Default summary windows

The manifest runner uses these windows by default:

```text
5,10,20,30,40,60,120,200
```

The main AEGIS decision window remains:

```text
30 seconds
```

So each workload is executed once, and the output row includes metrics for all requested summary windows.

## Dry run a manifest

Use dry-run first to check the generated commands without launching workloads:

```bash
python evaluation/threshold_sensitivity/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --limit 2 \
  --dry-run
```

This creates a suite directory under:

```text
evaluation/threshold_sensitivity/solo_runs/
```

and writes:

```text
metadata.json
commands.jsonl
```

No workload is launched in dry-run mode.

## Run one workload from a manifest

Use this as the first real smoke test when a GPU is free:

```bash
python evaluation/threshold_sensitivity/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --limit 1
```

## Run all 1-GPU solo workloads

```bash
python evaluation/threshold_sensitivity/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0
```

## Override summary windows

```bash
python evaluation/threshold_sensitivity/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --summary-windows 10,20,30,60,120,200
```

The decision window can also be changed:

```bash
python evaluation/threshold_sensitivity/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --window-seconds 60 \
  --summary-windows 10,20,30,60,120,200
```

## Output files

Each suite writes:

```text
index.csv
live_threshold_measurements.csv
commands.jsonl
metadata.json
events/*.jsonl
```

### `index.csv`

One row per attempted run, including failures.

Useful columns:

```text
runner_status
workload_status
failure_stage
failure_reason
measurement_recorded
return_code
summary_windows_requested
summary_windows_collected
```

### `live_threshold_measurements.csv`

One row per successful measurement.

Important runtime columns:

```text
total_runtime_seconds
ttfk_wait_seconds
time_from_ttfk_to_window_ready_seconds
time_from_window_ready_to_finish_seconds
```

Important decision-window metric columns:

```text
smact_mean
smact_median
smact_p95
smact_ewma
smact_risk

smocc_mean
smocc_median
smocc_p95
smocc_ewma
smocc_risk

drama_mean
drama_median
drama_p95
drama_ewma
drama_risk
```

These unsuffixed columns correspond to `--window-seconds`.

Additional summary-window columns are suffixed:

```text
smact_risk_w5s
smact_risk_w10s
smact_risk_w20s
smact_risk_w30s
smact_risk_w40s
smact_risk_w60s
smact_risk_w120s
smact_risk_w200s
```

The same suffix pattern applies to `smocc_*`, `drama_*`, memory, and window metadata columns.

## Inspect a completed suite

Replace `<suite-dir>` with the printed suite directory:

```bash
python - <<'PY'
import pandas as pd
from pathlib import Path

suite = Path("<suite-dir>")
index = pd.read_csv(suite / "index.csv")
print(index[[
    "runner_status",
    "workload_status",
    "failure_stage",
    "return_code",
    "measurement_recorded",
    "summary_windows_collected",
]])

measurements_path = suite / "live_threshold_measurements.csv"
if measurements_path.exists():
    df = pd.read_csv(measurements_path)
    cols = [
        "finish_status",
        "return_code",
        "window_seconds",
        "summary_windows_collected",
        "smact_risk",
        "smact_risk_w5s",
        "smact_risk_w10s",
        "smact_risk_w20s",
        "smact_risk_w30s",
        "smact_risk_w40s",
        "smact_risk_w60s",
        "smact_risk_w120s",
        "smact_risk_w200s",
    ]
    print(df[[c for c in cols if c in df.columns]])
PY
```

## Run with screen

For long solo campaigns, use `screen` so the run continues after disconnecting:

```bash
screen -S solo-1gpu
```

Inside the screen session:

```bash
cd /home/ehyo/AEGIS

python evaluation/threshold_sensitivity/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --suite-id solo_1gpu_threshold_windows_$(date +%Y%m%d_%H%M%S) \
  2>&1 | tee evaluation/threshold_sensitivity/solo_1gpu_threshold_windows.log
```

Detach:

```bash
Ctrl-a d
```

Reattach:

```bash
screen -r solo-1gpu
```

### Inspect partial results while a run is still active
Set the latest suite directory:

```bash
export SUITE=$(ls -td evaluation/threshold_sensitivity/solo_runs/solo_1gpu_threshold_windows_* | head -1)
echo "$SUITE"
```

Check run status:

```bash
python - <<'PY'
import os
import pandas as pd

suite = os.environ["SUITE"]
index = pd.read_csv(f"{suite}/index.csv")

print("attempted runs:", len(index))
print(index["runner_status"].value_counts(dropna=False))
print(index["workload_status"].value_counts(dropna=False))

cols = [
    "task_path",
    "runner_status",
    "workload_status",
    "failure_stage",
    "failure_reason",
    "return_code",
    "measurement_recorded",
]
print(index[[c for c in cols if c in index.columns]].tail(10))
PY
```

Run window analysis on partial results:

```bash
export SUITE=$(ls -td evaluation/threshold_sensitivity/solo_runs/solo_1gpu_threshold_windows_* | head -1)
echo "$SUITE"

python evaluation/threshold_sensitivity/summarize_solo_windows.py \
  --analysis-dir "$SUITE/window_analysis_partial" \
  --measurements-csv "$SUITE/live_threshold_measurements.csv" \
  --output-md evaluation/threshold_sensitivity/summaries/window_analysis_summary_partial.md \
  --reference-window 200 \
  --decision-window 30
```

Inspect the partial stability summary:

```bash
cat "$SUITE/window_analysis_partial/window_stability_summary.csv"
```



## Notes

- Start with `all_specs_1gpu.txt`.
- The current solo runner selects one GPU for each run.
- Use `--dry-run` before long campaigns.
- Failed runs are kept in `index.csv`; do not delete them from the dataset.
- The default windows are intended for window-sensitivity analysis. The final paper should select the decision window based on the collected data.



## Analyze window stability

After a solo suite finishes, run the window-stability analyzer on its measurement CSV:

```bash
python evaluation/threshold_sensitivity/analyze_solo_windows.py \
  --measurements-csv <suite-dir>/live_threshold_measurements.csv \
  --output-dir <suite-dir>/window_analysis \
  --reference-window 200
```

This writes:

```text
<suite-dir>/window_analysis/window_metrics_long.csv
<suite-dir>/window_analysis/window_stability_summary.csv
```

### `window_metrics_long.csv`

This file converts the wide per-run metric columns into long format.

Example wide columns:

```text
smact_risk_w5s
smact_risk_w10s
smact_risk_w30s
smact_risk_w200s
```

become rows like:

```text
run_id, task_path, summary_window_seconds, metric, value
```

This format is easier to group, filter, and plot.

### `window_stability_summary.csv`

This file compares each shorter window against the reference window, usually 200 seconds.

Important columns:

```text
metric
summary_window_seconds
reference_window_seconds
n
mean_abs_error
median_abs_error
p95_abs_error
mean_abs_relative_error
```

Use this output to check whether the 30-second decision window is close enough to the 200-second reference window, or whether another window is more stable.

Example question this file helps answer:

```text
Is smact_risk_w30s close enough to smact_risk_w200s across workloads?
```


## Generate a Markdown window-analysis summary

After running `analyze_solo_windows.py`, generate a compact Markdown summary:

```bash
python evaluation/threshold_sensitivity/summarize_solo_windows.py \
  --analysis-dir <suite-dir>/window_analysis \
  --measurements-csv <suite-dir>/live_threshold_measurements.csv \
  --output-md evaluation/threshold_sensitivity/summaries/window_analysis_summary_1gpu.md \
  --reference-window 200 \
  --decision-window 30
  ```

  For partial results while a run is still active:

  ```bash
python evaluation/threshold_sensitivity/summarize_solo_windows.py \
  --analysis-dir <suite-dir>/window_analysis_partial \
  --measurements-csv <suite-dir>/live_threshold_measurements.csv \
  --output-md evaluation/threshold_sensitivity/summaries/window_analysis_summary_partial.md \
  --reference-window 200 \
  --decision-window 30
  ```



  ```bash
  python evaluation/threshold_sensitivity/generate_analysis_artifacts.py \
  --suite-dir "$SUITE" \
  --analysis-name window_analysis \
  --summary-prefix window_analysis_summary_1gpu \
  --figure-prefix profile_threshold_insights_1gpu \
  --decision-windows 30,40,60,120 \
  --reference-window 200
  ```