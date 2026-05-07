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
| xception_imagenet_bs128_1gpu |                  1 | single      |                            1      |                     2 | Jumbo                    |
| vgg16_imagenet_bs64_1gpu     |                  1 | single      |                            1      |                     2 | Jumbo                    |
| resnet50_imagenet_bs64_1gpu  |                  1 | single      |                            1      |                     2 | Jumbo                    |
| xception_imagenet_bs64_1gpu  |                  1 | single      |                            0.9636 |                     2 | Jumbo                    |
| gpt2_large_wiki_bs8_2gpu     |                  2 | gpu_a       |                            0.949  |                     2 | Jumbo                    |
| xception_imagenet_bs32_1gpu  |                  1 | single      |                            0.9261 |                     2 | Jumbo                    |
| vgg16_imagenet_bs32_1gpu     |                  1 | single      |                            0.9037 |                     2 | Jumbo                    |
| resnet50_imagenet_bs32_1gpu  |                  1 | single      |                            0.8942 |                     2 | Jumbo                    |
| vgg16_imagenet_bs128_1gpu    |                  1 | single      |                            0.8693 |                     2 | Jumbo                    |


## Coarse resource labels

| coarse_resource_label   |   count |
|:------------------------|--------:|
| light                   |      50 |


## Largest 200s-vs-full mismatches


### SMACT mean

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.6758 |       0.9408 |                   0.265  |                        0.2817 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.6088 |       0.7885 |                   0.1797 |                        0.2279 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.6432 |       0.8329 |                   0.1897 |                        0.2277 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.7255 |       0.9208 |                   0.1953 |                        0.2121 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.7169 |       0.8616 |                   0.1447 |                        0.168  |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1371 |       0.1188 |                   0.0183 |                        0.1539 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.7345 |       0.8177 |                   0.0832 |                        0.1018 |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.7274 |       0.805  |                   0.0776 |                        0.0964 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0693 |       0.0752 |                   0.0058 |                        0.0776 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.1093 |       0.1185 |                   0.0092 |                        0.0775 |


### SMACT median

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0965 |        0.13  |                   0.0335 |                        0.2577 |
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.099  |        0.083 |                   0.016  |                        0.1928 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.748  |        0.913 |                   0.165  |                        0.1807 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.116  |        0.102 |                   0.014  |                        0.1373 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.837  |        0.957 |                   0.12   |                        0.1254 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.812  |        0.889 |                   0.077  |                        0.0866 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.91   |        0.955 |                   0.045  |                        0.0471 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.677  |        0.704 |                   0.027  |                        0.0384 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.2125 |        0.208 |                   0.0045 |                        0.0216 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.934  |        0.952 |                   0.018  |                        0.0189 |


### SMACT mode

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_base_wiki_bs32_1gpu         |                  1 | single      |            0 |        0.957 |                    0.957 |                             1 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |            0 |        0.964 |                    0.964 |                             1 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |            0 |        0.958 |                    0.958 |                             1 |
| inception_imagenet_bs128_1gpu    |                  1 | single      |            0 |        0.661 |                    0.661 |                             1 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |            0 |        0.962 |                    0.962 |                             1 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |            0 |        0.962 |                    0.962 |                             1 |
| efficientnet_imagenet_bs64_1gpu  |                  1 | single      |            0 |        0.63  |                    0.63  |                             1 |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |            0 |        0.607 |                    0.607 |                             1 |
| inception_imagenet_bs32_1gpu     |                  1 | single      |            0 |        0.636 |                    0.636 |                             1 |
| resnet50_imagenet_bs32_1gpu      |                  1 | single      |            0 |        0.663 |                    0.663 |                             1 |


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
| dlrm_criteo_bs32768_1gpu             |                  1 | single      |       0.4762 |       0.6127 |                   0.1364 |                        0.2227 |
| resnet34_cifar100_bs32_50e_1gpu      |                  1 | single      |       0.2099 |       0.201  |                   0.0089 |                        0.0443 |
| mobilenet_imagenet_bs32_1gpu         |                  1 | single      |       0.51   |       0.491  |                   0.019  |                        0.0387 |
| resnet18_cifar100_bs64_20e_1gpu      |                  1 | single      |       0.201  |       0.1937 |                   0.0073 |                        0.0377 |
| resnet18_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.193  |       0.199  |                   0.006  |                        0.0302 |
| efficientnet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.2505 |       0.257  |                   0.0065 |                        0.0253 |
| resnet34_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.198  |       0.2017 |                   0.0037 |                        0.0183 |
| resnet34_cifar100_bs128_50e_1gpu     |                  1 | single      |       0.2867 |       0.2825 |                   0.0041 |                        0.0147 |
| resnet18_cifar100_bs32_50e_1gpu      |                  1 | single      |       0.1924 |       0.195  |                   0.0026 |                        0.0131 |
| xlnet_large_cased_wiki_bs4_2gpu      |                  2 | gpu_a       |       0.906  |       0.8946 |                   0.0113 |                        0.0127 |


