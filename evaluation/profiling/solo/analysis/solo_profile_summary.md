# Solo Profile Analysis Summary

This summary is generated from extracted solo profiling results.

## Lucid-style 200s profile labels

| lucid_style_class_200s   |   count |
|:-------------------------|--------:|
| Tiny                     |      17 |
| Jumbo                    |      17 |
| Medium                   |      16 |


## Top Lucid-style pressure workloads

| workload_id                    |   source_gpu_count | gpu_label   |   lucid_style_pressure_score_200s |   lucid_style_ss_200s | lucid_style_class_200s   |
|:-------------------------------|-------------------:|:------------|----------------------------------:|----------------------:|:-------------------------|
| gpt2_large_wiki_bs8_2gpu       |                  2 | gpu_a       |                            1      |                     2 | Jumbo                    |
| maskrcnn_coco_bs8_1gpu         |                  1 | single      |                            1      |                     2 | Jumbo                    |
| resnet50_imagenet_bs128_1gpu   |                  1 | single      |                            1      |                     2 | Jumbo                    |
| xception_imagenet_bs128_1gpu   |                  1 | single      |                            1      |                     2 | Jumbo                    |
| gpt2_large_wiki_bs8_2gpu       |                  2 | gpu_b       |                            0.9972 |                     2 | Jumbo                    |
| xception_imagenet_bs64_1gpu    |                  1 | single      |                            0.9636 |                     2 | Jumbo                    |
| resnet50_imagenet_bs64_1gpu    |                  1 | single      |                            0.9268 |                     2 | Jumbo                    |
| vgg16_imagenet_bs64_1gpu       |                  1 | single      |                            0.9154 |                     2 | Jumbo                    |
| xlnet_base_cased_wiki_bs8_2gpu |                  2 | gpu_a       |                            0.9123 |                     2 | Jumbo                    |
| vgg16_imagenet_bs32_1gpu       |                  1 | single      |                            0.9102 |                     2 | Jumbo                    |


## Coarse resource labels

| coarse_resource_label   |   count |
|:------------------------|--------:|
| light                   |      50 |


## Largest 200s-vs-full mismatches


### SMACT profile risk

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.6422 |       0.9527 |                   0.3105 |                        0.3259 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.6501 |       0.9514 |                   0.3013 |                        0.3167 |
| inception_imagenet_bs32_1gpu     |                  1 | single      |       0.461  |       0.6282 |                   0.1672 |                        0.2661 |
| vgg16_imagenet_bs128_1gpu        |                  1 | single      |       0.6314 |       0.8551 |                   0.2237 |                        0.2616 |
| inception_imagenet_bs128_1gpu    |                  1 | single      |       0.5106 |       0.6913 |                   0.1807 |                        0.2614 |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |       0.4064 |       0.5412 |                   0.1347 |                        0.249  |
| resnet50_imagenet_bs32_1gpu      |                  1 | single      |       0.503  |       0.6695 |                   0.1665 |                        0.2487 |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |       0.4875 |       0.6422 |                   0.1546 |                        0.2408 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.1132 |       0.1419 |                   0.0287 |                        0.2021 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.1353 |       0.1182 |                   0.017  |                        0.1441 |


### SMOCC profile risk

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2395 |       0.3449 |                   0.1054 |                        0.3055 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2131 |       0.2957 |                   0.0825 |                        0.2791 |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |       0.2131 |       0.2871 |                   0.074  |                        0.2578 |
| vgg16_imagenet_bs128_1gpu        |                  1 | single      |       0.3249 |       0.4353 |                   0.1104 |                        0.2535 |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |       0.305  |       0.4044 |                   0.0994 |                        0.2459 |
| unet_voc_1gpu                    |                  1 | single      |       0.2737 |       0.3609 |                   0.0872 |                        0.2416 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.061  |       0.0761 |                   0.015  |                        0.1977 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.067  |       0.0772 |                   0.0102 |                        0.1323 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0952 |       0.0907 |                   0.0045 |                        0.0491 |
| resnet18_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.0676 |       0.0708 |                   0.0033 |                        0.0465 |


### DRAMA profile risk

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.1201 |       0.1684 |                   0.0483 |                        0.2866 |
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.0029 |       0.004  |                   0.0011 |                        0.273  |
| mobilenet_imagenet_bs64_1gpu        |                  1 | single      |       0.2304 |       0.3099 |                   0.0795 |                        0.2565 |
| unet_voc_1gpu                       |                  1 | single      |       0.3058 |       0.4109 |                   0.1051 |                        0.2558 |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.1794 |       0.2342 |                   0.0548 |                        0.234  |
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |       0.038  |       0.0428 |                   0.0048 |                        0.1112 |
| resnet34_cifar100_bs64_20e_1gpu     |                  1 | single      |       0.072  |       0.0653 |                   0.0067 |                        0.1032 |
| resnet18_cifar100_bs32_20e_1gpu     |                  1 | single      |       0.0537 |       0.0586 |                   0.005  |                        0.0847 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0088 |       0.0096 |                   0.0008 |                        0.0796 |
| mobilenet_cifar100_bs128_50e_1gpu   |                  1 | single      |       0.0049 |       0.0051 |                   0.0002 |                        0.0405 |


