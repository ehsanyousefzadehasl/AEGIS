# Solo Profile Memory Peak Summary

This table compares the 200s observed GPU memory peak against the full-run observed GPU memory peak from solo profiling runs. It does not use YAML memory requirements.

| anchor            |   n |   underestimates_full_peak_count |   underestimates_full_peak_rate |   median_underestimate_mib |   p95_underestimate_mib |   max_underestimate_mib |   median_abs_error_mib |   p95_abs_error_mib |   max_abs_error_mib |
|:------------------|----:|---------------------------------:|--------------------------------:|---------------------------:|------------------------:|------------------------:|-----------------------:|--------------------:|--------------------:|
| launch            |  49 |                                4 |                          0.0816 |                          3 |                    70.3 |                      82 |                      0 |                   2 |                  82 |
| first_memory      |  49 |                                4 |                          0.0816 |                          3 |                    70.3 |                      82 |                      0 |                   2 |                  82 |
| activity_filtered |  49 |                                4 |                          0.0816 |                          3 |                    70.3 |                      82 |                      0 |                   2 |                  82 |
