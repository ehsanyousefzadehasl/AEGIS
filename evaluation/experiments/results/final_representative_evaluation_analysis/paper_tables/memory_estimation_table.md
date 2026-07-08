# Memory-feasibility strategy table

Makespan, mean queue time, and mean execution time are geometric means normalized to Exclusive across traces. OOMs and recovered attempts are totals across traces. Mean failed-attempt time is the mean time spent in failed attempts before recovery.

| Memory mode    |   Makespan |   Mean queue |   Mean exec. |   OOMs |   Recovered | Mean failed-attempt time   |
|:---------------|-----------:|-------------:|-------------:|-------:|------------:|:---------------------------|
| Estimator-free |      0.73  |        0.484 |        1.632 |     12 |          12 | 22.6s                      |
| PeakMem        |      0.712 |        0.442 |        1.785 |      0 |           0 | 0.0s                       |
| HorusMem       |      0.733 |        0.517 |        1.477 |      3 |           3 | 24.3s                      |

## LaTeX label

`tab:eval-memory-estimation`
