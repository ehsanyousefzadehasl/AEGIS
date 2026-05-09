# Claims and Evidence

## Claim 1: Fixed profile windows can be unrepresentative

Evidence: `tables/solo_profile_anchor_comparison.md` and profile mismatch figures. Use this to discuss launch, first-memory, and activity-filtered anchoring.

| anchor            |   n |   median_relative_error_percent |   p90_relative_error_percent |   p95_relative_error_percent |   max_relative_error_percent |
|:------------------|----:|--------------------------------:|-----------------------------:|-----------------------------:|-----------------------------:|
| launch            | 162 |                          1.0094 |                       8.278  |                       9.8654 |                      18.4679 |
| first_memory      | 162 |                          1.1151 |                       6.8392 |                       8.619  |                      17.4504 |
| activity_filtered | 162 |                          0.9282 |                       5.4461 |                       8.4406 |                      18.4679 |


## Claim 2: First-observed-GPU-activity windows stabilize quickly

Evidence: `tables/first_gpu_activity_window_stability.md`, `threshold_window_stability_curve.pdf`, and per-workload heatmaps.

|   summary_window_seconds |   total_n |   weighted_mean_abs_error |   weighted_p95_abs_error |   weighted_mean_abs_relative_error |
|-------------------------:|----------:|--------------------------:|-------------------------:|-----------------------------------:|
|                       30 |       150 |                    0.0056 |                   0.0163 |                             0.0329 |
|                       40 |       150 |                    0.0052 |                   0.0161 |                             0.0301 |
|                       60 |       150 |                    0.0039 |                   0.013  |                             0.0255 |
|                      120 |       150 |                    0.0027 |                   0.0099 |                             0.0202 |


## Claim 3: Combined risk is a balanced score, not simply the lowest-error component

Evidence: `tables/risk_component_ablation_rollup.md` and `risk_component_ablation_curve.pdf`. The paper should explain that mean, median, p95, and EWMA capture complementary behavior.

| risk_component   |   summary_window_seconds |   total_n |   weighted_mean_abs_error |   weighted_p95_abs_error |
|:-----------------|-------------------------:|----------:|--------------------------:|-------------------------:|
| mean             |                       30 |       150 |                    0.0084 |                   0.0312 |
| mean             |                       40 |       150 |                    0.0074 |                   0.0225 |
| mean             |                       60 |       150 |                    0.0046 |                   0.0148 |
| median           |                       30 |       150 |                    0.0046 |                   0.0173 |
| median           |                       40 |       150 |                    0.0046 |                   0.0193 |
| median           |                       60 |       150 |                    0.0039 |                   0.0161 |
| p95              |                       30 |       150 |                    0.0032 |                   0.0099 |
| p95              |                       40 |       150 |                    0.0031 |                   0.0103 |
| p95              |                       60 |       150 |                    0.0026 |                   0.0099 |
| ewma             |                       30 |       150 |                    0.0097 |                   0.0321 |
| ewma             |                       40 |       150 |                    0.0088 |                   0.0294 |
| ewma             |                       60 |       150 |                    0.007  |                   0.029  |
| risk             |                       30 |       150 |                    0.0056 |                   0.0163 |
| risk             |                       40 |       150 |                    0.0052 |                   0.0161 |
| risk             |                       60 |       150 |                    0.0039 |                   0.013  |

