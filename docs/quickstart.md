# Quickstart

This guide shows the minimal workflow for running AEGIS as a local scheduler and submitting training jobs to it. It is intended for users who want to try the system, inspect the runtime behavior, or adapt AEGIS for their own workloads.

AEGIS has two user-facing entry points:

- `python main.py` starts the scheduler, submission server, and telemetry threads.
- `python submit.py --task <workload.yaml>` submits a workload specification to the running scheduler.

## 1. Configure the scheduler

AEGIS reads its default scheduler configuration from `config.yaml`.

At minimum, check the following fields before running on a new machine:

```yaml
mapper:
  policy: exclusive
  estimator: None

recovery:
  dir: test_logs_folder

risk:
  smact_threshold: 0.65
  smocc_threshold: 0.35
  drama_threshold: 0.50
```

The `mapper.policy` field selects the placement policy. For a first run, `exclusive` is the safest option because it runs one job per GPU. Collocation-oriented policies include `OR-MAGM`, `OR-LUG`, `EST-MAGM`, `EST-LUG`, `PROFILED-MAGM`, and `PROFILED-LUG`.

The `recovery.dir` field should point to a writable local directory. Avoid committing machine-specific absolute paths.

The `risk` thresholds are used by runtime-pressure-aware placement policies. They are ignored by purely exclusive placement.

## 2. Start AEGIS

In one terminal, start the scheduler:

```bash
python main.py
```

This launches:

- the submission server on port `5001`,
- the scheduler loop,
- GPU telemetry collection,
- system-level monitoring.

Keep this terminal running while submitting jobs.

## 3. Submit a workload

In a second terminal, submit a YAML workload specification:

```bash
python submit.py --task evaluation/workloads/training/specs/yaml/mnist_bs32_1gpu.yaml
```

The submission script sends the current user, working directory, and absolute workload-spec path to the scheduler.

A larger example is:

```bash
python submit.py --task evaluation/workloads/training/specs/yaml/bert_base_wiki_bs32_1gpu.yaml
```

## 4. Workload specification format

A workload specification describes the command to run, GPU requirements, memory estimates, and optional profiling metadata.

Example:

```yaml
version: 1

job:
  conda_env: tf
  command: python evaluation/workloads/training/scripts/clean/bert_base_wiki_train.py

resources:
  num_gpus: 1
  gpu_memory_requirement_mib: 19868

estimates:
  horus_mib: 17456.9336
  faketensor_mib: 40000
  gpumemnet_mib: 32000

profile:
  peak_memory_mib: 19868
  avg_smact: 0.8942
  avg_smocc: 0.2677
  avg_drama: 0.1419
  profiling_duration_s: 200
  source: solo_profile_200s
```

The most important fields are:

- `job.conda_env`: Conda environment used to launch the workload.
- `job.command`: training command.
- `resources.num_gpus`: number of GPUs requested.
- `resources.gpu_memory_requirement_mib`: memory requirement used by oracle-style placement.
- `estimates.*_mib`: memory estimates used by estimator-based policies.
- `profile.peak_memory_mib`: profiled peak memory.
- `profile.avg_smact`, `profile.avg_smocc`, `profile.avg_drama`: profiled pressure indicators used by profiled policies and analysis.

Some fields are policy-dependent. For example, the estimator-free runtime-pressure version of AEGIS does not require offline memory-estimator outputs in `estimates`. Policies that use oracle, estimator-based, profiled, or Lucid-style placement require the corresponding fields to be present in the workload specification.

## 5. Adding a new workload

To add a new workload:

1. Create or reuse a training script.
2. Add a YAML spec under `evaluation/workloads/training/specs/`.
3. Set `job.command` to the command that launches the training script.
4. Set `resources.num_gpus` and `resources.gpu_memory_requirement_mib`.
5. Add estimates or profiling metadata if the chosen policy requires them.
6. Submit the YAML file with `python submit.py --task <path>`.

For a first integration test, use `mapper.policy: exclusive` in `config.yaml`. After the workload runs correctly in exclusive mode, switch to a collocation policy.

## 6. Evaluation mode

The repository also includes evaluation runners and manifests under `evaluation/experiments/`. These are used to reproduce paper experiments and large batch runs rather than manually submitting one job at a time.

For paper-artifact reproduction, start from:

- [`ARTIFACT.md`](../ARTIFACT.md)
- [`evaluation/PAPER_ARTIFACT_WORKFLOW.md`](../evaluation/PAPER_ARTIFACT_WORKFLOW.md)
- [`evaluation/paper_artifacts/README.md`](../evaluation/paper_artifacts/README.md)
