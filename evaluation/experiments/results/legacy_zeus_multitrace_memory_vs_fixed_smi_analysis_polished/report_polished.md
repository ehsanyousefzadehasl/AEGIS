# Legacy RTX-2080Ti Evaluation

This polished report is generated from the completed legacy Zeus analysis outputs. It does not modify the original analyzer outputs.

## Evaluation status

| trace           |   configurations |   min_completion_fraction |   failed_attempts |   recovered_attempts |
|:----------------|-----------------:|--------------------------:|------------------:|---------------------:|
| Philly-legacy   |                8 |                         1 |                 1 |                    1 |
| Saturn-legacy   |                8 |                         1 |                 0 |                    0 |
| Venus-gapfix600 |                8 |                         1 |                 0 |                    0 |

## Trace note

The Venus legacy replay uses `venus_gapfix600`, a minimally adjusted variant of the Venus-derived trace. The original trace contained one idle interval of approximately 5.87 hours; only that interval was replaced by a 600-second gap. Job order and all other inter-arrival gaps are preserved. This avoids spending hours testing the replay harness idle path rather than scheduling behavior.

## Cross-trace geomean summary

All values are geometric means across traces and are normalized to Exclusive. Values below 1.0 are better for time metrics. The percentage columns report reduction relative to Exclusive; execution overhead is positive when co-location slows execution.

| policy      |   makespan |   makespan_reduction_% |   mean_jct |   mean_jct_reduction_% |   p95_jct |   mean_queue_wait |   p95_queue_wait |   mean_execution_time |   mean_execution_overhead_% |   p95_execution_time |
|:------------|-----------:|-----------------------:|-----------:|-----------------------:|----------:|------------------:|-----------------:|----------------------:|----------------------------:|---------------------:|
| Exclusive   |      1     |                  0     |      1     |                  0     |     1     |             1     |            1     |                 1     |                       0     |                1     |
| Memory-only |      1.007 |                 -0.716 |      0.998 |                  0.244 |     1.076 |             0.116 |            0.155 |                 1.731 |                      73.081 |                1.955 |
| AEGIS-SMI80 |      0.903 |                  9.693 |      0.89  |                 11     |     0.812 |             0.566 |            0.755 |                 1.185 |                      18.486 |                1.052 |
| AEGIS-SMI70 |      0.884 |                 11.559 |      0.892 |                 10.789 |     0.858 |             0.585 |            0.754 |                 1.172 |                      17.235 |                1.115 |
| AEGIS-SMI60 |      0.892 |                 10.827 |      0.919 |                  8.141 |     0.817 |             0.655 |            0.747 |                 1.157 |                      15.731 |                1.045 |
| AEGIS-SMI50 |      0.982 |                  1.85  |      0.907 |                  9.25  |     0.803 |             0.673 |            0.828 |                 1.113 |                      11.325 |                1.037 |
| Horus       |      0.897 |                 10.263 |      0.89  |                 11.028 |     0.844 |             0.647 |            0.76  |                 1.112 |                      11.224 |                1.044 |
| Lucid       |      0.95  |                  4.954 |      0.876 |                 12.356 |     0.832 |             0.51  |            0.631 |                 1.195 |                      19.474 |                0.963 |

## Cross-trace comparison

### Normalized makespan

![Normalized makespan](figures/normalized_makespan_by_trace.png)

| policy      |   geomean |   Philly-legacy |   Saturn-legacy |   Venus-gapfix600 |
|:------------|----------:|----------------:|----------------:|------------------:|
| Exclusive   |     1     |           1     |           1     |             1     |
| Memory-only |     1.007 |           1.102 |           0.862 |             1.076 |
| AEGIS-SMI80 |     0.903 |           0.987 |           0.737 |             1.013 |
| AEGIS-SMI70 |     0.884 |           0.968 |           0.704 |             1.015 |
| AEGIS-SMI60 |     0.892 |           0.928 |           0.744 |             1.026 |
| AEGIS-SMI50 |     0.982 |           1.088 |           0.861 |             1.009 |
| Horus       |     0.897 |           0.967 |           0.724 |             1.032 |
| Lucid       |     0.95  |           1.118 |           0.757 |             1.014 |

### Normalized mean JCT

![Normalized mean JCT](figures/normalized_mean_jct_by_trace.png)

