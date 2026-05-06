# Solo Profile Analysis Summary

This summary is generated from extracted solo profiling results.

## Lucid-style 200s profile labels

| lucid_style_class_200s   |   count |
|:-------------------------|--------:|
| Tiny                     |      17 |
| Jumbo                    |      17 |
| Medium                   |      16 |


## Top Lucid-style pressure workloads

| workload_id                  |   source_gpu_count | gpu_label   |   lucid_style_pressure_score_200s |   lucid_style_ss_200s | lucid_style_class_200s   |
|:-----------------------------|-------------------:|:------------|----------------------------------:|----------------------:|:-------------------------|
| maskrcnn_coco_bs8_1gpu       |                  1 | single      |                            1      |                     2 | Jumbo                    |
| vgg16_imagenet_bs128_1gpu    |                  1 | single      |                            1      |                     2 | Jumbo                    |
| xception_imagenet_bs128_1gpu |                  1 | single      |                            1      |                     2 | Jumbo                    |
| resnet50_imagenet_bs128_1gpu |                  1 | single      |                            1      |                     2 | Jumbo                    |
| vgg16_imagenet_bs64_1gpu     |                  1 | single      |                            0.9822 |                     2 | Jumbo                    |
| vgg16_imagenet_bs32_1gpu     |                  1 | single      |                            0.9652 |                     2 | Jumbo                    |
| xception_imagenet_bs64_1gpu  |                  1 | single      |                            0.9637 |                     2 | Jumbo                    |
| gpt2_large_wiki_bs8_2gpu     |                  2 | gpu_a       |                            0.949  |                     2 | Jumbo                    |
| resnet50_imagenet_bs64_1gpu  |                  1 | single      |                            0.936  |                     2 | Jumbo                    |
| xception_imagenet_bs32_1gpu  |                  1 | single      |                            0.909  |                     2 | Jumbo                    |


## Coarse resource labels

| coarse_resource_label   |   count |
|:------------------------|--------:|
| light                   |      50 |


## Largest 200s-vs-full mismatches


### SMACT mean

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.7114 |       0.9413 |                   0.23   |                        0.2443 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.6809 |       0.8347 |                   0.1538 |                        0.1843 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.645  |       0.7902 |                   0.1452 |                        0.1838 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.7609 |       0.9233 |                   0.1624 |                        0.1759 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1395 |       0.1192 |                   0.0203 |                        0.17   |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.7537 |       0.8686 |                   0.1149 |                        0.1322 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.766  |       0.8195 |                   0.0535 |                        0.0653 |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.7544 |       0.8066 |                   0.0522 |                        0.0647 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0709 |       0.0755 |                   0.0046 |                        0.0609 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.6936 |       0.6549 |                   0.0387 |                        0.059  |


### SMACT median

| workload_id                       |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:----------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu  |                  1 | single      |       0.1035 |        0.13  |                   0.0265 |                        0.2038 |
| mobilenet_cifar100_bs64_20e_1gpu  |                  1 | single      |       0.123  |        0.103 |                   0.02   |                        0.1942 |
| mobilenet_cifar100_bs32_50e_1gpu  |                  1 | single      |       0.099  |        0.083 |                   0.016  |                        0.1928 |
| gpt2_large_wiki_bs8_2gpu          |                  2 | gpu_b       |       0.793  |        0.914 |                   0.121  |                        0.1324 |
| bert_base_wiki_bs32_1gpu          |                  1 | single      |       0.874  |        0.957 |                   0.083  |                        0.0867 |
| gpt2_large_wiki_bs8_2gpu          |                  2 | gpu_a       |       0.817  |        0.889 |                   0.072  |                        0.081  |
| bert_large_wiki_bs8_1gpu          |                  1 | single      |       0.912  |        0.955 |                   0.043  |                        0.045  |
| resnet34_cifar100_bs128_50e_1gpu  |                  1 | single      |       0.215  |        0.208 |                   0.007  |                        0.0337 |
| mobilenet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.158  |        0.155 |                   0.003  |                        0.0194 |
| mobilenet_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.069  |        0.07  |                   0.001  |                        0.0143 |


