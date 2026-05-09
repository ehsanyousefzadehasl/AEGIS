# Solo Profile Anchor Comparison

This table compares 200s-vs-full profile mismatch under three anchors: `launch`, `first_memory`, and `activity_filtered`.

| stat               | anchor            |   n |   median_relative_error_percent |   p90_relative_error_percent |   p95_relative_error_percent |   max_relative_error_percent |
|:-------------------|:------------------|----:|--------------------------------:|-----------------------------:|-----------------------------:|-----------------------------:|
| mean               | launch            | 162 |                          2.9163 |                      16.7879 |                      22.7893 |                      28.1701 |
| mean               | first_memory      | 162 |                          1.3051 |                      16.8646 |                      18.4247 |                      24.4293 |
| mean               | activity_filtered | 162 |                          1.5543 |                       5.5441 |                      16.443  |                      28.1701 |
| median             | launch            | 157 |                          0.4167 |                       4.8272 |                      14.4261 |                      50      |
| median             | first_memory      | 157 |                          0.3236 |                       4.8914 |                      13.4824 |                      50      |
| median             | activity_filtered | 157 |                          0.2703 |                       3.2212 |                      11.1111 |                      50      |
| p95                | launch            | 162 |                          0.3184 |                       3.7882 |                       6.7663 |                      28.9565 |
| p95                | first_memory      | 162 |                          0.33   |                       3.5974 |                       6.7663 |                      28.9565 |
| p95                | activity_filtered | 162 |                          0.3093 |                       3.4925 |                       6.7629 |                      28.9565 |
| ewma               | launch            | 162 |                          2.6402 |                       9.5435 |                      12.1859 |                      18.4638 |
| ewma               | first_memory      | 162 |                          2.5375 |                       8.3155 |                      10.4361 |                      21.4343 |
| ewma               | activity_filtered | 162 |                          1.8639 |                       8.0319 |                      11.645  |                      22.3834 |
| aegis_profile_risk | launch            | 162 |                          1.0094 |                       8.278  |                       9.8654 |                      18.4679 |
| aegis_profile_risk | first_memory      | 162 |                          1.1151 |                       6.8392 |                       8.619  |                      17.4504 |
| aegis_profile_risk | activity_filtered | 162 |                          0.9282 |                       5.4461 |                       8.4406 |                      18.4679 |