### SMACT EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.121  |       0.1031 |                   0.0179 |                        0.1739 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.5784 |       0.5129 |                   0.0655 |                        0.1276 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.7189 |       0.8156 |                   0.0967 |                        0.1186 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.059  |       0.0656 |                   0.0066 |                        0.1008 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.6558 |       0.7256 |                   0.0698 |                        0.0962 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.6226 |       0.6864 |                   0.0638 |                        0.093  |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.738  |       0.8046 |                   0.0666 |                        0.0828 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.1837 |       0.1712 |                   0.0125 |                        0.0727 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.7139 |       0.7658 |                   0.0519 |                        0.0678 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0959 |       0.1025 |                   0.0066 |                        0.0646 |


### SMACT profile stat score

| workload_id                     |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:--------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu        |                  2 | gpu_b       |       0.5802 |       0.9071 |                   0.3269 |                        0.3604 |
| gpt2_large_wiki_bs8_2gpu        |                  2 | gpu_a       |       0.6051 |       0.9122 |                   0.3072 |                        0.3367 |
| gpt2_xl_wiki_bs2_1gpu           |                  1 | single      |       0.6422 |       0.9527 |                   0.3105 |                        0.3259 |
| bert_base_wiki_bs32_1gpu        |                  1 | single      |       0.6327 |       0.9382 |                   0.3054 |                        0.3256 |
| bert_large_wiki_bs8_1gpu        |                  1 | single      |       0.6501 |       0.9514 |                   0.3013 |                        0.3167 |
| xlnet_base_cased_wiki_bs8_2gpu  |                  2 | gpu_a       |       0.6069 |       0.8467 |                   0.2398 |                        0.2832 |
| maskrcnn_coco_bs8_1gpu          |                  1 | single      |       0.5419 |       0.753  |                   0.211  |                        0.2803 |
| inception_imagenet_bs32_1gpu    |                  1 | single      |       0.461  |       0.6282 |                   0.1672 |                        0.2661 |
| efficientnet_imagenet_bs64_1gpu |                  1 | single      |       0.4567 |       0.62   |                   0.1632 |                        0.2633 |
| vgg16_imagenet_bs128_1gpu       |                  1 | single      |       0.6314 |       0.8551 |                   0.2237 |                        0.2616 |


### SMACT AEGIS profile risk

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.7354 |       0.8375 |                   0.1021 |                        0.122  |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.8217 |       0.9166 |                   0.0949 |                        0.1036 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.1121 |       0.1245 |                   0.0124 |                        0.0999 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.7683 |       0.8524 |                   0.0841 |                        0.0987 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.8106 |       0.8896 |                   0.079  |                        0.0889 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.8344 |       0.9113 |                   0.077  |                        0.0845 |
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.0923 |       0.0865 |                   0.0058 |                        0.0669 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1969 |       0.2087 |                   0.0118 |                        0.0566 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0747 |       0.0782 |                   0.0035 |                        0.0443 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.1193 |       0.1145 |                   0.0047 |                        0.0414 |


