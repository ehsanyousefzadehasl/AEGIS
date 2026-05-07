# Solo Profile Memory Peak Summary

This table compares the 200s observed GPU memory peak against the full-run observed GPU memory peak from solo profiling runs. It does not use YAML memory requirements.

| anchor            |   n |   underestimates_full_peak_count |   underestimates_full_peak_rate |   median_underestimate_mib |   p95_underestimate_mib |   max_underestimate_mib |   median_abs_error_mib |   p95_abs_error_mib |   max_abs_error_mib |
|:------------------|----:|---------------------------------:|--------------------------------:|---------------------------:|------------------------:|------------------------:|-----------------------:|--------------------:|--------------------:|
| launch            |  49 |                                4 |                          0.0816 |                          3 |                    70.3 |                      82 |                      0 |                   2 |                  82 |
| first_memory      |  49 |                                4 |                          0.0816 |                          3 |                    70.3 |                      82 |                      0 |                   2 |                  82 |
| activity_filtered |  49 |                                4 |                          0.0816 |                          3 |                    70.3 |                      82 |                      0 |                   2 |                  82 |


## Largest 200s-vs-full memory peak misses

These rows identify the workloads responsible for the memory underestimation outliers.

| anchor            | workload_id                          |   gpu_memory_peak_200s_mib |   gpu_memory_peak_full_mib |   underestimate_mib |   abs_error_mib |
|:------------------|:-------------------------------------|---------------------------:|---------------------------:|--------------------:|----------------:|
| launch            | maskrcnn_coco_bs8_1gpu               |                      29854 |                      29936 |                  82 |              82 |
| activity_filtered | maskrcnn_coco_bs8_1gpu               |                      29854 |                      29936 |                  82 |              82 |
| first_memory      | maskrcnn_coco_bs8_1gpu               |                      29854 |                      29936 |                  82 |              82 |
| launch            | mobilenet_imagenet_bs128_1gpu        |                      11598 |                      11602 |                   4 |               4 |
| first_memory      | mobilenet_imagenet_bs128_1gpu        |                      11598 |                      11602 |                   4 |               4 |
| activity_filtered | mobilenet_imagenet_bs128_1gpu        |                      11598 |                      11602 |                   4 |               4 |
| first_memory      | mobilenet_imagenet_bs32_1gpu         |                       3354 |                       3356 |                   2 |               2 |
| launch            | mobilenet_imagenet_bs32_1gpu         |                       3354 |                       3356 |                   2 |               2 |
| first_memory      | mobilenet_imagenet_bs64_1gpu         |                       6162 |                       6164 |                   2 |               2 |
| activity_filtered | mobilenet_imagenet_bs32_1gpu         |                       3354 |                       3356 |                   2 |               2 |
| activity_filtered | mobilenet_imagenet_bs64_1gpu         |                       6162 |                       6164 |                   2 |               2 |
| launch            | mobilenet_imagenet_bs64_1gpu         |                       6162 |                       6164 |                   2 |               2 |
| launch            | dlrm_criteo_bs32768_1gpu             |                       1364 |                       1364 |                   0 |               0 |
| launch            | efficientnet_cifar100_bs32_20e_1gpu  |                        668 |                        668 |                   0 |               0 |
| launch            | efficientnet_cifar100_bs128_50e_1gpu |                        860 |                        860 |                   0 |               0 |
