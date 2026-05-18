# Progressive Threshold Sensitivity Experiments

This document describes how to reproduce the progressive threshold sensitivity experiments used to study AEGIS admission thresholds.

## Goal

The experiment evaluates threshold settings for AEGIS's post-TTFK admission rule:

```text
reject if:
  SMACT_risk >= tau_smact
  AND (SMOCC_risk >= tau_smocc OR DRAMA_risk >= tau_drama)
```

Each trial launches a sequence of workloads on one GPU. After each admitted workload, the runner waits until the workload is observed on the GPU, collects a post-TTFK monitoring window, computes risk summaries, and decides whether to admit the next workload.

## Recommended experiment split

Use two phases:

```text
Phase 1:
  Broad threshold grid on short/medium representative trials.

Phase 2:
  Heavy validation on selected top thresholds only.
```

Do not use short trial timeouts for final slowdown/throughput results. A timeout-killed workload has no valid slowdown measurement.

Use `tmux` or `screen` for long runs.

---

## Phase 1: Broad short-workload grid

### 1. Create the short-trial manifest

This manifest keeps only the two light CIFAR sequence trials from the larger plan.

```bash
mkdir -p /tmp/progressive_threshold_trials_phase1_short

python - <<'PY'
import json
from pathlib import Path

src = Path("/tmp/progressive_threshold_trials_v1_plan/progressive_trial_plan.jsonl")
dst = Path("/tmp/progressive_threshold_trials_phase1_short/progressive_trial_plan.jsonl")

keep = {"light_cifar_6jobs", "light_cifar_reverse_6jobs"}

rows = []
for line in src.read_text().splitlines():
    row = json.loads(line)
    if row["trial_id"] in keep:
        rows.append(row)

with dst.open("w", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row) + "\n")

print("wrote", dst)
print("rows", len(rows))
for row in rows:
    print(row["trial_id"], len(row["job_sequence"]))
PY
```

Expected:

```text
rows 2
light_cifar_6jobs 6
light_cifar_reverse_6jobs 6
```

### 2. Launch the broad grid

```bash
tmux new -s threshold_phase1_short
```

Inside tmux:

```bash
cd /home/ehyo/AEGIS

python evaluation/threshold_sensitivity/runners/run_progressive_threshold_sweep.py \
  --plan-jsonl /tmp/progressive_threshold_trials_phase1_short/progressive_trial_plan.jsonl \
  --output-root /tmp/progressive_threshold_phase1_short_grid \
  --workdir . \
  --solo-runtime-csv evaluation/threshold_sensitivity/solo_runs/combined_1gpu_threshold_windows_with_llama_20260509_202117/live_threshold_measurements.csv \
  --tau-smact-values 0.70,0.75,0.80,0.85,0.90 \
  --tau-smocc-values 0.35,0.40,0.45,0.50 \
  --tau-drama-values 0.30,0.35,0.40,0.45 \
  --limit-trials 2
```

Detach from tmux:

```text
Ctrl-b d
```

This grid contains:

```text
5 SMACT values × 4 SMOCC values × 4 DRAMA values = 80 threshold settings
```

### 3. Monitor progress

```bash
find /tmp/progressive_threshold_phase1_short_grid -maxdepth 2 -name progressive_trial_summary.csv | wc -l

find /tmp/progressive_threshold_phase1_short_grid -maxdepth 2 -name sweep_failure.json | wc -l

ps -ef | grep -E "run_progressive_threshold|threshold_phase1|train.py" | grep -v grep

nvidia-smi
```

Expected at completion:

```text
80 progressive_trial_summary.csv files
0 or small number of sweep_failure.json files
```

### 4. Aggregate results

```bash
python evaluation/threshold_sensitivity/analysis/aggregate_progressive_threshold_sweep.py \
  --sweep-root /tmp/progressive_threshold_phase1_short_grid

python evaluation/threshold_sensitivity/analysis/analyze_progressive_threshold_sweep.py \
  --summary-csv /tmp/progressive_threshold_phase1_short_grid/threshold_sweep_summary.csv \
  --output-dir /tmp/progressive_threshold_phase1_short_grid/analysis \
  --max-slowdown-budget 1.5
```

Useful outputs:

```text
/tmp/progressive_threshold_phase1_short_grid/threshold_sweep_summary.csv
/tmp/progressive_threshold_phase1_short_grid/analysis/threshold_settings_ranked.csv
/tmp/progressive_threshold_phase1_short_grid/analysis/threshold_settings_feasible.csv
```

---

## Phase 2: Heavy validation

After Phase 1, select the top 2--3 threshold settings and validate them on heavier trials such as ImageNet or memory-heavy models.

Use no timeout, or use a safety timeout that is much larger than expected completion time.

Example validation trials:

```text
imagenet_medium_4jobs
memory-heavy / transformer-heavy sequences
```

---

## Output structure

Per-threshold output directory:

```text
/tmp/progressive_threshold_phase1_short_grid/
  smact_<x>_smocc_<y>_drama_<z>/
    admission_observations.csv
    progressive_trial_summary.csv
    progressive_stage_plan.jsonl
    metadata.json
```

Important columns:

```text
admission_fraction:
  fraction of planned workloads admitted.

completion_fraction:
  fraction of started workloads that completed successfully.

mean_throughput_gain:
  sum of solo runtimes divided by collocated wall-clock runtime.

max_slowdown:
  worst observed slowdown among completed workloads.

reject_retry_count:
  number of rejected retry-later admission attempts.
```

A setting is preferred when it has:

```text
high throughput gain
low max/p95 slowdown
high completion fraction
low reject/retry count
```

---

## Notes for final paper results

For final results, use only completed workloads when computing slowdown and throughput. Timeout-killed or incomplete rows should be excluded from final performance claims and reported separately as failed/incomplete observations.

For the final evaluation, route workload stdout, stderr, timing logs, events, monitoring CSVs, and analysis artifacts into the corresponding experiment output directory.
