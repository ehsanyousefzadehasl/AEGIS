# First-Observed-GPU-Activity Window Stability

This table summarizes how shorter first-observed-GPU-activity windows compare against the 200s reference window for `smact_risk`, `smocc_risk`, and `drama_risk`.

|   summary_window_seconds |   total_n |   weighted_mean_abs_error |   weighted_median_abs_error |   weighted_p95_abs_error |   weighted_mean_abs_relative_error |
|-------------------------:|----------:|--------------------------:|----------------------------:|-------------------------:|-----------------------------------:|
|                        5 |       150 |                    0.0423 |                      0.019  |                   0.1389 |                             0.1638 |
|                       10 |       150 |                    0.0175 |                      0.0106 |                   0.0546 |                             0.0771 |
|                       20 |       150 |                    0.0082 |                      0.0057 |                   0.0238 |                             0.0437 |
|                       30 |       150 |                    0.0056 |                      0.0033 |                   0.0163 |                             0.0329 |
|                       40 |       150 |                    0.0052 |                      0.0035 |                   0.0161 |                             0.0301 |
|                       60 |       150 |                    0.0039 |                      0.0023 |                   0.013  |                             0.0255 |
|                      120 |       150 |                    0.0027 |                      0.0017 |                   0.0099 |                             0.0202 |
|                      200 |       150 |                    0      |                      0      |                   0      |                             0      |
