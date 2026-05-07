# Solo Profiling Workflow

> For the full paper-artifact workflow, see [Paper Artifact Workflow](../../PAPER_ARTIFACT_WORKFLOW.md).

This directory contains the artifacts, manifests, extracted results, and analysis outputs for solo workload profiling.

The solo profiling workflow is separate from the first-observed-GPU-activity threshold-sensitivity workflow. This workflow answers:

```text
How representative is a fixed solo profile window compared with the full solo run?
```

It supports three anchors:

```text
activity-filtered: current/default extractor behavior; DCGM metrics start when GPU activity appears.
first-memory:      starts from the first assigned-GPU memory increase; compute-metric zeros after that point are preserved.
launch:            starts from the first assigned-GPU monitor sample; startup/idle samples are included.
```

## What is here

```text
manifests/                         # spec lists and profiling argument manifests
runs/                              # raw solo run outputs and monitoring logs
extracted/                         # default activity-filtered extracted CSVs
extracted_first_memory_anchor/     # first-memory anchored extracted CSVs
extracted_launch_anchor/           # launch-anchored extracted CSVs
analysis/                          # default activity-filtered profile analysis
analysis_first_memory_anchor/      # first-memory anchored profile analysis
analysis_launch_anchor/            # launch-anchored profile analysis
anchor_comparison/                 # compact comparison across anchors, if generated
```

## 1. Regenerate manifests

Run this after adding/removing workload specs:

```bash
python evaluation/runners/generate_solo_manifests.py
python evaluation/runners/generate_profile_args_manifest.py
```

This regenerates:

```text
evaluation/profiling/solo/manifests/all_specs.txt
evaluation/profiling/solo/manifests/all_specs_1gpu.txt
evaluation/profiling/solo/manifests/all_specs_2gpu.txt
evaluation/profiling/solo/manifests/profile_args.csv
evaluation/profiling/solo/manifests/profile_args_1gpu.csv
evaluation/profiling/solo/manifests/profile_args_2gpu.csv
```

## 2. Run solo profiling workloads

### Run all 1-GPU workloads

```bash
python evaluation/runners/run_all_profiles.py --skip-2gpu
```

### Run all 2-GPU workloads

```bash
python evaluation/runners/run_all_profiles.py --skip-1gpu
```

### Run a custom 1-GPU subset

Create a manifest such as:

```text
evaluation/profiling/solo/manifests/missing_specs_1gpu.txt
```

with one spec path per line, for example:

```text
evaluation/workloads/training/specs/yaml/maskrcnn_coco_bs8_1gpu.yaml
evaluation/workloads/training/specs/yaml/mnist_bs32_1gpu.yaml
```

Then run:

```bash
python evaluation/runners/run_solo_profiles.py \
  --spec-list evaluation/profiling/solo/manifests/missing_specs_1gpu.txt \
  --cuda-visible-devices 0 \
  --profile-manifest evaluation/profiling/solo/manifests/profile_args_1gpu.csv
```

### Run a custom 2-GPU subset

Create a manifest such as:

```text
evaluation/profiling/solo/manifests/missing_specs_2gpu.txt
```

with one spec path per line, for example:

```text
evaluation/workloads/training/specs/yaml/xlnet_base_cased_wiki_bs8_2gpu.yaml
evaluation/workloads/training/specs/yaml/xlnet_large_cased_wiki_bs4_2gpu.yaml
```

Then run:

```bash
python evaluation/runners/run_solo_profiles.py \
  --spec-list evaluation/profiling/solo/manifests/missing_specs_2gpu.txt \
  --cuda-visible-devices 0,1 \
  --profile-manifest evaluation/profiling/solo/manifests/profile_args_2gpu.csv
```

### Run one spec directly

1-GPU:

```bash
python evaluation/runners/run_solo_profiles.py \
  --spec evaluation/workloads/training/specs/yaml/<spec_name>_1gpu.yaml \
  --cuda-visible-devices 0 \
  --profile-manifest evaluation/profiling/solo/manifests/profile_args_1gpu.csv
```

2-GPU:

```bash
python evaluation/runners/run_solo_profiles.py \
  --spec evaluation/workloads/training/specs/yaml/<spec_name>_2gpu.yaml \
  --cuda-visible-devices 0,1 \
  --profile-manifest evaluation/profiling/solo/manifests/profile_args_2gpu.csv
```

## 3. Extract anchored profile results from completed runs

The extractor reads existing run directories under:

```text
evaluation/profiling/solo/runs/
```

It writes compact extracted CSVs for 1-GPU and 2-GPU workloads.

### Activity-filtered extraction, default

This is the existing/default behavior. It filters the monitoring prefix until GPU activity appears.

```bash
python evaluation/runners/extract_solo_profile_results.py \
  --runs-root evaluation/profiling/solo/runs \
  --output-dir evaluation/profiling/solo/extracted \
  --window-sec 200
```

Outputs:

```text
evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv
evaluation/profiling/solo/extracted/solo_profile_results_2gpu.csv
```

### First-memory anchored extraction

This starts the finite profile window when assigned GPU memory first rises above its initial baseline. SMACT/SMOCC/DRAMA zeros after that point are preserved.

```bash
python evaluation/runners/extract_solo_profile_results.py \
  --runs-root evaluation/profiling/solo/runs \
  --output-dir evaluation/profiling/solo/extracted_first_memory_anchor \
  --window-sec 200 \
  --anchor first-memory
```

Outputs:

```text
evaluation/profiling/solo/extracted_first_memory_anchor/solo_profile_results_1gpu.csv
evaluation/profiling/solo/extracted_first_memory_anchor/solo_profile_results_2gpu.csv
```

### Launch anchored extraction

This starts from the first assigned-GPU sample in each monitor log and keeps startup/idle samples.

```bash
python evaluation/runners/extract_solo_profile_results.py \
  --runs-root evaluation/profiling/solo/runs \
  --output-dir evaluation/profiling/solo/extracted_launch_anchor \
  --window-sec 200 \
  --anchor launch
```

Outputs:

```text
evaluation/profiling/solo/extracted_launch_anchor/solo_profile_results_1gpu.csv
evaluation/profiling/solo/extracted_launch_anchor/solo_profile_results_2gpu.csv
```

## 4. Analyze extracted solo profiles

The analyzer compares the finite profile window against the full solo run and derives AEGIS profile-risk rows from:

```text
mean, median, p95, ewma
```

### Activity-filtered analysis

```bash
python evaluation/runners/analyze_solo_profile_results.py \
  --input-1gpu evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv \
  --input-2gpu evaluation/profiling/solo/extracted/solo_profile_results_2gpu.csv \
  --output-dir evaluation/profiling/solo/analysis

python evaluation/runners/summarize_solo_profile_analysis.py \
  --analysis-dir evaluation/profiling/solo/analysis \
  --output-md evaluation/profiling/solo/analysis/solo_profile_summary.md
```

### First-memory anchored analysis

```bash
python evaluation/runners/analyze_solo_profile_results.py \
  --input-1gpu evaluation/profiling/solo/extracted_first_memory_anchor/solo_profile_results_1gpu.csv \
  --input-2gpu evaluation/profiling/solo/extracted_first_memory_anchor/solo_profile_results_2gpu.csv \
  --output-dir evaluation/profiling/solo/analysis_first_memory_anchor

python evaluation/runners/summarize_solo_profile_analysis.py \
  --analysis-dir evaluation/profiling/solo/analysis_first_memory_anchor \
  --output-md evaluation/profiling/solo/analysis_first_memory_anchor/solo_profile_summary.md
```

### Launch anchored analysis

```bash
python evaluation/runners/analyze_solo_profile_results.py \
  --input-1gpu evaluation/profiling/solo/extracted_launch_anchor/solo_profile_results_1gpu.csv \
  --input-2gpu evaluation/profiling/solo/extracted_launch_anchor/solo_profile_results_2gpu.csv \
  --output-dir evaluation/profiling/solo/analysis_launch_anchor

python evaluation/runners/summarize_solo_profile_analysis.py \
  --analysis-dir evaluation/profiling/solo/analysis_launch_anchor \
  --output-md evaluation/profiling/solo/analysis_launch_anchor/solo_profile_summary.md
```

Each analysis directory contains compact files such as:

```text
profile_200s_vs_full.csv
workload_characterization.csv
lucid_style_profile_labels.csv
horus_oracle_inputs.csv
solo_profile_summary.md
```

## 5. Generate solo-profile figures

These figures use only the solo-profile analysis CSVs and should be kept separate from first-GPU-activity threshold-window figures.

### Activity-filtered figures

```bash
python evaluation/runners/plot_profile_and_threshold_insights.py \
  --profile-comparison evaluation/profiling/solo/analysis/profile_200s_vs_full.csv \
  --output-dir evaluation/figures/solo_profile_activity_filtered_w200s_vs_full \
  --top-k 12 \
  --skip-threshold-plots
```

### First-memory anchored figures

```bash
python evaluation/runners/plot_profile_and_threshold_insights.py \
  --profile-comparison evaluation/profiling/solo/analysis_first_memory_anchor/profile_200s_vs_full.csv \
  --output-dir evaluation/figures/solo_profile_first_memory_w200s_vs_full \
  --top-k 12 \
  --skip-threshold-plots
```

### Launch anchored figures

```bash
python evaluation/runners/plot_profile_and_threshold_insights.py \
  --profile-comparison evaluation/profiling/solo/analysis_launch_anchor/profile_200s_vs_full.csv \
  --output-dir evaluation/figures/solo_profile_launch_w200s_vs_full \
  --top-k 12 \
  --skip-threshold-plots
```

Expected figure families:

```text
profile_200s_vs_full_boxplot.*
profile_200s_vs_full_component_boxplots.*
profile_top_mismatches.*
profile_top_mismatches_mean.*
profile_top_mismatches_median.*
profile_top_mismatches_p95.*
profile_top_mismatches_ewma.*
figure_inventory.md
```

## 6. Build curated paper artifacts

After extraction, analysis, summaries, and figures are regenerated, build the paper artifact index:

```bash
export SUITE=$(ls -td evaluation/threshold_sensitivity/solo_runs/solo_1gpu_threshold_windows_* | head -1)

python evaluation/runners/build_paper_artifact_index.py \
  --suite-dir "$SUITE"
```

This writes:

```text
evaluation/paper_artifacts/
```

Use that folder when writing the paper.

## Notes

- `runs/index.csv` is appended after each run finishes.
- The extractor uses existing run directories under `runs/`.
- If a failed run directory was deleted, it will not appear in the extracted CSVs.
- For 2-GPU workloads, `CUDA_VISIBLE_DEVICES=0,1` only exposes two GPUs; the training script itself must support multi-GPU execution.
- If MPS causes CUDA issues, stop it before profiling.
- The first-memory anchor is a diagnostic baseline. AEGIS runtime admission uses first observed GPU activity, not first memory allocation.