### SMACT mode

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_base_wiki_bs32_1gpu         |                  1 | single      |        0     |        0.957 |                    0.957 |                        1      |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |        0     |        0.964 |                    0.964 |                        1      |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |        0     |        0.958 |                    0.958 |                        1      |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |        0     |        0.962 |                    0.962 |                        1      |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |        0     |        0.962 |                    0.962 |                        1      |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |        0     |        0.828 |                    0.828 |                        1      |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |        0.142 |        0.099 |                    0.043 |                        0.4343 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |        0.091 |        0.144 |                    0.053 |                        0.3681 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |        0.636 |        0.781 |                    0.145 |                        0.1857 |
| resnet50_imagenet_bs128_1gpu     |                  1 | single      |        0.804 |        0.683 |                    0.121 |                        0.1772 |


### SMACT max

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |        0.617 |        0.822 |                    0.205 |                        0.2494 |
| resnet34_cifar100_bs64_50e_1gpu     |                  1 | single      |        0.243 |        0.293 |                    0.05  |                        0.1706 |
| resnet18_cifar100_bs32_20e_1gpu     |                  1 | single      |        0.201 |        0.233 |                    0.032 |                        0.1373 |
| efficientnet_cifar100_bs64_50e_1gpu |                  1 | single      |        0.222 |        0.253 |                    0.031 |                        0.1225 |
| mobilenet_cifar100_bs32_50e_1gpu    |                  1 | single      |        0.116 |        0.131 |                    0.015 |                        0.1145 |
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |        0.156 |        0.175 |                    0.019 |                        0.1086 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |        0.178 |        0.198 |                    0.02  |                        0.101  |
| resnet18_cifar100_bs64_50e_1gpu     |                  1 | single      |        0.229 |        0.251 |                    0.022 |                        0.0876 |
| efficientnet_cifar100_bs64_20e_1gpu |                  1 | single      |        0.218 |        0.238 |                    0.02  |                        0.084  |
| efficientnet_cifar100_bs32_50e_1gpu |                  1 | single      |        0.174 |        0.185 |                    0.011 |                        0.0595 |


### SMACT p95

| workload_id                          |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:-------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu             |                  1 | single      |       0.4762 |       0.613  |                   0.1368 |                        0.2231 |
| resnet34_cifar100_bs32_50e_1gpu      |                  1 | single      |       0.2099 |       0.201  |                   0.0089 |                        0.0443 |
| mobilenet_imagenet_bs32_1gpu         |                  1 | single      |       0.51   |       0.491  |                   0.019  |                        0.0387 |
| resnet18_cifar100_bs64_20e_1gpu      |                  1 | single      |       0.201  |       0.194  |                   0.007  |                        0.0361 |
| resnet18_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.193  |       0.199  |                   0.006  |                        0.0302 |
| efficientnet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.2505 |       0.257  |                   0.0065 |                        0.0253 |
| resnet34_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.198  |       0.202  |                   0.004  |                        0.0198 |
| resnet18_cifar100_bs128_50e_1gpu     |                  1 | single      |       0.2506 |       0.2554 |                   0.0048 |                        0.0188 |
| resnet34_cifar100_bs128_50e_1gpu     |                  1 | single      |       0.2866 |       0.2827 |                   0.0039 |                        0.0138 |
| xlnet_large_cased_wiki_bs4_2gpu      |                  2 | gpu_a       |       0.906  |       0.8949 |                   0.0111 |                        0.0123 |


