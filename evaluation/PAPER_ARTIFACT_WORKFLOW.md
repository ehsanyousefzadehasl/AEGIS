# Paper Artifact Workflow

This document explains how to navigate and regenerate the curated AEGIS paper artifacts. It is a reviewer-facing guide, not a raw experiment log index.

AEGIS artifacts are organized around three levels:

1. **Curated reports**: Markdown reports with linked CSV tables and PNG figures.
2. **Paper artifact index**: paper-facing claims, evidence tables, and selected figures.
3. **Regeneration scripts**: analysis commands that rebuild reports from completed experiment outputs.

## Primary artifact entry points

Start from:

- [`paper_artifacts/README.md`](paper_artifacts/README.md): curated paper artifact index.
- [`paper_artifacts/claims_and_evidence.md`](paper_artifacts/claims_and_evidence.md): paper claims mapped to supporting evidence.
- [`../ARTIFACT.md`](../ARTIFACT.md): repository-level artifact guide.

The main generated reports are:

- [`experiments/results/final_representative_evaluation_analysis/report.md`](experiments/results/final_representative_evaluation_analysis/report.md): final representative evaluation across Philly, Saturn, and Venus.
- [`experiments/results/or_placement_sensitivity_analysis/report.md`](experiments/results/or_placement_sensitivity_analysis/report.md): placement-policy sensitivity.
- [`experiments/results/runtime_pressure_threshold_ablation_combined_analysis/report.md`](experiments/results/runtime_pressure_threshold_ablation_combined_analysis/report.md): runtime-pressure threshold ablation.
- [`experiments/results/estimator_sensitivity_analysis/estimator_sensitivity_report.md`](experiments/results/estimator_sensitivity_analysis/estimator_sensitivity_report.md): memory-estimator sensitivity.
- [`threshold_sensitivity/reports/threshold_sweep_v1_fixed_clean/report.md`](threshold_sensitivity/reports/threshold_sweep_v1_fixed_clean/report.md): threshold sweep report.

## Evaluation pipelines

### 1. Representative evaluation pipeline

This pipeline runs the scheduler over representative traces and compares AEGIS against exclusive execution and collocation baselines.

Main manifest:

```text
evaluation/experiments/manifests/final_representative_evaluation.yaml
```

Regenerate the final report:

```bash
python evaluation/experiments/analyze_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation.yaml \
  --refresh
```

Curated output:

```text
evaluation/experiments/results/final_representative_evaluation_analysis/
```

### 2. Placement-sensitivity pipeline

This pipeline compares placement choices while keeping the broader AEGIS admission design fixed.

Main manifest:

```text
evaluation/experiments/manifests/final_representative_evaluation_or_placement_sensitivity_combined.yaml
```

Regenerate the report:

```bash
python evaluation/experiments/analyze_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation_or_placement_sensitivity_combined.yaml \
  --refresh
```

Curated output:

```text
evaluation/experiments/results/or_placement_sensitivity_analysis/
```

### 3. Runtime-pressure threshold ablation

This pipeline evaluates the effect of runtime pressure gates and threshold choices.

Main manifest:

```text
evaluation/experiments/manifests/runtime_pressure_threshold_ablation_combined.yaml
```

Regenerate the report:

```bash
python evaluation/experiments/analyze_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/runtime_pressure_threshold_ablation_combined.yaml \
  --refresh
```

Curated output:

```text
evaluation/experiments/results/runtime_pressure_threshold_ablation_combined_analysis/
```

### 4. Memory-estimator sensitivity

This pipeline studies how different memory-estimation sources affect placement and performance.

Main manifest:

```text
evaluation/experiments/manifests/estimator_sensitivity_analysis.yaml
```

Regenerate the report:

```bash
python evaluation/experiments/analyze_estimator_sensitivity.py --refresh
```

Curated output:

```text
evaluation/experiments/results/estimator_sensitivity_analysis/
```

### 5. Solo profiling and threshold-window analyses

These analyses support the monitoring-window design. They compare fixed profile anchors and evaluate first-observed-GPU-activity windows against longer references.

Workflow documents:

- [`profiling/solo/README.md`](profiling/solo/README.md): solo profiling workflow.
- [`threshold_sensitivity/README.md`](threshold_sensitivity/README.md): threshold-sensitivity workflow.

Curated outputs include:

```text
evaluation/paper_artifacts/
evaluation/figures/solo_profile_launch_w200s_vs_full/
evaluation/figures/solo_profile_first_memory_w200s_vs_full/
evaluation/figures/solo_profile_activity_filtered_w200s_vs_full/
evaluation/figures/first_gpu_activity_windows_w30s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w40s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w60s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w120s_vs_w200s/
```

## Rebuilding the paper artifact index

After regenerating the solo-profile and threshold-window analyses, rebuild the paper artifact index with:

```bash
export SUITE=$(ls -td evaluation/threshold_sensitivity/solo_runs/solo_1gpu_threshold_windows_* | head -1)

python evaluation/runners/build_paper_artifact_index.py \
  --suite-dir "$SUITE"
```

This writes:

```text
evaluation/paper_artifacts/
```

Important files include:

- `evaluation/paper_artifacts/README.md`
- `evaluation/paper_artifacts/claims_and_evidence.md`
- `evaluation/paper_artifacts/figure_index.md`
- `evaluation/paper_artifacts/figure_gallery.md`
- `evaluation/paper_artifacts/tables/solo_profile_anchor_comparison.md`
- `evaluation/paper_artifacts/tables/first_gpu_activity_window_stability.md`
- `evaluation/paper_artifacts/tables/risk_component_ablation_rollup.md`
- `evaluation/paper_artifacts/tables/memory_safety_summary.md`
- `evaluation/paper_artifacts/tables/solo_profile_memory_peak_summary.md`
- `evaluation/paper_artifacts/tables/first_gpu_activity_memory_stability.md`
- `evaluation/paper_artifacts/tables/first_gpu_activity_delay_summary.md`

## Tracked and excluded artifacts

Tracked curated outputs include Markdown reports, CSV tables, and PNG figures. These are sufficient for GitHub-based inspection and paper evidence navigation.

Excluded outputs include raw runtime logs, datasets, generated PDF duplicates, and large raw DCGMI timeline samples. These are intentionally left out of Git to keep the repository reviewable.

## Terminology note

Some older scripts and CSV columns use `ttfk` as an internal shorthand. In this artifact, interpret it as the delay until the job is first observed as active on the GPU, not exact CUDA kernel-launch instrumentation.

The first-memory anchor is a diagnostic baseline only. AEGIS uses first-observed GPU activity as the runtime monitoring anchor.
