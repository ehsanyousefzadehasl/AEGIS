# Evaluation Manifests

AEGIS experiments can be launched from evaluation manifests. A manifest describes which traces to run, which scheduler configurations to evaluate, where results should be written, and how long each run is allowed to execute.

This guide is for trace-based evaluation runs. For the minimal two-terminal workflow, see the [quickstart guide](quickstart.md). For workload YAML files, see the [workload specification guide](workload-specs.md).

## What an evaluation manifest contains

A typical manifest defines:

- an experiment name,
- the base scheduler configuration,
- the output directory,
- one or more traces,
- one or more scheduler configurations,
- runtime settings such as startup wait time, idle-exit time, and run timeout.

Representative manifests live under:

```text
evaluation/experiments/manifests/
```

Trace files used by the representative evaluation live under:

```text
evaluation/experiments/traces/representative/
```

The curated analysis outputs and reports live under:

```text
evaluation/experiments/results/
evaluation/paper_artifacts/
```

## Manifest structure

A manifest has this general shape:

```yaml
experiment_name: final_representative_evaluation

repetitions: 1

runner:
  base_config: config.yaml
  results_dir: evaluation/experiments/results
  delay_scale: 1.0
  startup_wait_s: 10.0
  eval_idle_exit_minutes: 2.0
  run_timeout_minutes: 720.0

traces:
- name: philly
  csv: evaluation/experiments/traces/representative/philly_seed42_60jobs.execution.csv
- name: saturn
  csv: evaluation/experiments/traces/representative/saturn_seed42_60jobs.execution.csv
- name: venus
  csv: evaluation/experiments/traces/representative/venus_seed42_60jobs.execution.csv

configurations:
- label: exclusive
  policy: exclusive
  estimator: None

- label: aegis_estimator_free
  policy: OR-MAGM
  estimator: None
  risk_smact_threshold: 0.65
  risk_smocc_threshold: 0.35
  risk_drama_threshold: 0.50
```

The runner creates one scheduler run for each trace and configuration pair. Results are written under the configured `results_dir`.

## Trace files

Trace files are CSV files that describe the workload arrival sequence used for a scheduler experiment. The representative traces used by the paper artifact are stored under:

```text
evaluation/experiments/traces/representative/
```

Each trace points to workload specifications that AEGIS can submit during the run. Before launching a long evaluation, check that the trace paths and workload-spec paths are valid on the machine.

## Launching a manifest

Use the manifest runner from the repository root:

```bash
python evaluation/experiments/run_experiment_manifest.py   --manifest evaluation/experiments/manifests/<manifest-name>.yaml
```

For example:

```bash
python evaluation/experiments/run_experiment_manifest.py   --manifest evaluation/experiments/manifests/final_representative_evaluation.yaml
```

Some manifests may be intended for a specific machine, GPU type, or artifact phase. Check the manifest name and the paths inside the file before launching it.

## Runtime behavior

For each run, the manifest runner writes a run-specific configuration, starts AEGIS in evaluation mode, submits jobs according to the trace, waits for completion or idle exit, and stores runtime logs and event files under the experiment results directory.

Typical per-run outputs include:

```text
base_config.yaml
config.yaml
metadata.json
runtime/std.log
runtime/events-*.jsonl
runtime/task_logs/
```

Raw runtime directories can be large and are usually ignored by Git. Curated reports, summary CSVs, and selected figures are tracked separately for the paper artifact.

## Analyzing representative evaluation results

After the runs complete, use the representative-evaluation analysis script:

```bash
python evaluation/experiments/analyze_evaluation_manifest.py   --experiment-root evaluation/experiments/results/final_representative_evaluation   --output-dir evaluation/experiments/results/final_representative_evaluation_analysis
```

The analysis directory contains the generated report, summary CSVs, and figures used for the curated artifact snapshot.

The curated representative evaluation report is available at:

```text
evaluation/experiments/results/final_representative_evaluation_analysis/report.md
```

## Analyzing estimator sensitivity

For memory-estimator sensitivity, use:

```bash
python evaluation/experiments/analyze_estimator_sensitivity.py   --experiment-root evaluation/experiments/results/estimator_sensitivity   --output-dir evaluation/experiments/results/estimator_sensitivity_analysis
```

The curated report is available at:

```text
evaluation/experiments/results/estimator_sensitivity_analysis/estimator_sensitivity_report.md
```

## Other analysis outputs

The repository also includes curated analysis snapshots for placement sensitivity, runtime-pressure threshold ablation, and threshold-window studies. The main entry points are linked from:

```text
ARTIFACT.md
evaluation/PAPER_ARTIFACT_WORKFLOW.md
evaluation/paper_artifacts/README.md
```

These files are the best starting points when reproducing the paper artifact rather than launching a new experiment from scratch.

## Practical checks before launching

Before launching a long manifest run:

1. Confirm that the machine has the expected GPUs.
2. Confirm that the Conda environments used by the workloads exist.
3. Confirm that trace paths exist.
4. Confirm that workload-spec paths referenced by the traces exist.
5. Confirm that `runner.results_dir` points to a writable location.
6. Confirm that `run_timeout_minutes` is long enough for the trace.
7. Start with a small manifest or a single trace when testing a new machine.

## Common mistakes

Do not launch a full representative manifest before testing that `python main.py` and `python submit.py --task <spec>` work on the machine.

Do not commit raw runtime directories, task logs, or telemetry dumps unless they are explicitly curated artifact outputs.

Do not reuse a manifest from another machine without checking paths, GPU capacity assumptions, timeout settings, and workload environments.

Do not treat trace-based evaluation as the quickstart path. The quickstart is for validating that AEGIS launches and can submit one workload; manifests are for controlled multi-run experiments.
