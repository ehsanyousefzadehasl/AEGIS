# Threshold Sensitivity: First-Observed-GPU-Activity Solo Runs

> For the full paper-artifact workflow, see [Paper Artifact Workflow](../PAPER_ARTIFACT_WORKFLOW.md).

This workflow runs each workload alone, waits until the target job is first observed as active on the GPU, and records GPU metric summaries for several post-activity windows from the same workload execution.

Older scripts and CSV columns may still use `ttfk` as an internal shorthand. In this artifact, `ttfk_wait_seconds` means the wait until first observed GPU activity, not an exact CUDA kernel-launch timestamp.

## Default summary windows

The manifest runner uses these windows by default:

```text
5,10,20,30,40,60,120,200
```

The current candidate decision windows used for paper figures are:

```text
30,40,60,120
```

The reference window is:

```text
200 seconds
```

Each workload is executed once, and the output row includes metrics for all requested summary windows.

## Dry run a manifest

Use dry-run first to check the generated commands without launching workloads:

```bash
python evaluation/threshold_sensitivity/runners/run_solo_baselines.py \
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
python evaluation/threshold_sensitivity/runners/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --limit 1
```

## Run all 1-GPU solo workloads

```bash
python evaluation/threshold_sensitivity/runners/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0
```

## Run with `screen`

For long solo campaigns, use `screen` so the run continues after disconnecting:

```bash
screen -S solo-1gpu
```

Inside the screen session:

```bash
cd /home/ehyo/AEGIS

python evaluation/threshold_sensitivity/runners/run_solo_baselines.py \
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

## Override summary windows

```bash
python evaluation/threshold_sensitivity/runners/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --summary-windows 10,20,30,60,120,200
```

The decision window can also be changed:

```bash
python evaluation/threshold_sensitivity/runners/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_1gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --window-seconds 60 \
  --summary-windows 10,20,30,60,120,200
```

For two-gpu workloads:

### Run 2-GPU threshold-window solo workloads

For multi-GPU workloads, `--gpu-id` selects the GPU used for monitoring and first-GPU-activity detection, while `--cuda-visible-devices` controls which GPUs are exposed to the workload.

```bash
python evaluation/threshold_sensitivity/runners/run_solo_baselines.py \
  --spec-list evaluation/profiling/solo/manifests/all_specs_2gpu.txt \
  --workdir . \
  --gpu-id 0 \
  --cuda-visible-devices 0,1 \
  --window-seconds 30 \
  --summary-windows 5,10,20,30,40,60,120,200 \
  --suite-id solo_2gpu_threshold_windows_$(date +%Y%m%d_%H%M%S)
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

The `ttfk_*` names are legacy/internal names. Interpret them as first-observed-GPU-activity timing fields.

Important metric columns:

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

## Inspect a completed or running suite

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

Inspect measurement rows:

```bash
python - <<'PY'
import os
import pandas as pd

suite = os.environ["SUITE"]
measurements_path = f"{suite}/live_threshold_measurements.csv"
df = pd.read_csv(measurements_path)

cols = [
    "finish_status",
    "return_code",
    "window_seconds",
    "summary_windows_collected",
    "smact_risk",
    "smact_risk_w30s",
    "smact_risk_w40s",
    "smact_risk_w60s",
    "smact_risk_w120s",
    "smact_risk_w200s",
]
print(df[[c for c in cols if c in df.columns]].tail(20))
PY
```

## Analyze window stability

After a suite finishes, run the window-stability analyzer:

```bash
python evaluation/threshold_sensitivity/analyze_solo_windows.py \
  --measurements-csv "$SUITE/live_threshold_measurements.csv" \
  --output-dir "$SUITE/window_analysis" \
  --reference-window 200
```

This writes:

```text
$SUITE/window_analysis/window_metrics_long.csv
$SUITE/window_analysis/window_stability_summary.csv
$SUITE/window_analysis/risk_component_stability.csv
$SUITE/window_analysis/risk_component_stability_rollup.csv
```

### `window_metrics_long.csv`

This file converts wide per-run metric columns into long format.

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

## Generate final Markdown summaries

Generate final summaries for the decision-window candidates:

```bash
for W in 30 40 60 120; do
  python evaluation/threshold_sensitivity/summarize_solo_windows.py \
    --analysis-dir "$SUITE/window_analysis" \
    --measurements-csv "$SUITE/live_threshold_measurements.csv" \
    --output-md "evaluation/threshold_sensitivity/summaries/window_analysis_summary_1gpu_w${W}s_vs_w200s.md" \
    --reference-window 200 \
    --decision-window "$W"
done
```

This writes:

```text
evaluation/threshold_sensitivity/summaries/window_analysis_summary_1gpu_w30s_vs_w200s.md
evaluation/threshold_sensitivity/summaries/window_analysis_summary_1gpu_w40s_vs_w200s.md
evaluation/threshold_sensitivity/summaries/window_analysis_summary_1gpu_w60s_vs_w200s.md
evaluation/threshold_sensitivity/summaries/window_analysis_summary_1gpu_w120s_vs_w200s.md
```