### SMOCC mean

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2351 |       0.3256 |                   0.0905 |                        0.278  |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.18   |       0.2334 |                   0.0534 |                        0.2286 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.2053 |       0.2659 |                   0.0606 |                        0.2279 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2286 |       0.2896 |                   0.061  |                        0.2107 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.2151 |       0.2593 |                   0.0442 |                        0.1706 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0457 |       0.0398 |                   0.006  |                        0.1498 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.278  |       0.3099 |                   0.0319 |                        0.1029 |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.2769 |       0.3038 |                   0.0269 |                        0.0885 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0571 |       0.0622 |                   0.0051 |                        0.0825 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0345 |       0.0373 |                   0.0028 |                        0.0749 |


### SMOCC median

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |        0.05  |       0.037  |                   0.013  |                        0.3514 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |        0.052 |       0.069  |                   0.017  |                        0.2464 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |        0.221 |       0.267  |                   0.046  |                        0.1723 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |        0.256 |       0.273  |                   0.017  |                        0.0623 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |        0.058 |       0.055  |                   0.003  |                        0.0545 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |        0.294 |       0.307  |                   0.013  |                        0.0423 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |        0.281 |       0.292  |                   0.011  |                        0.0377 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |        0.329 |       0.3405 |                   0.0115 |                        0.0338 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |        0.263 |       0.27   |                   0.007  |                        0.0259 |
| resnet18_cifar100_bs64_20e_1gpu  |                  1 | single      |        0.065 |       0.066  |                   0.001  |                        0.0152 |


### SMOCC mode

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_base_wiki_bs32_1gpu         |                  1 | single      |            0 |        0.304 |                    0.304 |                             1 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |            0 |        0.257 |                    0.257 |                             1 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |            0 |        0.271 |                    0.271 |                             1 |
| efficientnet_imagenet_bs64_1gpu  |                  1 | single      |            0 |        0.378 |                    0.378 |                             1 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |            0 |        0.308 |                    0.308 |                             1 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |            0 |        0.319 |                    0.319 |                             1 |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |            0 |        0.389 |                    0.389 |                             1 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |            0 |        0.271 |                    0.271 |                             1 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |            0 |        0.312 |                    0.312 |                             1 |
| resnet50_imagenet_bs128_1gpu     |                  1 | single      |            0 |        0.353 |                    0.353 |                             1 |


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
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1547 |       0.2043 |                   0.0496 |                        0.2427 |
| resnet34_cifar100_bs32_50e_1gpu  |                  1 | single      |       0.0849 |       0.08   |                   0.0049 |                        0.0612 |
| resnet18_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.07   |       0.073  |                   0.003  |                        0.0411 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.282  |       0.294  |                   0.012  |                        0.0408 |
| mobilenet_imagenet_bs32_1gpu     |                  1 | single      |       0.2484 |       0.24   |                   0.0084 |                        0.035  |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.33   |       0.338  |                   0.008  |                        0.0237 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.1133 |       0.111  |                   0.0023 |                        0.0212 |
| resnet18_cifar100_bs64_50e_1gpu  |                  1 | single      |       0.0734 |       0.072  |                   0.0014 |                        0.0194 |
| resnet34_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.08   |       0.0813 |                   0.0013 |                        0.0166 |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.3534 |       0.348  |                   0.0054 |                        0.0155 |


### SMOCC EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0404 |       0.0345 |                   0.0059 |                        0.17   |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.2812 |       0.2457 |                   0.0355 |                        0.1445 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2489 |       0.2818 |                   0.0329 |                        0.1167 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0292 |       0.0325 |                   0.0033 |                        0.1017 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.2096 |       0.2318 |                   0.0222 |                        0.0957 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.1843 |       0.2032 |                   0.019  |                        0.0932 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2327 |       0.253  |                   0.0204 |                        0.0806 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0496 |       0.0539 |                   0.0043 |                        0.0805 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.2147 |       0.2305 |                   0.0158 |                        0.0684 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0714 |       0.067  |                   0.0044 |                        0.0653 |


