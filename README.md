# AEGIS

AEGIS is a monitoring-guided GPU training scheduler for improving GPU cluster throughput through controlled job collocation. The scheduler separates two decisions that are often conflated: memory feasibility is handled as a hard admission constraint, while runtime interference risk is estimated from short GPU-activity-anchored telemetry windows.

This repository contains the AEGIS scheduler, workload specifications, evaluation runners, and curated paper artifacts.

## Quickstart

To run AEGIS locally, start the scheduler in one terminal and submit workload specifications from another:

```bash
python main.py
```

```bash
python submit.py --task evaluation/workloads/training/specs/yaml/mnist_bs32_1gpu.yaml
```

See the [quickstart guide](docs/quickstart.md) for configuration notes, workload-spec examples, and policy-dependent fields.

## What is included


| Area | Location |
|---|---|
| Scheduler runtime | `runtime/` |
| Placement and admission policies | `placement/` |
| GPU telemetry collection | `telemetry/` |
| Workload specifications and loaders | `workload/`, `evaluation/workloads/` |
| Representative evaluation | `evaluation/experiments/` |
| Threshold-sensitivity studies | `evaluation/threshold_sensitivity/` |
| Solo profiling workflow | `evaluation/profiling/solo/` |
| Paper artifact index | `evaluation/paper_artifacts/` |

## Artifact navigation

For paper and artifact review, start from the curated entry points below.

- [Artifact workflow](evaluation/PAPER_ARTIFACT_WORKFLOW.md): overview of the profiling, threshold-window, and paper-artifact workflow.
- [Paper artifact index](evaluation/paper_artifacts/README.md): curated index of paper-facing tables, figures, and evidence files.
- [Claims and evidence](evaluation/paper_artifacts/claims_and_evidence.md): mapping from paper claims to supporting tables and figures.
- [Final representative evaluation](evaluation/experiments/results/final_representative_evaluation_analysis/report.md): cross-trace evaluation on Philly, Saturn, and Venus.
- [Placement sensitivity](evaluation/experiments/results/or_placement_sensitivity_analysis/report.md): comparison of placement choices.
- [Runtime-pressure threshold ablation](evaluation/experiments/results/runtime_pressure_threshold_ablation_combined_analysis/report.md): effect of the runtime pressure gates.
- [Memory-estimator sensitivity](evaluation/experiments/results/estimator_sensitivity_analysis/estimator_sensitivity_report.md): impact of memory-estimator choice.
- [Threshold sweep](evaluation/threshold_sensitivity/reports/threshold_sweep_v1_fixed_clean/report.md): threshold trade-off report.

## Reproducing analyses

The representative analysis can be regenerated from the evaluation manifest:

```bash
python evaluation/experiments/analyze_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation.yaml \
  --refresh
```

Estimator-sensitivity results can be regenerated with:

```bash
python evaluation/experiments/analyze_estimator_sensitivity.py --refresh
```

The broader paper-artifact workflow is documented in [`evaluation/PAPER_ARTIFACT_WORKFLOW.md`](evaluation/PAPER_ARTIFACT_WORKFLOW.md).

## Tracked artifacts

The repository tracks curated Markdown reports, CSV tables, and PNG figures needed for artifact inspection and reviewer navigation. Raw runtime logs, datasets, generated PDF duplicates, and large DCGMI timeline samples are intentionally excluded from Git.

## Terminology note

Some internal scripts and CSV columns still use legacy names such as `ttfk`. In this repository, those references denote the delay until a job is first observed as active on the GPU, not exact CUDA kernel-launch instrumentation.
