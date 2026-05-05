# Threshold Window Analysis Summary

This summary compares shorter TTFK-anchored monitoring windows against a 200s reference window.

## Measurement coverage

- measurement rows: `13`

| summary_windows_collected                |   count |
|:-----------------------------------------|--------:|
| 5.0,10.0,20.0,30.0,40.0,60.0,120.0,200.0 |      13 |


## Stability versus reference window

| metric     |   summary_window_seconds |   reference_window_seconds |   n |   mean_abs_error |   median_abs_error |   p95_abs_error |   mean_abs_relative_error |
|:-----------|-------------------------:|---------------------------:|----:|-----------------:|-------------------:|----------------:|--------------------------:|
| drama_risk |                        5 |                        200 |  12 |          0.0174  |            0.00229 |         0.07376 |                   0.15961 |
| drama_risk |                       10 |                        200 |  12 |          0.00746 |            0.00152 |         0.03035 |                   0.09028 |
| drama_risk |                       20 |                        200 |  12 |          0.00437 |            0.00148 |         0.01645 |                   0.05228 |
| drama_risk |                       30 |                        200 |  12 |          0.00351 |            0.00148 |         0.01133 |                   0.05413 |
| drama_risk |                       40 |                        200 |  12 |          0.00249 |            0.00083 |         0.00714 |                   0.04719 |
| drama_risk |                       60 |                        200 |  12 |          0.00175 |            0.00111 |         0.00557 |                   0.04267 |
| drama_risk |                      120 |                        200 |  12 |          0.00131 |            0.00071 |         0.00467 |                   0.02463 |
| drama_risk |                      200 |                        200 |  12 |          0       |            0       |         0       |                   0       |
| smact_risk |                        5 |                        200 |  12 |          0.073   |            0.0305  |         0.1987  |                   0.18794 |
| smact_risk |                       10 |                        200 |  12 |          0.02789 |            0.01156 |         0.08844 |                   0.05935 |
| smact_risk |                       20 |                        200 |  12 |          0.01781 |            0.01374 |         0.04445 |                   0.04631 |
| smact_risk |                       30 |                        200 |  12 |          0.01246 |            0.00905 |         0.03013 |                   0.03077 |
| smact_risk |                       40 |                        200 |  12 |          0.01456 |            0.00927 |         0.03402 |                   0.04662 |
| smact_risk |                       60 |                        200 |  12 |          0.01321 |            0.01034 |         0.02739 |                   0.04021 |
| smact_risk |                      120 |                        200 |  12 |          0.00823 |            0.00649 |         0.01924 |                   0.02905 |
| smact_risk |                      200 |                        200 |  12 |          0       |            0       |         0       |                   0       |
| smocc_risk |                        5 |                        200 |  12 |          0.03603 |            0.01733 |         0.12155 |                   0.18314 |
| smocc_risk |                       10 |                        200 |  12 |          0.01368 |            0.00682 |         0.04269 |                   0.05632 |
| smocc_risk |                       20 |                        200 |  12 |          0.00904 |            0.00651 |         0.02262 |                   0.04655 |
| smocc_risk |                       30 |                        200 |  12 |          0.00728 |            0.00554 |         0.01778 |                   0.03345 |
| smocc_risk |                       40 |                        200 |  12 |          0.00717 |            0.00532 |         0.01492 |                   0.04527 |
| smocc_risk |                       60 |                        200 |  12 |          0.00636 |            0.00496 |         0.01558 |                   0.03783 |
| smocc_risk |                      120 |                        200 |  12 |          0.0038  |            0.00298 |         0.00831 |                   0.02608 |
| smocc_risk |                      200 |                        200 |  12 |          0       |            0       |         0       |                   0       |


## Largest 30s-vs-200s mismatches

| metric     | task_path                                                                                           |   value_decision |   value_reference |   abs_error |   relative_error |   total_runtime_seconds |   ttfk_wait_seconds |
|:-----------|:----------------------------------------------------------------------------------------------------|-----------------:|------------------:|------------:|-----------------:|------------------------:|--------------------:|
| smact_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_imagenet_bs128_1gpu.yaml     |          0.57306 |           0.6084  |     0.03535 |          0.0581  |                1682.85  |             8.21484 |
| smact_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_imagenet_bs32_1gpu.yaml      |          0.44232 |           0.46818 |     0.02586 |          0.05524 |                2194.62  |             8.31041 |
| smact_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/bert_base_wiki_bs32_1gpu.yaml             |          0.87249 |           0.89734 |     0.02485 |          0.02769 |                 908.338 |            15.3849  |
| smact_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_imagenet_bs64_1gpu.yaml      |          0.58092 |           0.60522 |     0.0243  |          0.04015 |                1698.97  |             8.3562  |
| smocc_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_imagenet_bs128_1gpu.yaml     |          0.35426 |           0.37558 |     0.02132 |          0.05677 |                1682.85  |             8.21484 |
| smocc_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_imagenet_bs32_1gpu.yaml      |          0.24932 |           0.26421 |     0.01489 |          0.05635 |                2194.62  |             8.31041 |
| drama_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_imagenet_bs128_1gpu.yaml     |          0.33419 |           0.34903 |     0.01483 |          0.0425  |                1682.85  |             8.21484 |
| smocc_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_imagenet_bs64_1gpu.yaml      |          0.35088 |           0.36562 |     0.01474 |          0.04032 |                1698.97  |             8.3562  |
| smact_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_cifar100_bs64_50e_1gpu.yaml  |          0.18457 |           0.1958  |     0.01123 |          0.05737 |                1443.82  |             8.26222 |
| smact_risk | /home/ehyo/AEGIS/evaluation/workloads/training/specs/yaml/efficientnet_cifar100_bs128_50e_1gpu.yaml |          0.22332 |           0.23321 |     0.00989 |          0.04239 |                 743.055 |             8.16614 |


## Notes

- The unsuffixed live-runner metric columns correspond to the decision window.
- Suffixed columns such as `smact_risk_w30s` and `smact_risk_w200s` correspond to explicit summary windows.
- Large error at 30s means the 30s decision window does not match the 200s reference for that workload/metric.
- This file is generated from `window_stability_summary.csv` and `window_metrics_long.csv`.