### SMOCC profile stat score

| workload_id                     |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:--------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu        |                  2 | gpu_b       |       0.1748 |       0.2686 |                   0.0938 |                        0.3494 |
| bert_base_wiki_bs32_1gpu        |                  1 | single      |       0.197  |       0.2883 |                   0.0913 |                        0.3167 |
| gpt2_xl_wiki_bs2_1gpu           |                  1 | single      |       0.2395 |       0.3449 |                   0.1054 |                        0.3055 |
| gpt2_large_wiki_bs8_2gpu        |                  2 | gpu_a       |       0.1968 |       0.2827 |                   0.0859 |                        0.3038 |
| bert_large_wiki_bs8_1gpu        |                  1 | single      |       0.2131 |       0.2957 |                   0.0825 |                        0.2791 |
| xlnet_base_cased_wiki_bs8_2gpu  |                  2 | gpu_a       |       0.2343 |       0.3245 |                   0.0902 |                        0.2781 |
| efficientnet_imagenet_bs64_1gpu |                  1 | single      |       0.2764 |       0.375  |                   0.0985 |                        0.2628 |
| xlnet_large_cased_wiki_bs4_2gpu |                  2 | gpu_a       |       0.2392 |       0.3242 |                   0.085  |                        0.2621 |
| mobilenet_imagenet_bs64_1gpu    |                  1 | single      |       0.2131 |       0.2871 |                   0.074  |                        0.2578 |
| vgg16_imagenet_bs128_1gpu       |                  1 | single      |       0.3249 |       0.4353 |                   0.1104 |                        0.2535 |


### SMOCC AEGIS profile risk

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.2191 |       0.2492 |                   0.0301 |                        0.1207 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2985 |       0.3336 |                   0.0351 |                        0.1052 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0597 |       0.0663 |                   0.0066 |                        0.0999 |
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.0465 |       0.0423 |                   0.0042 |                        0.0981 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.24   |       0.2654 |                   0.0254 |                        0.0959 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2696 |       0.2922 |                   0.0226 |                        0.0774 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.2478 |       0.2677 |                   0.0199 |                        0.0742 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0647 |       0.0697 |                   0.0049 |                        0.071  |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.2938 |       0.307  |                   0.0132 |                        0.043  |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0377 |       0.0392 |                   0.0015 |                        0.0389 |


### DRAMA mean

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.1556 |       0.2118 |                   0.0563 |                        0.2655 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.1255 |       0.1596 |                   0.0341 |                        0.2136 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.1225 |       0.1555 |                   0.033  |                        0.2123 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.167  |       0.2117 |                   0.0446 |                        0.2109 |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.1133 |       0.136  |                   0.0227 |                        0.1669 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0266 |       0.0231 |                   0.0035 |                        0.1526 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0027 |       0.0031 |                   0.0004 |                        0.128  |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.1902 |       0.2115 |                   0.0213 |                        0.1008 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.1871 |       0.2074 |                   0.0203 |                        0.0981 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0017 |       0.0018 |                   0.0001 |                        0.0567 |


### DRAMA median

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.002  |        0.004 |                   0.002  |                        0.5    |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.136  |        0.166 |                   0.03   |                        0.1807 |
| efficientnet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.008  |        0.009 |                   0.001  |                        0.1111 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.008  |        0.009 |                   0.001  |                        0.1111 |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_b       |       0.152  |        0.16  |                   0.008  |                        0.05   |
| resnet34_cifar100_bs32_20e_1gpu     |                  1 | single      |       0.0525 |        0.051 |                   0.0015 |                        0.0294 |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.153  |        0.157 |                   0.004  |                        0.0255 |
| maskrcnn_coco_bs8_1gpu              |                  1 | single      |       0.388  |        0.398 |                   0.01   |                        0.0251 |
| resnet18_cifar100_bs32_50e_1gpu     |                  1 | single      |       0.047  |        0.048 |                   0.001  |                        0.0208 |
| resnet34_cifar100_bs32_50e_1gpu     |                  1 | single      |       0.05   |        0.051 |                   0.001  |                        0.0196 |


