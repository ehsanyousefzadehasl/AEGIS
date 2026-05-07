# First-Observed-GPU-Activity Window Stability

This table summarizes how shorter first-observed-GPU-activity windows compare against the 200s reference window for `smact_risk`, `smocc_risk`, and `drama_risk`.

|   summary_window_seconds |   total_n |   weighted_mean_abs_error |   weighted_median_abs_error |   weighted_p95_abs_error |   weighted_mean_abs_relative_error |
|-------------------------:|----------:|--------------------------:|----------------------------:|-------------------------:|-----------------------------------:|
|                        5 |       147 |                    0.0388 |                      0.0179 |                   0.1304 |                             0.1594 |
|                       10 |       147 |                    0.0159 |                      0.0101 |                   0.0481 |                             0.075  |
|                       20 |       147 |                    0.008  |                      0.0056 |                   0.0237 |                             0.0439 |
|                       30 |       147 |                    0.0055 |                      0.0032 |                   0.0163 |                             0.0331 |
|                       40 |       147 |                    0.0052 |                      0.0034 |                   0.0161 |                             0.0303 |
|                       60 |       147 |                    0.0038 |                      0.0022 |                   0.013  |                             0.0258 |
|                      120 |       147 |                    0.0027 |                      0.0017 |                   0.0099 |                             0.0205 |
|                      200 |       147 |                    0      |                      0      |                   0      |                             0      |