| policy      |   geomean |   Philly-legacy |   Saturn-legacy |   Venus-gapfix600 |
|:------------|----------:|----------------:|----------------:|------------------:|
| Exclusive   |     1     |           1     |           1     |             1     |
| Memory-only |     0.998 |           1.011 |           1.026 |             0.957 |
| AEGIS-SMI80 |     0.89  |           0.975 |           0.813 |             0.889 |
| AEGIS-SMI70 |     0.892 |           0.968 |           0.825 |             0.889 |
| AEGIS-SMI60 |     0.919 |           0.946 |           0.829 |             0.988 |
| AEGIS-SMI50 |     0.907 |           0.969 |           0.838 |             0.921 |
| Horus       |     0.89  |           0.923 |           0.822 |             0.928 |
| Lucid       |     0.876 |           0.948 |           0.772 |             0.919 |

### Normalized P95 JCT

![Normalized P95 JCT](figures/normalized_p95_jct_by_trace.png)

| policy      |   geomean |   Philly-legacy |   Saturn-legacy |   Venus-gapfix600 |
|:------------|----------:|----------------:|----------------:|------------------:|
| Exclusive   |     1     |           1     |           1     |             1     |
| Memory-only |     1.076 |           1.002 |           1.179 |             1.054 |
| AEGIS-SMI80 |     0.812 |           0.914 |           0.79  |             0.742 |
| AEGIS-SMI70 |     0.858 |           0.9   |           0.904 |             0.775 |
| AEGIS-SMI60 |     0.817 |           0.847 |           0.806 |             0.798 |
| AEGIS-SMI50 |     0.803 |           0.846 |           0.817 |             0.75  |
| Horus       |     0.844 |           0.898 |           0.85  |             0.787 |
| Lucid       |     0.832 |           0.883 |           0.812 |             0.805 |

### Normalized mean queue wait

![Normalized mean queue wait](figures/normalized_mean_queue_wait_by_trace.png)

| policy      |   geomean |   Philly-legacy |   Saturn-legacy |   Venus-gapfix600 |
|:------------|----------:|----------------:|----------------:|------------------:|
| Exclusive   |     1     |           1     |           1     |             1     |
| Memory-only |     0.116 |           0.399 |           0.369 |             0.011 |
| AEGIS-SMI80 |     0.566 |           0.558 |           0.644 |             0.505 |
| AEGIS-SMI70 |     0.585 |           0.598 |           0.658 |             0.51  |
| AEGIS-SMI60 |     0.655 |           0.584 |           0.703 |             0.685 |
| AEGIS-SMI50 |     0.673 |           0.702 |           0.723 |             0.599 |
| Horus       |     0.647 |           0.74  |           0.666 |             0.55  |
| Lucid       |     0.51  |           0.581 |           0.589 |             0.387 |

### Normalized P95 queue wait

![Normalized P95 queue wait](figures/normalized_p95_queue_wait_by_trace.png)

| policy      |   geomean |   Philly-legacy |   Saturn-legacy |   Venus-gapfix600 |
|:------------|----------:|----------------:|----------------:|------------------:|
| Exclusive   |     1     |           1     |           1     |             1     |
| Memory-only |     0.155 |           0.589 |           0.577 |             0.011 |
| AEGIS-SMI80 |     0.755 |           0.62  |           0.798 |             0.871 |
| AEGIS-SMI70 |     0.754 |           0.61  |           0.809 |             0.869 |
| AEGIS-SMI60 |     0.747 |           0.62  |           0.806 |             0.835 |
| AEGIS-SMI50 |     0.828 |           0.793 |           0.832 |             0.862 |
| Horus       |     0.76  |           0.738 |           0.707 |             0.841 |
| Lucid       |     0.631 |           0.668 |           0.732 |             0.514 |

### Normalized mean execution time

![Normalized mean execution time](figures/normalized_mean_execution_time_by_trace.png)

| policy      |   geomean |   Philly-legacy |   Saturn-legacy |   Venus-gapfix600 |
|:------------|----------:|----------------:|----------------:|------------------:|
| Exclusive   |     1     |           1     |           1     |             1     |
| Memory-only |     1.731 |           1.517 |           2.489 |             1.373 |
| AEGIS-SMI80 |     1.185 |           1.32  |           1.192 |             1.057 |
| AEGIS-SMI70 |     1.172 |           1.273 |           1.198 |             1.056 |
| AEGIS-SMI60 |     1.157 |           1.246 |           1.11  |             1.121 |
| AEGIS-SMI50 |     1.113 |           1.189 |           1.092 |             1.062 |
| Horus       |     1.112 |           1.073 |           1.172 |             1.094 |
| Lucid       |     1.195 |           1.252 |           1.182 |             1.153 |

### Normalized P95 execution time

![Normalized P95 execution time](figures/normalized_p95_execution_time_by_trace.png)