### DRAMA mode

| workload_id                     |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:--------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_base_wiki_bs32_1gpu        |                  1 | single      |            0 |        0.135 |                    0.135 |                             1 |
| bert_large_wiki_bs8_1gpu        |                  1 | single      |            0 |        0.153 |                    0.153 |                             1 |
| maskrcnn_coco_bs8_1gpu          |                  1 | single      |            0 |        0.414 |                    0.414 |                             1 |
| gpt2_large_wiki_bs8_2gpu        |                  2 | gpu_a       |            0 |        0.214 |                    0.214 |                             1 |
| gpt2_xl_wiki_bs2_1gpu           |                  1 | single      |            0 |        0.12  |                    0.12  |                             1 |
| gpt2_large_wiki_bs8_2gpu        |                  2 | gpu_b       |            0 |        0.145 |                    0.145 |                             1 |
| xlnet_large_cased_wiki_bs4_2gpu |                  2 | gpu_a       |            0 |        0.21  |                    0.21  |                             1 |
| xlnet_base_cased_wiki_bs8_2gpu  |                  2 | gpu_a       |            0 |        0.205 |                    0.205 |                             1 |
| unet_voc_1gpu                   |                  1 | single      |            0 |        0.404 |                    0.404 |                             1 |
| resnet50_imagenet_bs128_1gpu    |                  1 | single      |            0 |        0.488 |                    0.488 |                             1 |


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
| resnet18_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.061  |       0.0671 |                   0.0061 |                        0.0909 |
| resnet18_cifar100_bs64_50e_1gpu      |                  1 | single      |       0.069  |       0.064  |                   0.005  |                        0.0781 |
| efficientnet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0233 |       0.025  |                   0.0017 |                        0.068  |
| resnet18_cifar100_bs64_20e_1gpu      |                  1 | single      |       0.0628 |       0.06   |                   0.0028 |                        0.0467 |
| resnet34_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.0774 |       0.081  |                   0.0036 |                        0.0438 |
| resnet18_cifar100_bs32_50e_1gpu      |                  1 | single      |       0.0643 |       0.062  |                   0.0023 |                        0.0379 |


### DRAMA EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0237 |       0.02   |                   0.0037 |                        0.1846 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3343 |       0.2845 |                   0.0498 |                        0.1752 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0024 |       0.0027 |                   0.0003 |                        0.1248 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.1626 |       0.183  |                   0.0204 |                        0.1116 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.062  |       0.0568 |                   0.0053 |                        0.0925 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.1277 |       0.139  |                   0.0113 |                        0.0815 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.1279 |       0.139  |                   0.0111 |                        0.08   |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.1701 |       0.1842 |                   0.0141 |                        0.0766 |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |       0.2518 |       0.235  |                   0.0168 |                        0.0713 |
| mobilenet_imagenet_bs32_1gpu     |                  1 | single      |       0.2053 |       0.1927 |                   0.0127 |                        0.0656 |


### DRAMA profile stat score

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_a       |       0.1595 |       0.2242 |                   0.0647 |                        0.2884 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.1201 |       0.1684 |                   0.0483 |                        0.2866 |
| gpt2_large_wiki_bs8_2gpu         |                  2 | gpu_b       |       0.1169 |       0.1637 |                   0.0468 |                        0.2858 |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.1563 |       0.2156 |                   0.0593 |                        0.2752 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0029 |       0.004  |                   0.0011 |                        0.273  |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.1623 |       0.2226 |                   0.0603 |                        0.271  |
| bert_base_wiki_bs32_1gpu         |                  1 | single      |       0.1093 |       0.1493 |                   0.0399 |                        0.2675 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3183 |       0.4296 |                   0.1113 |                        0.2591 |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |       0.2304 |       0.3099 |                   0.0795 |                        0.2565 |
| unet_voc_1gpu                    |                  1 | single      |       0.3058 |       0.4109 |                   0.1051 |                        0.2558 |


