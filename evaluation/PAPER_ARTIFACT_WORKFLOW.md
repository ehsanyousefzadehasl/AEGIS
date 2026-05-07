# Paper Artifact Workflow

This document is the entry point for reproducing and navigating the evaluation artifacts used for the paper.

There are two separate evaluation pipelines:

1. **Solo profile pipeline**
   - Runs workloads alone and collects profiling logs.
   - Extracts fixed-window profile summaries from raw logs.
   - Compares fixed profile windows against full solo runs.
   - Used for launch-anchor, first-memory-anchor, and activity-filtered analyses.

2. **First-observed-GPU-activity threshold pipeline**
   - Runs workloads alone through the threshold-sensitivity runner.
   - Waits until the job is first observed as active on the GPU.
   - Records multiple post-activity summary windows from the same run.
   - Compares 30s/40s/60s/120s windows against a 200s reference.

## Main workflow documents

- [Solo profiling workflow](profiling/solo/README.md)
- [Threshold sensitivity workflow](threshold_sensitivity/README.md)

## Curated paper artifacts

After regenerating analyses and figures, build the paper artifact index:

```bash
export SUITE=$(ls -td evaluation/threshold_sensitivity/solo_runs/solo_1gpu_threshold_windows_* | head -1)

python evaluation/runners/build_paper_artifact_index.py \
  --suite-dir "$SUITE"
```

This writes:

```text
evaluation/paper_artifacts/
```

Important files:

- `evaluation/paper_artifacts/README.md`
- `evaluation/paper_artifacts/claims_and_evidence.md`
- `evaluation/paper_artifacts/figure_index.md`
- `evaluation/paper_artifacts/tables/solo_profile_anchor_comparison.md`
- `evaluation/paper_artifacts/tables/first_gpu_activity_window_stability.md`
- `evaluation/paper_artifacts/tables/risk_component_ablation_rollup.md`
- `evaluation/paper_artifacts/tables/memory_safety_summary.md`

## Figure organization

Solo-profile figures:

```text
evaluation/figures/solo_profile_launch_w200s_vs_full/
evaluation/figures/solo_profile_first_memory_w200s_vs_full/
evaluation/figures/solo_profile_activity_filtered_w200s_vs_full/
```

First-observed-GPU-activity threshold figures:

```text
evaluation/figures/first_gpu_activity_windows_w30s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w40s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w60s_vs_w200s/
evaluation/figures/first_gpu_activity_windows_w120s_vs_w200s/
```

## Terminology note

Some older scripts and CSV columns may still use `ttfk` as an internal shorthand. In this artifact, that should be interpreted as the wait until the job is first observed as active on the GPU, not as exact CUDA kernel-launch instrumentation.

The first-memory anchor is a diagnostic baseline only. AEGIS uses first-observed GPU activity as the runtime monitoring anchor.
