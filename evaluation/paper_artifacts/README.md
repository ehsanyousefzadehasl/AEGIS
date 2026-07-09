# Paper Artifacts

This directory is a curated index for the AEGIS paper artifacts. It links paper-facing claims to stable analysis tables, figures, and generated reports. It is intended for writing, review, and artifact navigation; it does not replace the raw experiment outputs.

## What this directory contains

| File | Purpose |
|---|---|
| [`claims_and_evidence.md`](claims_and_evidence.md) | Paper-facing claims and the evidence supporting them. |
| [`figure_index.md`](figure_index.md) | Generated figure paths grouped by analysis. |
| [`figure_gallery.md`](figure_gallery.md) | Visual gallery of selected generated figures. |
| [`tables/solo_profile_anchor_comparison.md`](tables/solo_profile_anchor_comparison.md) | Comparison of launch, first-memory, and activity-filtered profile anchors. |
| [`tables/first_gpu_activity_window_stability.md`](tables/first_gpu_activity_window_stability.md) | Stability of shorter first-observed-GPU-activity windows against a 200s reference. |
| [`tables/risk_component_ablation_rollup.md`](tables/risk_component_ablation_rollup.md) | Summary of mean, median, p95, EWMA, and combined risk components. |
| [`tables/memory_safety_summary.md`](tables/memory_safety_summary.md) | Memory-safety summary for profile windows and workload memory requirements. |
| [`tables/solo_profile_memory_peak_summary.md`](tables/solo_profile_memory_peak_summary.md) | Solo-profile memory peak summary. |
| [`tables/first_gpu_activity_memory_stability.md`](tables/first_gpu_activity_memory_stability.md) | Memory stability of first-observed-GPU-activity windows. |
| [`tables/first_gpu_activity_delay_summary.md`](tables/first_gpu_activity_delay_summary.md) | Delay from dispatch to first observed GPU activity. |

## Source analyses

The curated tables and figures are derived from three analysis groups.

### Solo profile anchor analyses

These compare fixed profile windows against full solo-run behavior:

```text
evaluation/profiling/solo/analysis/
evaluation/profiling/solo/analysis_first_memory_anchor/
evaluation/profiling/solo/analysis_launch_anchor/
```

### First-observed-GPU-activity threshold-window analysis

This analysis evaluates 30s, 40s, 60s, and 120s post-activity windows against a 200s reference.

Primary figure folders:

```text
evaluation/figures/first_gpu_activity_windows_w30s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w40s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w60s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w120s_vs_w200s/
```

### Representative evaluation reports

Main generated reports are tracked under:

```text
evaluation/experiments/results/final_representative_evaluation_analysis/
evaluation/experiments/results/or_placement_sensitivity_analysis/
evaluation/experiments/results/runtime_pressure_threshold_ablation_combined_analysis/
evaluation/experiments/results/estimator_sensitivity_analysis/
evaluation/threshold_sensitivity/reports/threshold_sweep_v1_fixed_clean/
```

## Terminology note

The threshold-window pipeline uses a first-observed-GPU-activity anchor. Some internal CSV columns retain legacy names such as `ttfk_wait_seconds`; interpret those as the delay until the job is first observed as active on the GPU, not exact CUDA kernel-launch instrumentation.