### SMACT EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.6381 |       0.5458 |                   0.0923 |                        0.169  |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1203 |       0.1032 |                   0.0171 |                        0.1659 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.7353 |       0.8158 |                   0.0804 |                        0.0986 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0595 |       0.0657 |                   0.0062 |                        0.0951 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.186  |       0.1717 |                   0.0143 |                        0.0835 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.6724 |       0.7261 |                   0.0538 |                        0.0741 |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |       0.5441 |       0.5079 |                   0.0362 |                        0.0713 |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |       0.4482 |       0.4188 |                   0.0294 |                        0.0701 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.639  |       0.6869 |                   0.0479 |                        0.0697 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.7527 |       0.8053 |                   0.0526 |                        0.0654 |


### SMACT profile stat score

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.6005 |       0.9078 |                   0.3073 |                        0.3385 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.6157 |       0.9127 |                   0.297  |                        0.3254 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.6533 |       0.9528 |                   0.2995 |                        0.3143 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.6595 |       0.9521 |                   0.2926 |                        0.3073 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.6512 |       0.9399 |                   0.2887 |                        0.3072 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.615  |       0.8471 |                   0.2321 |                        0.274  |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.1158 |       0.142  |                   0.0262 |                        0.1846 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.1346 |       0.118  |                   0.0166 |                        0.1408 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.2026 |       0.2353 |                   0.0327 |                        0.1389 |
| resnet34_cifar100_bs64_50e_1gpu  |                  1 | single      |       0.1951 |       0.2088 |                   0.0137 |                        0.0655 |


### SMACT AEGIS profile risk

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.7598 |       0.8383 |                   0.0785 |                        0.0937 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.8369 |       0.9168 |                   0.0798 |                        0.0871 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.7831 |       0.853  |                   0.0699 |                        0.0819 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.1153 |       0.1247 |                   0.0094 |                        0.075  |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.8474 |       0.9121 |                   0.0648 |                        0.071  |
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.0925 |       0.0866 |                   0.0059 |                        0.0685 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.8337 |       0.8919 |                   0.0582 |                        0.0653 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.1224 |       0.1152 |                   0.0072 |                        0.0622 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1975 |       0.2089 |                   0.0113 |                        0.0543 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.7067 |       0.6742 |                   0.0325 |                        0.0482 |


### SMOCC mean

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2463 |       0.3258 |                   0.0795 |                        0.2441 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.2171 |       0.2664 |                   0.0493 |                        0.185  |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.1908 |       0.2339 |                   0.0431 |                        0.1844 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2395 |       0.2904 |                   0.0509 |                        0.1752 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0465 |       0.0399 |                   0.0066 |                        0.1663 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.2263 |       0.2614 |                   0.0351 |                        0.1345 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.2898 |       0.3106 |                   0.0208 |                        0.0669 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3369 |       0.3161 |                   0.0208 |                        0.0658 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0353 |       0.0375 |                   0.0022 |                        0.0579 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0589 |       0.0625 |                   0.0036 |                        0.0575 |


### SMOCC median

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.05   |        0.037 |                   0.013  |                        0.3514 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.052  |        0.07  |                   0.018  |                        0.2571 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.226  |        0.267 |                   0.041  |                        0.1536 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.0595 |        0.055 |                   0.0045 |                        0.0818 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.259  |        0.274 |                   0.015  |                        0.0547 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.295  |        0.307 |                   0.012  |                        0.0391 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.282  |        0.292 |                   0.01   |                        0.0342 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.084  |        0.082 |                   0.002  |                        0.0244 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.264  |        0.27  |                   0.006  |                        0.0222 |
| resnet18_cifar100_bs128_50e_1gpu |                  1 | single      |       0.08   |        0.079 |                   0.001  |                        0.0127 |


### SMOCC mode

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_base_wiki_bs32_1gpu         |                  1 | single      |        0     |        0.304 |                    0.304 |                        1      |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |        0     |        0.257 |                    0.257 |                        1      |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |        0     |        0.271 |                    0.271 |                        1      |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |        0     |        0.271 |                    0.271 |                        1      |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |        0     |        0.308 |                    0.308 |                        1      |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |        0     |        0.312 |                    0.312 |                        1      |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |        0     |        0.312 |                    0.312 |                        1      |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |        0.05  |        0.078 |                    0.028 |                        0.359  |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |        0.094 |        0.082 |                    0.012 |                        0.1463 |
| efficientnet_imagenet_bs64_1gpu  |                  1 | single      |        0.338 |        0.378 |                    0.04  |                        0.1058 |