| policy      |   geomean |   Philly-legacy |   Saturn-legacy |   Venus-gapfix600 |
|:------------|----------:|----------------:|----------------:|------------------:|
| Exclusive   |     1     |           1     |           1     |             1     |
| Memory-only |     1.955 |           1.97  |           2.869 |             1.322 |
| AEGIS-SMI80 |     1.052 |           1.314 |           1.027 |             0.863 |
| AEGIS-SMI70 |     1.115 |           1.312 |           1.24  |             0.852 |
| AEGIS-SMI60 |     1.045 |           1.301 |           1.044 |             0.84  |
| AEGIS-SMI50 |     1.037 |           1.26  |           1.06  |             0.835 |
| Horus       |     1.044 |           1.262 |           1.095 |             0.824 |
| Lucid       |     0.963 |           1.058 |           0.994 |             0.848 |

## Cross-trace mean/P95 summaries

### JCT mean bars with P95 markers

![JCT mean bars with P95 markers](figures/normalized_jct_mean_bars_p95_markers_by_trace.png)

### Queue-wait mean bars with P95 markers

![Queue-wait mean bars with P95 markers](figures/normalized_queue_wait_mean_bars_p95_markers_by_trace.png)

### Execution-time mean bars with P95 markers

![Execution-time mean bars with P95 markers](figures/normalized_execution_time_mean_bars_p95_markers_by_trace.png)

### Queue/execution trade-off

![Queue/execution trade-off](figures/normalized_queue_execution_tradeoff.png)

## Per-trace distribution figures

### Philly-legacy

#### JCT ECDF

![Philly-legacy JCT ECDF](figures/jct_ecdf_philly_legacy.png)

#### Queue-wait ECDF

![Philly-legacy Queue-wait ECDF](figures/queue_wait_ecdf_philly_legacy.png)

#### Execution-time ECDF

![Philly-legacy Execution-time ECDF](figures/execution_time_ecdf_philly_legacy.png)

#### Completion progress

![Philly-legacy Completion progress](figures/completion_progress_philly_legacy.png)

### Saturn-legacy

#### JCT ECDF

![Saturn-legacy JCT ECDF](figures/jct_ecdf_saturn_legacy.png)

#### Queue-wait ECDF

![Saturn-legacy Queue-wait ECDF](figures/queue_wait_ecdf_saturn_legacy.png)

#### Execution-time ECDF

![Saturn-legacy Execution-time ECDF](figures/execution_time_ecdf_saturn_legacy.png)

#### Completion progress

![Saturn-legacy Completion progress](figures/completion_progress_saturn_legacy.png)

### Venus-gapfix600

#### JCT ECDF

![Venus-gapfix600 JCT ECDF](figures/jct_ecdf_venus_gapfix600.png)

#### Queue-wait ECDF

![Venus-gapfix600 Queue-wait ECDF](figures/queue_wait_ecdf_venus_gapfix600.png)

#### Execution-time ECDF

![Venus-gapfix600 Execution-time ECDF](figures/execution_time_ecdf_venus_gapfix600.png)

#### Completion progress

![Venus-gapfix600 Completion progress](figures/completion_progress_venus_gapfix600.png)

## Per-trace raw summaries

### Philly-legacy

| trace         | policy      |   makespan_s |   mean_jct_s |   p95_jct_s |   mean_queue_wait_s |   p95_queue_wait_s |   mean_execution_s |   p95_execution_s |   failed_attempts |   recovered_attempts |
|:--------------|:------------|-------------:|-------------:|------------:|--------------------:|-------------------:|-------------------:|------------------:|------------------:|---------------------:|
| Philly-legacy | Exclusive   |      30774.7 |      5487.91 |     16874.4 |             2482.51 |           10697    |            3003.38 |           8435.66 |                 0 |                    0 |
| Philly-legacy | Memory-only |      33900.5 |      5549.61 |     16901.9 |              990.83 |            6297.62 |            4556.11 |          16622.3  |                 1 |                    1 |
| Philly-legacy | AEGIS-SMI80 |      30369.7 |      5351.65 |     15418.7 |             1385.04 |            6630.05 |            3964.21 |          11080.9  |                 0 |                    0 |
| Philly-legacy | AEGIS-SMI70 |      29777.8 |      5310.98 |     15189.6 |             1484.1  |            6529.57 |            3824.57 |          11070.1  |                 0 |                    0 |
| Philly-legacy | AEGIS-SMI60 |      28567   |      5194.3  |     14290.9 |             1449.39 |            6635.16 |            3742.58 |          10978.6  |                 0 |                    0 |
| Philly-legacy | AEGIS-SMI50 |      33488.7 |      5317.71 |     14270.2 |             1743.46 |            8480.75 |            3571.99 |          10630.7  |                 0 |                    0 |
| Philly-legacy | Horus       |      29745.7 |      5064.15 |     15156.4 |             1838.16 |            7895.31 |            3223.85 |          10643.9  |                 0 |                    0 |
| Philly-legacy | Lucid       |      34400.2 |      5204.77 |     14895   |             1443.16 |            7146.03 |            3759.33 |           8926.63 |                 0 |                    0 |