### DRAMA AEGIS profile risk

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.003  |       0.0037 |                   0.0007 |                        0.1847 |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.2114 |       0.2415 |                   0.0301 |                        0.1245 |
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |       0.036  |       0.0395 |                   0.0035 |                        0.0891 |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_b       |       0.147  |       0.1606 |                   0.0136 |                        0.0847 |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.1478 |       0.1612 |                   0.0134 |                        0.0833 |
| gpt2_large_wiki_bs8_2gpu            |                  2 | gpu_a       |       0.199  |       0.2137 |                   0.0147 |                        0.0689 |
| bert_base_wiki_bs32_1gpu            |                  1 | single      |       0.1354 |       0.1437 |                   0.0083 |                        0.0575 |
| efficientnet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.011  |       0.0116 |                   0.0006 |                        0.055  |
| resnet18_cifar100_bs32_20e_1gpu     |                  1 | single      |       0.0494 |       0.0516 |                   0.0022 |                        0.0432 |
| resnet18_cifar100_bs64_50e_1gpu     |                  1 | single      |       0.0526 |       0.0506 |                   0.0021 |                        0.0411 |


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
| gpt2_large_wiki_bs8_2gpu       |                  2 | gpu_a       |                  95.5178 |                   74.8595 |                              99 |                          100 |                          28330 |                             20.6583 |                                   0.2163 |
| xlnet_base_cased_wiki_bs8_2gpu |                  2 | gpu_a       |                  91.7022 |                   82.7582 |                              93 |                          100 |                           8988 |                              8.9439 |                                   0.0975 |
| gpt2_large_wiki_bs8_2gpu       |                  2 | gpu_b       |                  91.0897 |                   72.3459 |                              98 |                          100 |                          16458 |                             18.7438 |                                   0.2058 |
| unet_voc_1gpu                  |                  1 | single      |                  88.1983 |                   84.2015 |                              99 |                          100 |                           5636 |                              3.9968 |                                   0.0453 |
| xception_imagenet_bs128_1gpu   |                  1 | single      |                  86.5031 |                   83.9104 |                              84 |                          100 |                          21004 |                              2.5927 |                                   0.03   |
| vgg16_imagenet_bs128_1gpu      |                  1 | single      |                  86.1971 |                   82.7519 |                              84 |                          100 |                          21668 |                              3.4452 |                                   0.04   |
| vgg16_imagenet_bs32_1gpu       |                  1 | single      |                  85.9037 |                   82.2105 |                              86 |                           92 |                           6680 |                              3.6931 |                                   0.043  |
| vgg16_imagenet_bs64_1gpu       |                  1 | single      |                  85.8903 |                   82.7068 |                              87 |                           92 |                          11776 |                              3.1835 |                                   0.0371 |
| xception_imagenet_bs64_1gpu    |                  1 | single      |                  85.7403 |                   83.3881 |                              88 |                           92 |                          10978 |                              2.3523 |                                   0.0274 |
| xception_imagenet_bs32_1gpu    |                  1 | single      |                  84.9492 |                   82.3955 |                              85 |                           91 |                           5922 |                              2.5537 |                                   0.0301 |


## Profile score component breakdown

`profile_stat_score` is the equal-weight average of mean, median, mode, and max from the extracted solo-profile CSVs. It is not the AEGIS risk formula. `aegis_profile_risk` is only available when mean, median, p95, and EWMA are present.

