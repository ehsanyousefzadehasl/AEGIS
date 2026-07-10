# Workload Specifications

AEGIS workloads are described with YAML files. A workload specification tells the scheduler what command to run, how many GPUs the job needs, and which placement metadata are available for the selected policy.

The examples in this repository live under:

```text
evaluation/workloads/training/specs/
```

## Minimal structure

A typical workload specification has four main sections:

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

## Required fields

The fields that must be present depend on the placement policy.

For every runnable workload, AEGIS needs:

```yaml
version: 1

job:
  conda_env: <conda-environment-name>
  command: <training-command>

resources:
  num_gpus: <number-of-gpus>
```

The `job.command` field is executed from the repository working directory used when the job is submitted. Relative paths should therefore be written relative to the repository root.

## Memory and profiling fields

AEGIS supports several placement modes. Some require offline memory information, while others do not.

### Estimator-free runtime-pressure placement

Estimator-free runtime-pressure placement does not require offline memory-estimator outputs in the `estimates` section.

This mode relies on runtime telemetry and admission control rather than a precomputed memory-estimator value. In this mode, the workload specification can omit fields such as:

```yaml
estimates:
  horus_mib: ...
  faketensor_mib: ...
  gpumemnet_mib: ...
```

Use this mode when evaluating the estimator-free AEGIS path.

### Oracle-style placement

Oracle-style policies require an explicit memory requirement:

```yaml
resources:
  gpu_memory_requirement_mib: 19868
```

This value is treated as the known memory requirement of the job.

### Estimator-based placement

Estimator-based policies require the corresponding estimator output:

```yaml
estimates:
  horus_mib: 17456.9336
  faketensor_mib: 40000
  gpumemnet_mib: 32000
```

For example, a Horus-based run needs `horus_mib`, while a FakeTensor-based run needs `faketensor_mib`.

### Profiled placement

Profiled policies require profiled memory information:

```yaml
profile:
  peak_memory_mib: 19868
```

If the policy also uses profiled pressure information, include:

```yaml
profile:
  avg_smact: 0.8942
  avg_smocc: 0.2677
  avg_drama: 0.1419
```

These fields summarize GPU activity from a profiling run.

### Lucid-style placement

Lucid-style placement assigns each workload to a sharing-sensitivity class and uses that class during placement. In the Lucid workflow used in this repository, the training data for the Lucid classifier is built from pairwise collocation experiments: workloads are run together, their observed sharing behavior is labeled, and those labels form the dataset used to train the classifier. The classifier is then used to assign Lucid-compatible labels to unseen workloads.

The Lucid pairwise calibration data, labels, and classifier-derived metadata are kept under `evaluation/lucid` - [check this notebooks](../evaluation/lucid/notebooks/lucid_classifier_inspection.ipynb) - and are used by the Lucid-compatible baseline configuration.

```yaml
profile:
  lucid_class: medium
  lucid_ss: 1
  lucid_label_source: predicted_classifier_lucid_faithful
```


## Adding a new workload

To add a new workload:

1. Add the training script under `evaluation/workloads/training/scripts/` or point to an existing script.
2. Create a YAML specification under `evaluation/workloads/training/specs/`.
3. Set `job.conda_env` to the Conda environment that contains the workload dependencies.
4. Set `job.command` to the command that launches the workload.
5. Set `resources.num_gpus`.
6. Add memory estimates or profiling metadata only if the selected policy requires them.
7. Start with `mapper.policy: exclusive` in `config.yaml` to confirm that the workload launches correctly.
8. After the workload runs in exclusive mode, switch to the target placement policy.

## Example: estimator-free workload

For estimator-free AEGIS, a lightweight specification can focus on launch information and GPU count:

```yaml
version: 1

job:
  conda_env: tf
  command: python evaluation/workloads/training/scripts/clean/mnist_train.py

resources:
  num_gpus: 1
```

This is sufficient only for policies that do not require offline memory estimates or profiled metadata.

## Example: profiled workload

A profiled workload includes peak memory and pressure summaries:

```yaml
version: 1

job:
  conda_env: tf
  command: python evaluation/workloads/training/scripts/clean/bert_base_wiki_train.py

resources:
  num_gpus: 1
  gpu_memory_requirement_mib: 19868

profile:
  peak_memory_mib: 19868
  avg_smact: 0.8942
  avg_smocc: 0.2677
  avg_drama: 0.1419
  profiling_duration_s: 200
  source: solo_profile_200s
```

Use this style for policies that need profiled metadata.

## Common mistakes

Avoid machine-specific absolute paths in committed workload specifications. Prefer paths relative to the repository root.

Make sure the Conda environment exists on the machine running AEGIS.

Make sure the training command can run directly from the repository root.

Do not add estimator outputs unless they are actually produced by the corresponding estimator or profiling workflow.

Do not assume that every workload spec must contain every possible field. AEGIS intentionally supports policy-dependent specifications so estimator-free runs do not need offline estimator metadata.