## Generate clean threshold-window figures

Generate first-observed-GPU-activity threshold figures in separate folders:

```bash
for W in 30 40 60 120; do
  python evaluation/runners/plot_profile_and_threshold_insights.py \
    --window-stability "$SUITE/window_analysis/window_stability_summary.csv" \
    --risk-component-rollup "$SUITE/window_analysis/risk_component_stability_rollup.csv" \
    --per-workload-components "$SUITE/window_analysis/per_workload_risk_components_w${W}s_vs_w200s.csv" \
    --output-dir "evaluation/figures/first_gpu_activity_windows_w${W}s_vs_w200s" \
    --decision-window "$W" \
    --reference-window 200 \
    --top-k 12 \
    --heatmap-components risk,mean,median,p95,ewma \
    --skip-profile-plots
done
```

Expected figure folders:

```text
evaluation/figures/first_gpu_activity_windows_w30s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w40s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w60s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w120s_vs_w200s/
```

Each folder should contain only threshold-window figures:

```text
threshold_window_stability_curve.*
risk_component_ablation_curve.*
per_workload_risk_error_heatmap.*
per_workload_mean_error_heatmap.*
per_workload_median_error_heatmap.*
per_workload_p95_error_heatmap.*
per_workload_ewma_error_heatmap.*
figure_inventory.md
```

## Partial results while a run is still active

Run analysis into a separate partial directory:

```bash
python evaluation/threshold_sensitivity/analyze_solo_windows.py \
  --measurements-csv "$SUITE/live_threshold_measurements.csv" \
  --output-dir "$SUITE/window_analysis_partial" \
  --reference-window 200
```

Then generate a partial summary:

```bash
python evaluation/threshold_sensitivity/summarize_solo_windows.py \
  --analysis-dir "$SUITE/window_analysis_partial" \
  --measurements-csv "$SUITE/live_threshold_measurements.csv" \
  --output-md evaluation/threshold_sensitivity/summaries/window_analysis_summary_partial.md \
  --reference-window 200 \
  --decision-window 30
```

Use partial artifacts only for inspection, not final paper claims.

## Build the curated paper artifact index

After final analyses and figures are generated:

```bash
python evaluation/runners/build_paper_artifact_index.py \
  --suite-dir "$SUITE"
```

This writes:

```text
evaluation/paper_artifacts/
```

## Notes

- Start with `all_specs_1gpu.txt`.
- The current solo runner selects one GPU for each run.
- Use `--dry-run` before long campaigns.
- Failed runs are kept in `index.csv`; do not delete them from the dataset.
- The final paper should choose the decision window based on the collected latency/stability tradeoff, not by assumption.

## Script inventory

### Canonical execution scripts

- `live_threshold_runner.py`: launches one workload, observes the post-launch GPU-activity window, records runtime and metric summaries.
- `run_solo_baselines.py`: runs solo baselines for one spec or a spec list using `live_threshold_runner.py`.
- `plan_progressive_threshold_trials.py`: converts a CSV/manifest of progressive job sequences into JSONL trial plans.
- `run_progressive_threshold_trials.py`: executes progressive collocation trials for one threshold setting.
- `run_progressive_threshold_sweep.py`: runs `run_progressive_threshold_trials.py` across a threshold grid.
- `aggregate_progressive_threshold_sweep.py`: aggregates per-setting progressive trial summaries.
- `analyze_progressive_threshold_sweep.py`: ranks aggregated threshold settings by throughput/slowdown constraints.
- `analyze_threshold_sweep_report.py`: generates Markdown reports, tables, and figures from one or more sweep result directories.

### Solo-window analysis scripts

- `analyze_solo_windows.py`: analyzes solo-window measurements from `live_threshold_measurements.csv`.
- `summarize_solo_windows.py`: creates summary files comparing shorter windows against longer reference windows.

### Validation/helper scripts

- `validate_progressive_manifest_memory.py`: checks whether progressive manifest entries fit memory constraints.
- `analyze_admission_thresholds.py`: legacy/ad-hoc threshold analysis helper; review before reuse.
- `generate_analysis_artifacts.py`: legacy/ad-hoc artifact generator; review before reuse.
- `resume_phase1_short_grid.py`: phase1-specific resume helper; candidate for removal after generic resume support is added.

## Output directory conventions

- `manifests/`: input manifests and planned trial JSONL files.
- `solo_runs/`: measured solo-baseline runs.
- `results/`: progressive sweep outputs.
- `summaries/`: solo-window summary Markdown files.
- `reports/`: generated Markdown reports and figures. This directory is ignored and can be regenerated.
- `docs/`: human-written experiment documentation.