### SMOCC max

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |        0.203 |        0.269 |                    0.066 |                        0.2454 |
| resnet18_cifar100_bs32_20e_1gpu     |                  1 | single      |        0.073 |        0.085 |                    0.012 |                        0.1412 |
| mobilenet_cifar100_bs128_50e_1gpu   |                  1 | single      |        0.116 |        0.132 |                    0.016 |                        0.1212 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |        0.1   |        0.112 |                    0.012 |                        0.1071 |
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |        0.085 |        0.095 |                    0.01  |                        0.1053 |
| mobilenet_cifar100_bs32_50e_1gpu    |                  1 | single      |        0.06  |        0.067 |                    0.007 |                        0.1045 |
| resnet18_cifar100_bs64_50e_1gpu     |                  1 | single      |        0.086 |        0.095 |                    0.009 |                        0.0947 |
| efficientnet_cifar100_bs64_20e_1gpu |                  1 | single      |        0.136 |        0.145 |                    0.009 |                        0.0621 |
| efficientnet_cifar100_bs32_50e_1gpu |                  1 | single      |        0.099 |        0.104 |                    0.005 |                        0.0481 |
| inception_imagenet_bs128_1gpu       |                  1 | single      |        0.348 |        0.364 |                    0.016 |                        0.044  |


### SMOCC p95

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1547 |       0.2045 |                   0.0498 |                        0.2433 |
| resnet34_cifar100_bs32_50e_1gpu  |                  1 | single      |       0.0849 |       0.08   |                   0.0049 |                        0.0612 |
| mobilenet_imagenet_bs32_1gpu     |                  1 | single      |       0.2484 |       0.24   |                   0.0084 |                        0.035  |
| resnet18_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.0704 |       0.073  |                   0.0026 |                        0.0349 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.33   |       0.338  |                   0.008  |                        0.0237 |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.3554 |       0.348  |                   0.0074 |                        0.0213 |
| resnet18_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0945 |       0.0965 |                   0.002  |                        0.0207 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.1133 |       0.111  |                   0.0023 |                        0.0207 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.288  |       0.294  |                   0.006  |                        0.0204 |
| resnet18_cifar100_bs64_50e_1gpu  |                  1 | single      |       0.0734 |       0.072  |                   0.0013 |                        0.0187 |


### SMOCC EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.309  |       0.2606 |                   0.0484 |                        0.1857 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0402 |       0.0345 |                   0.0056 |                        0.1629 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2524 |       0.2819 |                   0.0294 |                        0.1044 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0294 |       0.0325 |                   0.0031 |                        0.095  |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0725 |       0.0672 |                   0.0053 |                        0.0784 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.2146 |       0.2319 |                   0.0173 |                        0.0747 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.1892 |       0.2034 |                   0.0142 |                        0.0697 |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |       0.3364 |       0.3154 |                   0.0211 |                        0.0668 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2369 |       0.2533 |                   0.0164 |                        0.0646 |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |       0.2348 |       0.2209 |                   0.0138 |                        0.0626 |


### SMOCC profile stat score

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.1787 |       0.2687 |                   0.09   |                        0.335  |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.2006 |       0.2891 |                   0.0885 |                        0.3062 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2426 |       0.3449 |                   0.1024 |                        0.2968 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.2    |       0.2829 |                   0.0828 |                        0.2928 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2161 |       0.2958 |                   0.0797 |                        0.2695 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.2372 |       0.3247 |                   0.0874 |                        0.2693 |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.2421 |       0.3244 |                   0.0822 |                        0.2536 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0615 |       0.0764 |                   0.0149 |                        0.1951 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.067  |       0.0772 |                   0.0102 |                        0.1323 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0949 |       0.0906 |                   0.0043 |                        0.0479 |


