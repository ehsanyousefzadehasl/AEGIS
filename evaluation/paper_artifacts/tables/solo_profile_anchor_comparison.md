# Solo Profile Anchor Comparison

This table compares 200s-vs-full profile mismatch under three anchors: `launch`, `first_memory`, and `activity_filtered`.

| stat               | anchor            |   n |   median_relative_error_percent |   p90_relative_error_percent |   p95_relative_error_percent |   max_relative_error_percent |
|:-------------------|:------------------|----:|--------------------------------:|-----------------------------:|-----------------------------:|-----------------------------:|
| mean               | launch            | 159 |                          2.8911 |                      15.2814 |                      21.2435 |                      28.1701 |
| mean               | first_memory      | 159 |                          1.2984 |                      13.2687 |                      17.6001 |                      24.4293 |
| mean               | activity_filtered | 159 |                          1.6187 |                       5.5892 |                      16.6714 |                      28.1701 |
| median             | launch            | 156 |                          0.4184 |                       4.856  |                      14.6012 |                      50      |
| median             | first_memory      | 156 |                          0.3247 |                       4.9885 |                      13.5433 |                      50      |
| median             | activity_filtered | 156 |                          0.2717 |                       3.2452 |                      11.1111 |                      50      |
| p95                | launch            | 159 |                          0.332  |                       3.8062 |                       6.9013 |                      28.9565 |
| p95                | first_memory      | 159 |                          0.3835 |                       3.6205 |                       6.9013 |                      28.9565 |
| p95                | activity_filtered | 159 |                          0.3169 |                       3.5339 |                       6.9013 |                      28.9565 |
| ewma               | launch            | 159 |                          2.5935 |                       9.2595 |                      11.6896 |                      18.4638 |
| ewma               | first_memory      | 159 |                          2.5032 |                       7.6318 |                       9.9277 |                      21.4343 |
| ewma               | activity_filtered | 159 |                          1.9765 |                       8.0521 |                      11.6896 |                      22.3834 |
| aegis_profile_risk | launch            | 159 |                          0.9861 |                       7.8556 |                       9.8798 |                      18.4679 |
| aegis_profile_risk | first_memory      | 159 |                          1.0812 |                       6.813  |                       8.6482 |                      17.4504 |
| aegis_profile_risk | activity_filtered | 159 |                          0.9861 |                       5.5049 |                       8.4658 |                      18.4679 |
