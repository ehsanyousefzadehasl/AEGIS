# Solo profiling workflow

> For the full paper-artifact workflow, see [Paper Artifact Workflow](../../PAPER_ARTIFACT_WORKFLOW.md).

This directory contains the artifacts, manifests, and extracted results for solo workload profiling.

## What is here

- `manifests/`
  - spec lists (`*.txt`)
  - per-spec profiling args (`profile_args*.csv`)
- `runs/`
  - raw run outputs and monitoring logs
- `extracted/`
  - CSVs extracted from completed runs

## 1) Regenerate manifests

```bash
python evaluation/runners/generate_solo_manifests.py
python evaluation/runners/generate_profile_args_manifest.py
```

This regenerates:

- `evaluation/profiling/solo/manifests/all_specs.txt`
- `evaluation/profiling/solo/manifests/all_specs_1gpu.txt`
- `evaluation/profiling/solo/manifests/all_specs_2gpu.txt`
- `evaluation/profiling/solo/manifests/profile_args.csv`
- `evaluation/profiling/solo/manifests/profile_args_1gpu.csv`
- `evaluation/profiling/solo/manifests/profile_args_2gpu.csv`

## 2) Run all 1-GPU workloads

```bash
python evaluation/runners/run_all_profiles.py --skip-2gpu
```

## 3) Run all 2-GPU workloads

```bash
python evaluation/runners/run_all_profiles.py --skip-1gpu
```

## 4) Run a custom subset

### 1-GPU subset

Create a manifest such as:

`evaluation/profiling/solo/manifests/missing_specs_1gpu.txt`

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

### 2-GPU subset

Create a manifest such as:

`evaluation/profiling/solo/manifests/missing_specs_2gpu.txt`

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

## 5) Run a single spec directly

### 1-GPU

```bash
python evaluation/runners/run_solo_profiles.py \
  --spec evaluation/workloads/training/specs/yaml/<spec_name>_1gpu.yaml \
  --cuda-visible-devices 0 \
  --profile-manifest evaluation/profiling/solo/manifests/profile_args_1gpu.csv
```

### 2-GPU

```bash
python evaluation/runners/run_solo_profiles.py \
  --spec evaluation/workloads/training/specs/yaml/<spec_name>_2gpu.yaml \
  --cuda-visible-devices 0,1 \
  --profile-manifest evaluation/profiling/solo/manifests/profile_args_2gpu.csv
```

## 6) Extract results from completed runs

```bash
python evaluation/runners/extract_solo_profile_results.py
```

This writes:

- `evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv`
- `evaluation/profiling/solo/extracted/solo_profile_results_2gpu.csv`

## Notes

- `runs/index.csv` is appended after each run finishes.
- The extractor uses existing run directories under `runs/`.
- If a failed run directory was deleted, it will not appear in the extracted CSVs.
- For 2-GPU workloads, `CUDA_VISIBLE_DEVICES=0,1` only exposes two GPUs; the training script itself must support multi-GPU execution.
- If MPS causes CUDA issues, stop it before profiling.
