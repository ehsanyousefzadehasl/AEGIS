# Resource and Energy Evidence

This report is generated as secondary evidence. It summarizes GPU telemetry over inferred trace windows and computes GPU energy-to-solution when cumulative energy counters are available.

Energy is computed per GPU as the difference between the cumulative energy counter near the inferred trace end and start, then summed across GPUs. Normalized energy is relative to Exclusive within each trace.

| trace   | policy              | window_duration_s   |   gpu_memory_mean_gb |   gpu_memory_p95_gb |   smact_mean |   smocc_mean |   drama_mean |   power_mean |   total_gpu_energy_j |   normalized_energy_vs_exclusive |   telemetry_file_count |   energy_gpu_count | window_source    |
|:--------|:--------------------|:--------------------|---------------------:|--------------------:|-------------:|-------------:|-------------:|-------------:|---------------------:|---------------------------------:|-----------------------:|-------------------:|:-----------------|
| philly  | Exclusive           |                     |                 5216 |               37070 |       0.3905 |       0.1779 |       0.2421 |        205.9 |            2.635e+10 |                           1      |                      3 |                  3 | telemetry_minmax |
| philly  | Horus               |                     |                 2884 |               29460 |       0.4639 |       0.2079 |       0.2627 |        219.7 |            2.58e+10  |                           0.9791 |                      3 |                  3 | telemetry_minmax |
| philly  | Lucid               |                     |                 4854 |               34490 |       0.6475 |       0.2959 |       0.2859 |        229.2 |            2.481e+10 |                           0.9412 |                      3 |                  3 | telemetry_minmax |
| philly  | AEGIS+HorusMem      |                     |                 2867 |               25360 |       0.5552 |       0.2613 |       0.3399 |        244.6 |            2.312e+10 |                           0.8771 |                      3 |                  3 | telemetry_minmax |
| philly  | AEGIS+PeakMem       |                     |                 3236 |               24730 |       0.5571 |       0.2675 |       0.3471 |        241.2 |            2.261e+10 |                           0.858  |                      3 |                  3 | telemetry_minmax |
| philly  | AEGIS-EstimatorFree |                     |                 2471 |               22600 |       0.5926 |       0.2808 |       0.3553 |        248.1 |            2.256e+10 |                           0.856  |                      3 |                  3 | telemetry_minmax |
| saturn  | Exclusive           |                     |                 5439 |               39540 |       0.3685 |       0.166  |       0.2159 |        191.3 |            2.745e+10 |                           1      |                      3 |                  3 | telemetry_minmax |
| saturn  | Horus               |                     |                 3176 |               31420 |       0.4123 |       0.1845 |       0.2383 |        205.7 |            2.688e+10 |                           0.9792 |                      3 |                  3 | telemetry_minmax |
| saturn  | Lucid               |                     |                 5206 |               35640 |       0.5821 |       0.263  |       0.2529 |        215.4 |            2.626e+10 |                           0.9567 |                      3 |                  3 | telemetry_minmax |
| saturn  | AEGIS+HorusMem      |                     |                 2834 |               24800 |       0.5248 |       0.2427 |       0.3136 |        236.4 |            2.417e+10 |                           0.8806 |                      3 |                  3 | telemetry_minmax |
| saturn  | AEGIS+PeakMem       |                     |                 3080 |               23920 |       0.5201 |       0.2487 |       0.3385 |        243.4 |            2.356e+10 |                           0.8581 |                      3 |                  3 | telemetry_minmax |
| saturn  | AEGIS-EstimatorFree |                     |                 3018 |               23950 |       0.5486 |       0.2568 |       0.3265 |        239.9 |            2.389e+10 |                           0.8703 |                      3 |                  3 | telemetry_minmax |
| venus   | Exclusive           |                     |                 5454 |               39090 |       0.5373 |       0.2392 |       0.2349 |        203.5 |            2.729e+10 |                           1      |                      3 |                  3 | telemetry_minmax |
| venus   | Horus               |                     |                 5017 |               35980 |       0.4123 |       0.1858 |       0.253  |        213   |            2.686e+10 |                           0.9844 |                      3 |                  3 | telemetry_minmax |
| venus   | Lucid               |                     |                 3970 |               33750 |       0.4327 |       0.1945 |       0.2637 |        219.8 |            2.666e+10 |                           0.9769 |                      3 |                  3 | telemetry_minmax |
| venus   | AEGIS+HorusMem      |                     |                 4082 |               30530 |       0.5365 |       0.2482 |       0.3221 |        240.6 |            2.432e+10 |                           0.8912 |                      3 |                  3 | telemetry_minmax |
| venus   | AEGIS+PeakMem       |                     |                 2290 |               16650 |       0.5577 |       0.2593 |       0.3368 |        246   |            2.399e+10 |                           0.8792 |                      3 |                  3 | telemetry_minmax |
| venus   | AEGIS-EstimatorFree |                     |                 4452 |               31420 |       0.6989 |       0.3209 |       0.3076 |        235.1 |            2.475e+10 |                           0.907  |                      3 |                  3 | telemetry_minmax |


## Notes

- Check `window_source`: `events_inferred` is preferred; `telemetry_minmax` means the script used the telemetry file span.

- Check `energy_source_column` in the CSV to verify the DCGMI energy counter and unit.

- Use energy-to-solution, not average power alone, for paper claims.