### SMOCC AEGIS profile risk

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.0466 |       0.0424 |                   0.0042 |                        0.1    |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.2244 |       0.2493 |                   0.0249 |                        0.0998 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.3024 |       0.3337 |                   0.0312 |                        0.0936 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0605 |       0.0666 |                   0.0062 |                        0.0925 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.2459 |       0.2656 |                   0.0197 |                        0.074  |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.065  |       0.0697 |                   0.0047 |                        0.0681 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2736 |       0.2924 |                   0.0188 |                        0.0643 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.2528 |       0.2686 |                   0.0158 |                        0.0589 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3435 |       0.3263 |                   0.0172 |                        0.0527 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0881 |       0.0849 |                   0.0032 |                        0.0381 |


### DRAMA mean

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.1631 |       0.2119 |                   0.0489 |                        0.2305 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.1283 |       0.1559 |                   0.0276 |                        0.1771 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0271 |       0.0232 |                   0.004  |                        0.1716 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.1326 |       0.16   |                   0.0273 |                        0.1708 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.1763 |       0.2121 |                   0.0358 |                        0.1689 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.1193 |       0.1371 |                   0.0179 |                        0.1304 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0028 |       0.0031 |                   0.0003 |                        0.1027 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.4003 |       0.3697 |                   0.0306 |                        0.0826 |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.1974 |       0.2119 |                   0.0145 |                        0.0685 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.1951 |       0.2079 |                   0.0128 |                        0.0615 |


### DRAMA median

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.002  |        0.004 |                   0.002  |                        0.5    |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.142  |        0.166 |                   0.024  |                        0.1446 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.008  |        0.009 |                   0.001  |                        0.1111 |
| resnet18_cifar100_bs64_50e_1gpu     |                  1 | single      |       0.052  |        0.048 |                   0.004  |                        0.0833 |
| resnet18_cifar100_bs64_20e_1gpu     |                  1 | single      |       0.052  |        0.049 |                   0.003  |                        0.0612 |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_b       |       0.154  |        0.16  |                   0.006  |                        0.0375 |
| resnet34_cifar100_bs128_50e_1gpu    |                  1 | single      |       0.066  |        0.064 |                   0.002  |                        0.0312 |
| resnet34_cifar100_bs32_20e_1gpu     |                  1 | single      |       0.0525 |        0.051 |                   0.0015 |                        0.0294 |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.153  |        0.157 |                   0.004  |                        0.0255 |
| resnet18_cifar100_bs32_50e_1gpu     |                  1 | single      |       0.047  |        0.048 |                   0.001  |                        0.0208 |


### DRAMA mode

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_base_wiki_bs32_1gpu            |                  1 | single      |        0     |        0.135 |                    0.135 |                        1      |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |        0     |        0.153 |                    0.153 |                        1      |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_b       |        0     |        0.145 |                    0.145 |                        1      |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_a       |        0     |        0.214 |                    0.214 |                        1      |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |        0     |        0.12  |                    0.12  |                        1      |
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |        0.002 |        0.004 |                    0.002 |                        0.5    |
| resnet34_cifar100_bs64_20e_1gpu     |                  1 | single      |        0.077 |        0.052 |                    0.025 |                        0.4808 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |        0.008 |        0.009 |                    0.001 |                        0.1111 |
| efficientnet_cifar100_bs64_20e_1gpu |                  1 | single      |        0.012 |        0.011 |                    0.001 |                        0.0909 |
| resnet34_cifar100_bs32_50e_1gpu     |                  1 | single      |        0.048 |        0.052 |                    0.004 |                        0.0769 |


