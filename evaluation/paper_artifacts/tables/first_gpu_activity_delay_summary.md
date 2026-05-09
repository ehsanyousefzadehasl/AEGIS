# First Observed GPU Activity Delay Summary

This table summarizes the delay from workload dispatch to first observed GPU activity. The internal CSV column is `ttfk_wait_seconds`, but it should be interpreted as first observed GPU activity delay, not exact CUDA-kernel-launch instrumentation.

## Aggregate summary

|   n |   median_first_gpu_activity_delay_s |   p90_first_gpu_activity_delay_s |   p95_first_gpu_activity_delay_s |   max_first_gpu_activity_delay_s |
|----:|------------------------------------:|---------------------------------:|---------------------------------:|---------------------------------:|
|  50 |                              8.1997 |                          10.5511 |                          20.5775 |                          55.4751 |


## Largest first-observed-GPU-activity delays

| workload_id                       |   ttfk_wait_seconds |   time_from_ttfk_to_window_ready_seconds |   total_runtime_seconds |
|:----------------------------------|--------------------:|-----------------------------------------:|------------------------:|
| llama3_width_8layer_wiki_bs1_1gpu |             55.4751 |                                  30.0227 |                2366.65  |
| gpt2_xl_wiki_bs2_1gpu             |             37.91   |                                  30.0253 |               14544.8   |
| maskrcnn_coco_bs8_1gpu            |             23.1613 |                                  30.0413 |                6702.34  |
| bert_large_wiki_bs8_1gpu          |             17.4195 |                                  30.2926 |                2717.19  |
| bert_base_wiki_bs32_1gpu          |             15.3848 |                                  30.2455 |                 908.338 |
| vgg16_imagenet_bs64_1gpu          |             10.014  |                                  30.3825 |                2819.9   |
| vgg16_imagenet_bs128_1gpu         |              9.9204 |                                  30.006  |                2699.78  |
| vgg16_imagenet_bs32_1gpu          |              9.8999 |                                  30.5201 |                3035.35  |
| inception_imagenet_bs128_1gpu     |              9.2678 |                                  30.5214 |                3040     |
| resnet50_imagenet_bs128_1gpu      |              9.1209 |                                  30.1248 |                1888.49  |
| xception_imagenet_bs128_1gpu      |              9.015  |                                  30.2094 |                2866.9   |
| inception_imagenet_bs32_1gpu      |              8.9827 |                                  30.6086 |                3360.57  |
| resnet50_imagenet_bs32_1gpu       |              8.9373 |                                  30.2641 |                2098.91  |
| xception_imagenet_bs64_1gpu       |              8.9342 |                                  30.1804 |                2955.53  |
| resnet50_imagenet_bs64_1gpu       |              8.908  |                                  30.3365 |                1959.5   |