| metric   | stat               |   n |   mean_200s |   mean_full |   mean_abs_error |   median_abs_error |   p95_abs_error |   mean_relative_error |
|:---------|:-------------------|----:|------------:|------------:|-----------------:|-------------------:|----------------:|----------------------:|
| smact    | mean               |  55 |      0.3945 |      0.4223 |           0.0288 |             0.0066 |          0.1827 |                0.0481 |
| smact    | median             |  55 |      0.4307 |      0.4381 |           0.0118 |             0.002  |          0.0602 |                0.0244 |
| smact    | mode               |  55 |      0.1633 |      0.4022 |           0.241  |             0.002  |          0.9592 |                0.3682 |
| smact    | max                |  55 |      0.5055 |      0.5173 |           0.0119 |             0.002  |          0.0363 |                0.0298 |
| smact    | profile_stat_score |  55 |      0.3735 |      0.445  |           0.0721 |             0.0064 |          0.306  |                0.1072 |
| smact    | p95                |  55 |      0.4797 |      0.4819 |           0.0051 |             0.0016 |          0.0096 |                0.0113 |
| smact    | ewma               |  55 |      0.3613 |      0.3617 |           0.0152 |             0.0066 |          0.0658 |                0.0368 |
| smact    | aegis_profile_risk |  55 |      0.4166 |      0.426  |           0.0119 |             0.0027 |          0.0806 |                0.0228 |
| smocc    | mean               |  55 |      0.1855 |      0.196  |           0.0109 |             0.0034 |          0.0555 |                0.048  |
| smocc    | median             |  55 |      0.2002 |      0.2018 |           0.0034 |             0.001  |          0.017  |                0.0231 |
| smocc    | mode               |  55 |      0.1153 |      0.2026 |           0.089  |             0.001  |          0.3605 |                0.3057 |
| smocc    | max                |  55 |      0.2384 |      0.2433 |           0.0049 |             0.001  |          0.0146 |                0.0257 |
| smocc    | profile_stat_score |  55 |      0.1849 |      0.2109 |           0.0265 |             0.0032 |          0.0988 |                0.0936 |
| smocc    | p95                |  55 |      0.2261 |      0.2274 |           0.0025 |             0.001  |          0.0081 |                0.0123 |
| smocc    | ewma               |  55 |      0.1686 |      0.1677 |           0.0061 |             0.0033 |          0.0209 |                0.0355 |
| smocc    | aegis_profile_risk |  55 |      0.1951 |      0.1982 |           0.0043 |             0.0015 |          0.0235 |                0.0225 |
| drama    | mean               |  55 |      0.1624 |      0.1698 |           0.0077 |             0.0017 |          0.0333 |                0.0474 |
| drama    | median             |  55 |      0.1722 |      0.1729 |           0.0019 |             0.001  |          0.0086 |                0.0232 |
| drama    | mode               |  55 |      0.1161 |      0.1723 |           0.0585 |             0.001  |          0.3452 |                0.2587 |
| drama    | max                |  55 |      0.2086 |      0.2118 |           0.0032 |             0.001  |          0.0148 |                0.0213 |
| drama    | profile_stat_score |  55 |      0.1648 |      0.1817 |           0.0173 |             0.0017 |          0.0886 |                0.0793 |
| drama    | p95                |  55 |      0.198  |      0.1987 |           0.0025 |             0.001  |          0.0093 |                0.024  |
| drama    | ewma               |  55 |      0.1471 |      0.1444 |           0.006  |             0.0031 |          0.0187 |                0.042  |
| drama    | aegis_profile_risk |  55 |      0.1699 |      0.1715 |           0.0032 |             0.0016 |          0.0135 |                0.026  |


## Notes for paper analysis

- `lucid_style_class_200s` is a Lucid-style profile class, not an exact Lucid reproduction.
- `profile_stat_score` uses equal weights over mean, median, mode, and max from extracted solo-profile CSVs.
- `profile_stat_score` is per metric/GPU/window, not a workload-level AEGIS risk.
- `aegis_profile_risk` should only be used when mean, median, p95, and EWMA are available.
- For activity metrics on 2-GPU workloads, inspect `gpu_a` and `gpu_b` separately.
- For memory footprint on 2-GPU workloads, use sum columns when reasoning about total memory demand.
- Large 200s-vs-full mismatch indicates that a short profiling window may not represent the full run.