### Saturn-legacy

| trace         | policy      |   makespan_s |   mean_jct_s |   p95_jct_s |   mean_queue_wait_s |   p95_queue_wait_s |   mean_execution_s |   p95_execution_s |   failed_attempts |   recovered_attempts |
|:--------------|:------------|-------------:|-------------:|------------:|--------------------:|-------------------:|-------------------:|------------------:|------------------:|---------------------:|
| Saturn-legacy | Exclusive   |      33744   |     10427.6  |     21829.3 |             7197.59 |           15054.1  |            3227.54 |           8747.97 |                 0 |                    0 |
| Saturn-legacy | Memory-only |      29084.3 |     10697.7  |     25738.4 |             2657.94 |            8680.03 |            8034.53 |          25097.5  |                 0 |                    0 |
| Saturn-legacy | AEGIS-SMI80 |      24867.5 |      8481.52 |     17238.1 |             4632.05 |           12013.4  |            3846.45 |           8982.28 |                 0 |                    0 |
| Saturn-legacy | AEGIS-SMI70 |      23758.2 |      8603.78 |     19732   |             4733.02 |           12173.7  |            3867.84 |          10847.1  |                 0 |                    0 |
| Saturn-legacy | AEGIS-SMI60 |      25113.2 |      8644.44 |     17592.3 |             5059.95 |           12137.1  |            3581.71 |           9132.03 |                 0 |                    0 |
| Saturn-legacy | AEGIS-SMI50 |      29050.2 |      8734.09 |     17831.6 |             5207.18 |           12522.5  |            3524.3  |           9276.6  |                 0 |                    0 |
| Saturn-legacy | Horus       |      24439.4 |      8576.57 |     18559.4 |             4792.06 |           10645.4  |            3781.68 |           9577.05 |                 0 |                    0 |
| Saturn-legacy | Lucid       |      25557.5 |      8052.84 |     17726.9 |             4236.7  |           11020.9  |            3813.35 |           8692.76 |                 0 |                    0 |

### Venus-gapfix600

| trace           | policy      |   makespan_s |   mean_jct_s |   p95_jct_s |   mean_queue_wait_s |   p95_queue_wait_s |   mean_execution_s |   p95_execution_s |   failed_attempts |   recovered_attempts |
|:----------------|:------------|-------------:|-------------:|------------:|--------------------:|-------------------:|-------------------:|------------------:|------------------:|---------------------:|
| Venus-gapfix600 | Exclusive   |      25519.8 |      4381.45 |    12968.3  |             1337.95 |            6121.7  |            3041.41 |          10322.2  |                 0 |                    0 |
| Venus-gapfix600 | Memory-only |      27459.5 |      4192.5  |    13664.3  |               14.3  |              67.27 |            4175.91 |          13648.5  |                 0 |                    0 |
| Venus-gapfix600 | AEGIS-SMI80 |      25843.7 |      3894.19 |     9625.86 |              675.78 |            5333.29 |            3216.21 |           8911.81 |                 0 |                    0 |
| Venus-gapfix600 | AEGIS-SMI70 |      25912.9 |      3895.78 |    10056.7  |              682.26 |            5319.39 |            3211.27 |           8793.97 |                 0 |                    0 |
| Venus-gapfix600 | AEGIS-SMI60 |      26194.4 |      4328.17 |    10353.3  |              916.73 |            5109.34 |            3409.16 |           8667.54 |                 0 |                    0 |
| Venus-gapfix600 | AEGIS-SMI50 |      25757   |      4034.64 |     9722.19 |              801.32 |            5275.09 |            3231.09 |           8615.09 |                 0 |                    0 |
| Venus-gapfix600 | Horus       |      26343.2 |      4065.85 |    10208.6  |              736.39 |            5148.63 |            3327.27 |           8509.41 |                 0 |                    0 |
| Venus-gapfix600 | Lucid       |      25881.8 |      4027.36 |    10437    |              517.92 |            3148.58 |            3507.2  |           8756.44 |                 0 |                    0 |