### DRAMA max

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |        0.113 |        0.148 |                    0.035 |                        0.2365 |
| resnet18_cifar100_bs32_20e_1gpu     |                  1 | single      |        0.071 |        0.09  |                    0.019 |                        0.2111 |
| mobilenet_cifar100_bs128_50e_1gpu   |                  1 | single      |        0.007 |        0.008 |                    0.001 |                        0.125  |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |        0.011 |        0.012 |                    0.001 |                        0.0833 |
| efficientnet_cifar100_bs64_20e_1gpu |                  1 | single      |        0.015 |        0.016 |                    0.001 |                        0.0625 |
| efficientnet_cifar100_bs64_50e_1gpu |                  1 | single      |        0.015 |        0.016 |                    0.001 |                        0.0625 |
| inception_imagenet_bs128_1gpu       |                  1 | single      |        0.412 |        0.433 |                    0.021 |                        0.0485 |
| xlnet_base_cased_wiki_bs8_2gpu      |                  2 | gpu_a       |        0.231 |        0.242 |                    0.011 |                        0.0455 |
| resnet34_cifar100_bs32_20e_1gpu     |                  1 | single      |        0.095 |        0.098 |                    0.003 |                        0.0306 |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |        0.426 |        0.439 |                    0.013 |                        0.0296 |


### DRAMA p95

| workload_id                          |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:-------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu             |                  1 | single      |       0.0817 |       0.115  |                   0.0333 |                        0.2896 |
| efficientnet_cifar100_bs64_20e_1gpu  |                  1 | single      |       0.013  |       0.015  |                   0.002  |                        0.1333 |
| resnet34_cifar100_bs32_50e_1gpu      |                  1 | single      |       0.0889 |       0.079  |                   0.0099 |                        0.1253 |
| efficientnet_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.01   |       0.009  |                   0.001  |                        0.1111 |
| resnet18_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.061  |       0.0675 |                   0.0065 |                        0.097  |
| resnet18_cifar100_bs64_50e_1gpu      |                  1 | single      |       0.069  |       0.064  |                   0.005  |                        0.0781 |
| efficientnet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0233 |       0.025  |                   0.0017 |                        0.068  |
| resnet18_cifar100_bs64_20e_1gpu      |                  1 | single      |       0.0628 |       0.06   |                   0.0028 |                        0.0467 |
| resnet34_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.0774 |       0.081  |                   0.0036 |                        0.0438 |
| resnet18_cifar100_bs32_50e_1gpu      |                  1 | single      |       0.0643 |       0.062  |                   0.0023 |                        0.0379 |


### DRAMA EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3663 |       0.3017 |                   0.0647 |                        0.2143 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0237 |       0.02   |                   0.0037 |                        0.1827 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0634 |       0.0569 |                   0.0064 |                        0.1133 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0024 |       0.0027 |                   0.0003 |                        0.0987 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.1654 |       0.1831 |                   0.0177 |                        0.0966 |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |       0.2541 |       0.2352 |                   0.0189 |                        0.0804 |
| mobilenet_imagenet_bs32_1gpu     |                  1 | single      |       0.2075 |       0.1929 |                   0.0146 |                        0.0758 |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |       0.3106 |       0.2902 |                   0.0204 |                        0.0704 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.0026 |       0.0024 |                   0.0002 |                        0.069  |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.1271 |       0.136  |                   0.009  |                        0.0658 |


### DRAMA profile stat score

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_a       |       0.1618 |       0.2243 |                   0.0625 |                        0.2785 |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.1216 |       0.1685 |                   0.0469 |                        0.2784 |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_b       |       0.1192 |       0.1637 |                   0.0446 |                        0.2723 |
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.003  |       0.004  |                   0.0011 |                        0.2679 |
| bert_base_wiki_bs32_1gpu            |                  1 | single      |       0.1111 |       0.1495 |                   0.0385 |                        0.2573 |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.1828 |       0.2342 |                   0.0515 |                        0.2197 |
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |       0.038  |       0.0428 |                   0.0048 |                        0.1112 |
| resnet34_cifar100_bs64_20e_1gpu     |                  1 | single      |       0.0716 |       0.0652 |                   0.0064 |                        0.0982 |
| resnet18_cifar100_bs32_20e_1gpu     |                  1 | single      |       0.0536 |       0.0586 |                   0.005  |                        0.0856 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0088 |       0.0096 |                   0.0008 |                        0.0822 |