### GPU memory peak

| workload_id                     |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:--------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| xlnet_base_cased_wiki_bs8_2gpu  |                  2 | gpu_a       |         8890 |         8988 |                       98 |                        0.0109 |
| xlnet_base_cased_wiki_bs8_2gpu  |                  2 | sum         |         9318 |         9416 |                       98 |                        0.0104 |
| maskrcnn_coco_bs8_1gpu          |                  1 | single      |        29854 |        29936 |                       82 |                        0.0027 |
| mobilenet_imagenet_bs32_1gpu    |                  1 | single      |         3354 |         3356 |                        2 |                        0.0006 |
| xlnet_large_cased_wiki_bs4_2gpu |                  2 | gpu_a       |        13798 |        13806 |                        8 |                        0.0006 |
| xlnet_large_cased_wiki_bs4_2gpu |                  2 | sum         |        14226 |        14234 |                        8 |                        0.0006 |
| mobilenet_imagenet_bs128_1gpu   |                  1 | single      |        11598 |        11602 |                        4 |                        0.0003 |
| mobilenet_imagenet_bs64_1gpu    |                  1 | single      |         6162 |         6164 |                        2 |                        0.0003 |
| dlrm_criteo_bs32768_1gpu        |                  1 | single      |         1364 |         1364 |                        0 |                        0      |
| bert_base_wiki_bs32_1gpu        |                  1 | single      |        19868 |        19868 |                        0 |                        0      |


## Horus-like oracle utilization inputs

For a generous Horus-like analysis, `horus_oracle_util_full` uses the observed full-run mean GPU utilization (`gputl_mean_full`) as if utilization were predicted perfectly. `horus_profile_util_200s` keeps the first-200s profiled value for comparison.

| workload_id                    |   source_gpu_count | gpu_label   |   horus_oracle_util_full |   horus_profile_util_200s |   horus_oracle_util_median_full |   horus_oracle_util_max_full |   horus_oracle_memory_full_mib |   horus_abs_error_200s_vs_full_util |   horus_relative_error_200s_vs_full_util |
|:-------------------------------|-------------------:|:------------|-------------------------:|--------------------------:|--------------------------------:|-----------------------------:|-------------------------------:|------------------------------------:|-----------------------------------------:|
| gpt2_large_wiki_bs8_2gpu       |                  2 | gpu_a       |                  96.5384 |                   95.0107 |                              99 |                          100 |                          28330 |                              1.5277 |                                   0.0158 |
| xlnet_base_cased_wiki_bs8_2gpu |                  2 | gpu_a       |                  92.1616 |                   90.8251 |                              93 |                          100 |                           8988 |                              1.3364 |                                   0.0145 |
| gpt2_large_wiki_bs8_2gpu       |                  2 | gpu_b       |                  92.063  |                   91.0214 |                              98 |                          100 |                          16458 |                              1.0416 |                                   0.0113 |
| unet_voc_1gpu                  |                  1 | single      |                  88.1983 |                   84.2015 |                              99 |                          100 |                           5636 |                              3.9968 |                                   0.0453 |
| xception_imagenet_bs128_1gpu   |                  1 | single      |                  86.7304 |                   87.3955 |                              84 |                          100 |                          21004 |                              0.6651 |                                   0.0077 |
| vgg16_imagenet_bs128_1gpu      |                  1 | single      |                  86.1971 |                   82.7519 |                              84 |                          100 |                          21668 |                              3.4452 |                                   0.04   |
| vgg16_imagenet_bs32_1gpu       |                  1 | single      |                  86.1591 |                   86.1343 |                              86 |                           92 |                           6680 |                              0.0247 |                                   0.0003 |
| xception_imagenet_bs64_1gpu    |                  1 | single      |                  85.9587 |                   86.597  |                              88 |                           92 |                          10978 |                              0.6383 |                                   0.0074 |
| vgg16_imagenet_bs64_1gpu       |                  1 | single      |                  85.8903 |                   82.7068 |                              87 |                           92 |                          11776 |                              3.1835 |                                   0.0371 |
| xception_imagenet_bs32_1gpu    |                  1 | single      |                  84.9492 |                   82.3955 |                              85 |                           91 |                           5922 |                              2.5537 |                                   0.0301 |


## Notes for paper analysis

- `lucid_style_class_200s` is a Lucid-style profile class, not an exact Lucid reproduction.
- `profile_risk` uses equal weights over mean, median, mode, and max.
- For activity metrics on 2-GPU workloads, inspect `gpu_a` and `gpu_b` separately.
- For memory footprint on 2-GPU workloads, use sum columns when reasoning about total memory demand.
- Large 200s-vs-full mismatch indicates that a short profiling window may not represent the full run.
