# First-GPU-Activity Memory Stability

This table compares observed GPU memory used in shorter first-GPU-activity windows against the 200s reference window. Memory used is computed as `GPU_mem_total - GPU_mem_available`. This is a window-vs-reference comparison, not a full-run peak comparison.

|   summary_window_seconds |   reference_window_seconds |   n |   underestimates_reference_count |   underestimates_reference_rate |   median_underestimate_mib |   p95_underestimate_mib |   max_underestimate_mib |   median_abs_error_mib |   p95_abs_error_mib |   max_abs_error_mib |
|-------------------------:|---------------------------:|----:|---------------------------------:|--------------------------------:|---------------------------:|------------------------:|------------------------:|-----------------------:|--------------------:|--------------------:|
|                       30 |                        200 |  50 |                                0 |                               0 |                          0 |                       0 |                       0 |                      0 |                   0 |                   0 |
|                       40 |                        200 |  50 |                                0 |                               0 |                          0 |                       0 |                       0 |                      0 |                   0 |                   9 |
|                       60 |                        200 |  50 |                                0 |                               0 |                          0 |                       0 |                       0 |                      0 |                   0 |                  28 |
|                      120 |                        200 |  50 |                                0 |                               0 |                          0 |                       0 |                       0 |                      0 |                   0 |                  86 |