### DRAMA AEGIS profile risk

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.0031 |       0.0037 |                   0.0006 |                        0.1745 |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.2155 |       0.2415 |                   0.026  |                        0.1078 |
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |       0.0361 |       0.0395 |                   0.0034 |                        0.0864 |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.1494 |       0.1606 |                   0.0113 |                        0.07   |
| resnet18_cifar100_bs64_50e_1gpu     |                  1 | single      |       0.0541 |       0.0507 |                   0.0035 |                        0.0684 |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_b       |       0.1501 |       0.1608 |                   0.0107 |                        0.0664 |
| maskrcnn_coco_bs8_1gpu              |                  1 | single      |       0.4166 |       0.3931 |                   0.0235 |                        0.0598 |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_a       |       0.2022 |       0.2139 |                   0.0117 |                        0.0546 |
| efficientnet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.0111 |       0.0116 |                   0.0006 |                        0.0489 |
| resnet34_cifar100_bs32_50e_1gpu     |                  1 | single      |       0.0609 |       0.0582 |                   0.0027 |                        0.0466 |


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
| gpt2_large_wiki_bs8_2gpu       |                  2 | gpu_a       |                  95.7253 |                   79.1075 |                              99 |                          100 |                          28330 |                             16.6178 |                                   0.1736 |
| xlnet_base_cased_wiki_bs8_2gpu |                  2 | gpu_a       |                  91.9026 |                   86.2802 |                              93 |                          100 |                           8988 |                              5.6224 |                                   0.0612 |
| gpt2_large_wiki_bs8_2gpu       |                  2 | gpu_b       |                  91.2877 |                   76.3011 |                              98 |                          100 |                          16458 |                             14.9866 |                                   0.1642 |
| unet_voc_1gpu                  |                  1 | single      |                  88.3291 |                   85.6866 |                              99 |                          100 |                           5636 |                              2.6425 |                                   0.0299 |
| xception_imagenet_bs128_1gpu   |                  1 | single      |                  86.6394 |                   86.097  |                              84 |                          100 |                          21004 |                              0.5424 |                                   0.0063 |
| vgg16_imagenet_bs128_1gpu      |                  1 | single      |                  86.3911 |                   85.2857 |                              84 |                          100 |                          21668 |                              1.1054 |                                   0.0128 |
| vgg16_imagenet_bs32_1gpu       |                  1 | single      |                  86.0312 |                   84.203  |                              86 |                           92 |                           6680 |                              1.8282 |                                   0.0213 |
| vgg16_imagenet_bs64_1gpu       |                  1 | single      |                  86.0198 |                   84.5338 |                              87 |                           92 |                          11776 |                              1.486  |                                   0.0173 |
| xception_imagenet_bs64_1gpu    |                  1 | single      |                  85.8712 |                   85.2537 |                              88 |                           92 |                          10978 |                              0.6175 |                                   0.0072 |
| xception_imagenet_bs32_1gpu    |                  1 | single      |                  85.1188 |                   84.9701 |                              85 |                           91 |                           5922 |                              0.1487 |                                   0.0017 |


## Profile score component breakdown

`profile_stat_score` is the equal-weight average of mean, median, mode, and max from the extracted solo-profile CSVs. It is not the AEGIS risk formula. `aegis_profile_risk` is only available when mean, median, p95, and EWMA are present.

