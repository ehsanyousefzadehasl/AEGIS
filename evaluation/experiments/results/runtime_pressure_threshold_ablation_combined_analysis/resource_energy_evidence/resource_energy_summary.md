# Resource and Energy Evidence

This report is generated as secondary evidence. It summarizes GPU telemetry over inferred trace windows and computes GPU energy-to-solution when cumulative energy counters are available.

Energy is computed per GPU as the difference between the cumulative energy counter near the inferred trace end and start, then summed across GPUs. Normalized energy is relative to Exclusive within each trace.

| trace   | policy                   | window_duration_s   |   gpu_memory_mean_gb |   gpu_memory_p95_gb |   smact_mean |   smocc_mean |   drama_mean |   power_mean |   total_gpu_energy_j |   normalized_energy_vs_exclusive |   telemetry_file_count |   energy_gpu_count | window_source    |
|:--------|:-------------------------|:--------------------|---------------------:|--------------------:|-------------:|-------------:|-------------:|-------------:|---------------------:|---------------------------------:|-----------------------:|-------------------:|:-----------------|
| philly  | Exclusive                |                     |                 5216 |               37070 |       0.3905 |       0.1779 |       0.2421 |        205.9 |            2.635e+10 |                           1      |                      3 |                  3 | telemetry_minmax |
| philly  | aegis_lug_no_thresholds  |                     |                 3494 |               27860 |       0.5588 |       0.2727 |       0.3336 |        230.6 |            2.319e+10 |                           0.88   |                      3 |                  3 | telemetry_minmax |
| philly  | aegis_lug_thresholded    |                     |                 1439 |                4956 |       0.5165 |       0.2449 |       0.3147 |        225.7 |            2.301e+10 |                           0.8731 |                      3 |                  3 | telemetry_minmax |
| philly  | aegis_magm_no_thresholds |                     |                 3160 |               25840 |       0.7653 |       0.3729 |       0.3503 |        238.8 |            2.274e+10 |                           0.8628 |                      3 |                  3 | telemetry_minmax |
| philly  | aegis_magm_thresholded   |                     |                 2471 |               22600 |       0.5926 |       0.2808 |       0.3553 |        248.1 |            2.256e+10 |                           0.856  |                      3 |                  3 | telemetry_minmax |
| saturn  | Exclusive                |                     |                 5439 |               39540 |       0.3685 |       0.166  |       0.2159 |        191.3 |            2.745e+10 |                           1      |                      3 |                  3 | telemetry_minmax |
| saturn  | aegis_lug_no_thresholds  |                     |                 2843 |               24840 |       0.5264 |       0.254  |       0.3135 |        224   |            2.429e+10 |                           0.8847 |                      3 |                  3 | telemetry_minmax |
| saturn  | aegis_lug_thresholded    |                     |                 1321 |                4880 |       0.5255 |       0.2427 |       0.2957 |        226.3 |            2.414e+10 |                           0.8793 |                      3 |                  3 | telemetry_minmax |
| saturn  | aegis_magm_no_thresholds |                     |                 3036 |               26370 |       0.5715 |       0.2739 |       0.3431 |        242.6 |            2.381e+10 |                           0.8673 |                      3 |                  3 | telemetry_minmax |
| saturn  | aegis_magm_thresholded   |                     |                 3018 |               23950 |       0.5486 |       0.2568 |       0.3265 |        239.9 |            2.389e+10 |                           0.8703 |                      3 |                  3 | telemetry_minmax |
| venus   | Exclusive                |                     |                 5454 |               39090 |       0.5373 |       0.2392 |       0.2349 |        203.5 |            2.729e+10 |                           1      |                      3 |                  3 | telemetry_minmax |
| venus   | aegis_lug_no_thresholds  |                     |                 2133 |               18680 |       0.5991 |       0.2907 |       0.3506 |        239.9 |            2.43e+10  |                           0.8906 |                      3 |                  3 | telemetry_minmax |
| venus   | aegis_lug_thresholded    |                     |                 1312 |                4431 |       0.5579 |       0.2592 |       0.3291 |        241.8 |            2.415e+10 |                           0.8851 |                      3 |                  3 | telemetry_minmax |
| venus   | aegis_magm_no_thresholds |                     |                 2381 |               23950 |       0.5789 |       0.2812 |       0.3438 |        235.4 |            2.415e+10 |                           0.885  |                      3 |                  3 | telemetry_minmax |
| venus   | aegis_magm_thresholded   |                     |                 4452 |               31420 |       0.6989 |       0.3209 |       0.3076 |        235.1 |            2.475e+10 |                           0.907  |                      3 |                  3 | telemetry_minmax |


## Notes

- Check `window_source`: `events_inferred` is preferred; `telemetry_minmax` means the script used the telemetry file span.

- Check `energy_source_column` in the CSV to verify the DCGMI energy counter and unit.

- Use energy-to-solution, not average power alone, for paper claims.
