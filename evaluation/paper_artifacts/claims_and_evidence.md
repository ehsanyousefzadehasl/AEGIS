# Claims and Evidence

## Claim 1: Fixed profile windows can be unrepresentative

Evidence: `tables/solo_profile_anchor_comparison.md` and profile mismatch figures. Use this to discuss launch, first-memory, and activity-filtered anchoring.

| anchor            |   n |   median_relative_error_percent |   p90_relative_error_percent |   p95_relative_error_percent |   max_relative_error_percent |
|:------------------|----:|--------------------------------:|-----------------------------:|-----------------------------:|-----------------------------:|
| launch            | 159 |                          0.9861 |                       7.8556 |                       9.8798 |                      18.4679 |
| first_memory      | 159 |                          1.0812 |                       6.813  |                       8.6482 |                      17.4504 |
| activity_filtered | 159 |                          0.9861 |                       5.5049 |                       8.4658 |                      18.4679 |


## Claim 2: First-observed-GPU-activity windows stabilize quickly

Evidence: `tables/first_gpu_activity_window_stability.md`, `threshold_window_stability_curve.pdf`, and per-workload heatmaps.

|   summary_window_seconds |   total_n |   weighted_mean_abs_error |   weighted_p95_abs_error |   weighted_mean_abs_relative_error |
|-------------------------:|----------:|--------------------------:|-------------------------:|-----------------------------------:|
|                       30 |       147 |                    0.0055 |                   0.0163 |                             0.0331 |
|                       40 |       147 |                    0.0052 |                   0.0161 |                             0.0303 |
|                       60 |       147 |                    0.0038 |                   0.013  |                             0.0258 |
|                      120 |       147 |                    0.0027 |                   0.0099 |                             0.0205 |


## Claim 3: Combined risk is a balanced score, not simply the lowest-error component

Evidence: `tables/risk_component_ablation_rollup.md` and `risk_component_ablation_curve.pdf`. The paper should explain that mean, median, p95, and EWMA capture complementary behavior.

| risk_component   |   summary_window_seconds |   total_n |   weighted_mean_abs_error |   weighted_p95_abs_error |
|:-----------------|-------------------------:|----------:|--------------------------:|-------------------------:|
| mean             |                       30 |       147 |                    0.008  |                   0.0305 |
| mean             |                       40 |       147 |                    0.0071 |                   0.0218 |
| mean             |                       60 |       147 |                    0.0044 |                   0.0144 |
| median           |                       30 |       147 |                    0.0047 |                   0.0175 |
| median           |                       40 |       147 |                    0.0047 |                   0.0195 |
| median           |                       60 |       147 |                    0.004  |                   0.0162 |
| p95              |                       30 |       147 |                    0.0032 |                   0.01   |
| p95              |                       40 |       147 |                    0.0032 |                   0.0104 |
| p95              |                       60 |       147 |                    0.0026 |                   0.01   |
| ewma             |                       30 |       147 |                    0.0094 |                   0.0322 |
| ewma             |                       40 |       147 |                    0.0086 |                   0.0295 |
| ewma             |                       60 |       147 |                    0.0069 |                   0.0292 |
| risk             |                       30 |       147 |                    0.0055 |                   0.0163 |
| risk             |                       40 |       147 |                    0.0052 |                   0.0161 |
| risk             |                       60 |       147 |                    0.0038 |                   0.013  |

