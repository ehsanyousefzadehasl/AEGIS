# AEGIS Artifact Guide

This document provides a reviewer-facing entry point for inspecting the AEGIS artifact. It focuses on the curated paper artifacts tracked in this repository and separates lightweight inspection from full GPU experiments.

## Artifact contents

The repository contains:

- the AEGIS scheduler implementation;
- workload specifications and evaluation manifests;
- scripts for representative evaluations, estimator sensitivity, threshold sensitivity, and runtime-pressure ablations;
- curated Markdown reports, CSV tables, and PNG figures used for paper validation.

Large raw runtime logs, datasets, generated PDF duplicates, and raw DCGMI timeline samples are intentionally excluded from Git.

## Main entry points

Start with:

- [`README.md`](README.md): repository overview.
- [`evaluation/PAPER_ARTIFACT_WORKFLOW.md`](evaluation/PAPER_ARTIFACT_WORKFLOW.md): paper-artifact workflow.
- [`evaluation/paper_artifacts/README.md`](evaluation/paper_artifacts/README.md): curated paper artifact index.
- [`evaluation/paper_artifacts/claims_and_evidence.md`](evaluation/paper_artifacts/claims_and_evidence.md): claims mapped to evidence.

The main generated evaluation reports are:

- [`evaluation/experiments/results/final_representative_evaluation_analysis/report.md`](evaluation/experiments/results/final_representative_evaluation_analysis/report.md)
- [`evaluation/experiments/results/or_placement_sensitivity_analysis/report.md`](evaluation/experiments/results/or_placement_sensitivity_analysis/report.md)
- [`evaluation/experiments/results/runtime_pressure_threshold_ablation_combined_analysis/report.md`](evaluation/experiments/results/runtime_pressure_threshold_ablation_combined_analysis/report.md)
- [`evaluation/experiments/results/estimator_sensitivity_analysis/estimator_sensitivity_report.md`](evaluation/experiments/results/estimator_sensitivity_analysis/estimator_sensitivity_report.md)
- [`evaluation/threshold_sensitivity/reports/threshold_sweep_v1_fixed_clean/report.md`](evaluation/threshold_sensitivity/reports/threshold_sweep_v1_fixed_clean/report.md)

## Quick inspection

A reviewer can inspect the artifact without rerunning GPU experiments by opening the curated reports above. These reports include the generated tables and figures needed to validate the paper-level claims.

Useful checks:

```bash
git status --short
find evaluation/experiments/results -maxdepth 2 -type f -name '*.md' | sort
find evaluation/paper_artifacts -type f | sort
```

## Regenerating analysis reports

Representative evaluation analysis:

```bash
python evaluation/experiments/analyze_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation.yaml \
  --refresh
```

Estimator sensitivity:

```bash
python evaluation/experiments/analyze_estimator_sensitivity.py --refresh
```

Runtime-pressure threshold ablation:

```bash
python evaluation/experiments/analyze_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/runtime_pressure_threshold_ablation_combined.yaml \
  --refresh
```

Placement sensitivity:

```bash
python evaluation/experiments/analyze_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation_or_placement_sensitivity_combined.yaml \
  --refresh
```

## Full GPU evaluation

Full end-to-end reruns require a multi-GPU machine, the training environments, datasets, and access to GPU telemetry. The representative evaluation manifests are located in:

```text
evaluation/experiments/manifests/
```

A small smoke manifest is available at:

```text
evaluation/experiments/manifests/smoke_manifest.yaml
```

The full experiments are more expensive than the curated report inspection path and are intended for artifact evaluators who want to rerun the scheduler.

## Terminology

Some internal scripts and CSV columns use the legacy shorthand `ttfk`. In this artifact, it denotes the delay until a job is first observed as active on the GPU, not exact CUDA kernel-launch instrumentation.