| metric   | stat               |   n |   mean_200s |   mean_full |   mean_abs_error |   median_abs_error |   p95_abs_error |   mean_relative_error |
|:---------|:-------------------|----:|------------:|------------:|-----------------:|-------------------:|----------------:|----------------------:|
| smact    | mean               |  55 |      0.408  |      0.4239 |           0.0208 |             0.0039 |          0.1478 |                0.035  |
| smact    | median             |  55 |      0.4339 |      0.4383 |           0.0095 |             0.002  |          0.0594 |                0.0217 |
| smact    | mode               |  55 |      0.3036 |      0.4064 |           0.1115 |             0.002  |          0.9592 |                0.1545 |
| smact    | max                |  55 |      0.5057 |      0.5173 |           0.0117 |             0.002  |          0.0363 |                0.0296 |
| smact    | profile_stat_score |  55 |      0.4128 |      0.4465 |           0.0365 |             0.0036 |          0.2939 |                0.0551 |
| smact    | p95                |  55 |      0.4798 |      0.4821 |           0.0051 |             0.0016 |          0.0095 |                0.0112 |
| smact    | ewma               |  55 |      0.3667 |      0.3628 |           0.0153 |             0.0082 |          0.053  |                0.0365 |
| smact    | aegis_profile_risk |  55 |      0.4221 |      0.4268 |           0.0108 |             0.0031 |          0.0663 |                0.0215 |
| smocc    | mean               |  55 |      0.1915 |      0.1968 |           0.0074 |             0.0017 |          0.045  |                0.0345 |
| smocc    | median             |  55 |      0.2009 |      0.2019 |           0.0032 |             0.001  |          0.0159 |                0.0223 |
| smocc    | mode               |  55 |      0.1647 |      0.2026 |           0.0399 |             0.001  |          0.3052 |                0.1543 |
| smocc    | max                |  55 |      0.2384 |      0.2433 |           0.0049 |             0.001  |          0.0146 |                0.0257 |
| smocc    | profile_stat_score |  55 |      0.1989 |      0.2111 |           0.0131 |             0.0016 |          0.0878 |                0.0541 |
| smocc    | p95                |  55 |      0.2265 |      0.2274 |           0.0024 |             0.001  |          0.0076 |                0.0119 |
| smocc    | ewma               |  55 |      0.1709 |      0.1681 |           0.0066 |             0.0037 |          0.0185 |                0.036  |
| smocc    | aegis_profile_risk |  55 |      0.1975 |      0.1986 |           0.0041 |             0.0014 |          0.0191 |                0.0215 |
| drama    | mean               |  55 |      0.1678 |      0.1704 |           0.0056 |             0.0018 |          0.0285 |                0.0387 |
| drama    | median             |  55 |      0.1729 |      0.1729 |           0.0017 |             0      |          0.0046 |                0.0225 |
| drama    | mode               |  55 |      0.1587 |      0.1723 |           0.0169 |             0.001  |          0.138  |                0.1298 |
| drama    | max                |  55 |      0.2086 |      0.2118 |           0.0032 |             0.001  |          0.0148 |                0.0213 |
| drama    | profile_stat_score |  55 |      0.177  |      0.1819 |           0.0059 |             0.0011 |          0.0453 |                0.0437 |
| drama    | p95                |  55 |      0.1982 |      0.1988 |           0.0024 |             0.001  |          0.0093 |                0.0238 |
| drama    | ewma               |  55 |      0.149  |      0.1447 |           0.0067 |             0.0037 |          0.0204 |                0.0422 |
| drama    | aegis_profile_risk |  55 |      0.172  |      0.1717 |           0.0035 |             0.0016 |          0.0114 |                0.0254 |


## Notes for paper analysis

- `lucid_style_class_200s` is a Lucid-style profile class, not an exact Lucid reproduction.
- `profile_stat_score` uses equal weights over mean, median, mode, and max from extracted solo-profile CSVs.
- `profile_stat_score` is per metric/GPU/window, not a workload-level AEGIS risk.
- `aegis_profile_risk` should only be used when mean, median, p95, and EWMA are available.
- For activity metrics on 2-GPU workloads, inspect `gpu_a` and `gpu_b` separately.
- For memory footprint on 2-GPU workloads, use sum columns when reasoning about total memory demand.
- Large 200s-vs-full mismatch indicates that a short profiling window may not represent the full run.
