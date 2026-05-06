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


### SMACT mean

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.6758 |       0.9408 |                   0.265  |                        0.2817 |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.7255 |       0.9208 |                   0.1953 |                        0.2121 |
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |       0.1395 |       0.1192 |                   0.0203 |                        0.17   |
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.1093 |       0.1185 |                   0.0092 |                        0.0775 |
| mobilenet_cifar100_bs32_20e_1gpu    |                  1 | single      |       0.0715 |       0.0757 |                   0.0042 |                        0.0555 |
| mobilenet_cifar100_bs32_50e_1gpu    |                  1 | single      |       0.0878 |       0.0832 |                   0.0046 |                        0.055  |
| resnet34_cifar100_bs128_50e_1gpu    |                  1 | single      |       0.2148 |       0.2042 |                   0.0106 |                        0.0517 |
| maskrcnn_coco_bs8_1gpu              |                  1 | single      |       0.6879 |       0.6548 |                   0.0331 |                        0.0506 |
| efficientnet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.1525 |       0.1599 |                   0.0074 |                        0.0462 |
| unet_voc_1gpu                       |                  1 | single      |       0.6109 |       0.6363 |                   0.0254 |                        0.0399 |


### SMACT median

| workload_id                       |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:----------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu  |                  1 | single      |       0.0965 |       0.13   |                   0.0335 |                        0.2577 |
| mobilenet_cifar100_bs64_20e_1gpu  |                  1 | single      |       0.1245 |       0.1035 |                   0.021  |                        0.2029 |
| mobilenet_cifar100_bs32_50e_1gpu  |                  1 | single      |       0.099  |       0.083  |                   0.016  |                        0.1928 |
| bert_large_wiki_bs8_1gpu          |                  1 | single      |       0.91   |       0.955  |                   0.045  |                        0.0471 |
| resnet34_cifar100_bs128_50e_1gpu  |                  1 | single      |       0.215  |       0.208  |                   0.007  |                        0.0337 |
| mobilenet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.158  |       0.155  |                   0.003  |                        0.0194 |
| gpt2_xl_wiki_bs2_1gpu             |                  1 | single      |       0.934  |       0.952  |                   0.018  |                        0.0189 |
| mobilenet_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.069  |       0.07   |                   0.001  |                        0.0143 |
| resnet18_cifar100_bs64_50e_1gpu   |                  1 | single      |       0.177  |       0.175  |                   0.002  |                        0.0114 |
| resnet50_imagenet_bs32_1gpu       |                  1 | single      |       0.6715 |       0.665  |                   0.0065 |                        0.0098 |


### SMACT mode

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_large_wiki_bs8_1gpu         |                  1 | single      |        0     |        0.964 |                    0.964 |                        1      |
| inception_imagenet_bs32_1gpu     |                  1 | single      |        0     |        0.636 |                    0.636 |                        1      |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |        0     |        0.607 |                    0.607 |                        1      |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |        0     |        0.958 |                    0.958 |                        1      |
| inception_imagenet_bs128_1gpu    |                  1 | single      |        0     |        0.661 |                    0.661 |                        1      |
| resnet50_imagenet_bs32_1gpu      |                  1 | single      |        0     |        0.663 |                    0.663 |                        1      |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |        0     |        0.531 |                    0.531 |                        1      |
| vgg16_imagenet_bs128_1gpu        |                  1 | single      |        0     |        0.851 |                    0.851 |                        1      |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |        0.142 |        0.099 |                    0.043 |                        0.4343 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |        0.091 |        0.144 |                    0.053 |                        0.3681 |


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
| resnet18_cifar100_bs64_20e_1gpu      |                  1 | single      |       0.201  |       0.1943 |                   0.0067 |                        0.0342 |
| resnet18_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.193  |       0.199  |                   0.006  |                        0.0302 |
| efficientnet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.2505 |       0.257  |                   0.0065 |                        0.0255 |
| resnet34_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.198  |       0.2022 |                   0.0042 |                        0.0208 |
| resnet34_cifar100_bs128_50e_1gpu     |                  1 | single      |       0.2866 |       0.2828 |                   0.0038 |                        0.0134 |
| xlnet_large_cased_wiki_bs4_2gpu      |                  2 | gpu_a       |       0.9058 |       0.895  |                   0.0107 |                        0.012  |
| resnet18_cifar100_bs128_50e_1gpu     |                  1 | single      |       0.2506 |       0.2536 |                   0.003  |                        0.0118 |


### SMACT EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.6042 |       0.5143 |                   0.0899 |                        0.1749 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1203 |       0.1032 |                   0.0171 |                        0.1659 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.7189 |       0.8156 |                   0.0967 |                        0.1186 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0596 |       0.0658 |                   0.0061 |                        0.0933 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.738  |       0.8046 |                   0.0666 |                        0.0828 |
| mobilenet_imagenet_bs128_1gpu    |                  1 | single      |       0.4397 |       0.4121 |                   0.0275 |                        0.0668 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0959 |       0.1025 |                   0.0066 |                        0.0646 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.2208 |       0.2076 |                   0.0132 |                        0.0637 |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |       0.5398 |       0.5075 |                   0.0322 |                        0.0635 |
| resnet50_imagenet_bs128_1gpu     |                  1 | single      |       0.6331 |       0.5955 |                   0.0376 |                        0.0632 |


### SMACT profile stat score

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


### SMACT AEGIS profile risk

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.8217 |       0.9166 |                   0.0949 |                        0.1036 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.1121 |       0.1245 |                   0.0124 |                        0.0999 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.8344 |       0.9113 |                   0.077  |                        0.0845 |
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.0926 |       0.0866 |                   0.006  |                        0.0692 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.1232 |       0.1154 |                   0.0077 |                        0.0671 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.1975 |       0.2089 |                   0.0113 |                        0.0543 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.6964 |       0.6663 |                   0.0301 |                        0.0452 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.2343 |       0.2257 |                   0.0086 |                        0.0383 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0754 |       0.0784 |                   0.0029 |                        0.0374 |
| mobilenet_imagenet_bs32_1gpu     |                  1 | single      |       0.4623 |       0.4521 |                   0.0102 |                        0.0226 |


### SMOCC mean

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2351 |       0.3256 |                   0.0905 |                        0.278  |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2286 |       0.2896 |                   0.061  |                        0.2107 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0465 |       0.0399 |                   0.0066 |                        0.1663 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0571 |       0.0622 |                   0.0051 |                        0.0825 |
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.0437 |       0.0413 |                   0.0024 |                        0.058  |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3342 |       0.316  |                   0.0182 |                        0.0575 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0356 |       0.0375 |                   0.002  |                        0.0523 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0837 |       0.0799 |                   0.0038 |                        0.0479 |
| unet_voc_1gpu                    |                  1 | single      |       0.3039 |       0.3177 |                   0.0138 |                        0.0434 |
| inception_imagenet_bs128_1gpu    |                  1 | single      |       0.2911 |       0.3037 |                   0.0127 |                        0.0417 |


### SMOCC median

| workload_id                       |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:----------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs32_50e_1gpu  |                  1 | single      |       0.05   |        0.037 |                   0.013  |                        0.3514 |
| mobilenet_cifar100_bs64_50e_1gpu  |                  1 | single      |       0.052  |        0.069 |                   0.017  |                        0.2464 |
| mobilenet_cifar100_bs64_20e_1gpu  |                  1 | single      |       0.061  |        0.055 |                   0.006  |                        0.1091 |
| gpt2_xl_wiki_bs2_1gpu             |                  1 | single      |       0.294  |        0.307 |                   0.013  |                        0.0423 |
| bert_large_wiki_bs8_1gpu          |                  1 | single      |       0.281  |        0.292 |                   0.011  |                        0.0377 |
| resnet34_cifar100_bs128_50e_1gpu  |                  1 | single      |       0.084  |        0.082 |                   0.002  |                        0.0244 |
| mobilenet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.093  |        0.091 |                   0.002  |                        0.022  |
| bert_base_wiki_bs32_1gpu          |                  1 | single      |       0.2705 |        0.276 |                   0.0055 |                        0.0199 |
| resnet34_cifar100_bs64_20e_1gpu   |                  1 | single      |       0.074  |        0.073 |                   0.001  |                        0.0137 |
| resnet18_cifar100_bs128_50e_1gpu  |                  1 | single      |       0.08   |        0.079 |                   0.001  |                        0.0127 |


### SMOCC mode

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_large_wiki_bs8_1gpu         |                  1 | single      |        0     |        0.257 |                    0.257 |                        1      |
| efficientnet_imagenet_bs128_1gpu |                  1 | single      |        0     |        0.389 |                    0.389 |                        1      |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |        0     |        0.308 |                    0.308 |                        1      |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |        0     |        0.291 |                    0.291 |                        1      |
| unet_voc_1gpu                    |                  1 | single      |        0     |        0.333 |                    0.333 |                        1      |
| vgg16_imagenet_bs128_1gpu        |                  1 | single      |        0     |        0.425 |                    0.425 |                        1      |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |        0.05  |        0.078 |                    0.028 |                        0.359  |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |        0.094 |        0.082 |                    0.012 |                        0.1463 |
| efficientnet_imagenet_bs64_1gpu  |                  1 | single      |        0.338 |        0.378 |                    0.04  |                        0.1058 |
| resnet34_cifar100_bs32_50e_1gpu  |                  1 | single      |        0.079 |        0.072 |                    0.007 |                        0.0972 |


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
| resnet34_cifar100_bs32_50e_1gpu  |                  1 | single      |       0.0849 |       0.08   |                   0.0048 |                        0.0606 |
| mobilenet_imagenet_bs32_1gpu     |                  1 | single      |       0.2484 |       0.24   |                   0.0084 |                        0.035  |
| resnet18_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.0705 |       0.073  |                   0.0025 |                        0.0342 |
| xlnet_large_cased_wiki_bs4_2gpu  |                  2 | gpu_a       |       0.3553 |       0.348  |                   0.0073 |                        0.021  |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.1133 |       0.111  |                   0.0023 |                        0.0207 |
| resnet34_cifar100_bs32_20e_1gpu  |                  1 | single      |       0.08   |       0.0816 |                   0.0016 |                        0.0196 |
| resnet18_cifar100_bs64_50e_1gpu  |                  1 | single      |       0.0734 |       0.0721 |                   0.0013 |                        0.018  |
| xlnet_base_cased_wiki_bs8_2gpu   |                  2 | gpu_a       |       0.332  |       0.338  |                   0.006  |                        0.0178 |
| resnet18_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0945 |       0.0957 |                   0.0012 |                        0.0131 |


### SMOCC EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.2935 |       0.2461 |                   0.0474 |                        0.1926 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0402 |       0.0345 |                   0.0056 |                        0.1629 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2489 |       0.2818 |                   0.0329 |                        0.1167 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.0295 |       0.0326 |                   0.003  |                        0.0928 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2327 |       0.253  |                   0.0204 |                        0.0806 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0496 |       0.0539 |                   0.0043 |                        0.0805 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.086  |       0.0811 |                   0.0049 |                        0.0604 |
| mobilenet_imagenet_bs128_1gpu    |                  1 | single      |       0.2365 |       0.2231 |                   0.0134 |                        0.0601 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.0536 |       0.0506 |                   0.003  |                        0.0599 |
| resnet50_imagenet_bs128_1gpu     |                  1 | single      |       0.3281 |       0.3096 |                   0.0185 |                        0.0598 |


### SMOCC profile stat score

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


### SMOCC AEGIS profile risk

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.2985 |       0.3336 |                   0.0351 |                        0.1052 |
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.0467 |       0.0424 |                   0.0043 |                        0.101  |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0597 |       0.0663 |                   0.0066 |                        0.0999 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.2696 |       0.2922 |                   0.0226 |                        0.0774 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.065  |       0.0697 |                   0.0047 |                        0.0681 |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3385 |       0.3226 |                   0.0159 |                        0.0493 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.0642 |       0.0614 |                   0.0028 |                        0.0455 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0918 |       0.0885 |                   0.0033 |                        0.0368 |
| mobilenet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.038  |       0.0393 |                   0.0012 |                        0.0317 |
| resnet34_cifar100_bs32_50e_1gpu  |                  1 | single      |       0.0753 |       0.0735 |                   0.0018 |                        0.0241 |


### DRAMA mean

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.1556 |       0.2118 |                   0.0563 |                        0.2655 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.1225 |       0.1555 |                   0.033  |                        0.2123 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0271 |       0.0232 |                   0.004  |                        0.1716 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0027 |       0.0031 |                   0.0004 |                        0.128  |
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3972 |       0.3696 |                   0.0276 |                        0.0746 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0727 |       0.0682 |                   0.0044 |                        0.0652 |
| resnet18_cifar100_bs64_50e_1gpu  |                  1 | single      |       0.0518 |       0.0492 |                   0.0027 |                        0.0546 |
| mobilenet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.0019 |       0.0018 |                   0.0001 |                        0.0523 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.003  |       0.0029 |                   0.0001 |                        0.0504 |
| resnet34_cifar100_bs32_50e_1gpu  |                  1 | single      |       0.058  |       0.0552 |                   0.0028 |                        0.0501 |


### DRAMA median

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.002  |        0.004 |                   0.002  |                        0.5    |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.136  |        0.166 |                   0.03   |                        0.1807 |
| efficientnet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.008  |        0.009 |                   0.001  |                        0.1111 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |       0.008  |        0.009 |                   0.001  |                        0.1111 |
| resnet18_cifar100_bs64_50e_1gpu     |                  1 | single      |       0.052  |        0.048 |                   0.004  |                        0.0833 |
| resnet18_cifar100_bs64_20e_1gpu     |                  1 | single      |       0.052  |        0.05  |                   0.002  |                        0.04   |
| resnet34_cifar100_bs128_50e_1gpu    |                  1 | single      |       0.066  |        0.064 |                   0.002  |                        0.0312 |
| resnet34_cifar100_bs32_20e_1gpu     |                  1 | single      |       0.0525 |        0.051 |                   0.0015 |                        0.0294 |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.153  |        0.157 |                   0.004  |                        0.0255 |
| resnet18_cifar100_bs32_50e_1gpu     |                  1 | single      |       0.047  |        0.048 |                   0.001  |                        0.0208 |


### DRAMA mode

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| bert_large_wiki_bs8_1gpu            |                  1 | single      |        0     |        0.153 |                    0.153 |                        1      |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |        0     |        0.12  |                    0.12  |                        1      |
| unet_voc_1gpu                       |                  1 | single      |        0     |        0.404 |                    0.404 |                        1      |
| mobilenet_imagenet_bs64_1gpu        |                  1 | single      |        0     |        0.316 |                    0.316 |                        1      |
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |        0.002 |        0.004 |                    0.002 |                        0.5    |
| resnet34_cifar100_bs64_20e_1gpu     |                  1 | single      |        0.077 |        0.052 |                    0.025 |                        0.4808 |
| efficientnet_cifar100_bs32_20e_1gpu |                  1 | single      |        0.008 |        0.009 |                    0.001 |                        0.1111 |
| efficientnet_cifar100_bs64_20e_1gpu |                  1 | single      |        0.012 |        0.011 |                    0.001 |                        0.0909 |
| resnet34_cifar100_bs32_50e_1gpu     |                  1 | single      |        0.048 |        0.052 |                    0.004 |                        0.0769 |
| maskrcnn_coco_bs8_1gpu              |                  1 | single      |        0.39  |        0.414 |                    0.024 |                        0.058  |


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
| resnet18_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.061  |       0.0677 |                   0.0067 |                        0.099  |
| resnet18_cifar100_bs64_50e_1gpu      |                  1 | single      |       0.069  |       0.064  |                   0.005  |                        0.0781 |
| efficientnet_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0233 |       0.025  |                   0.0017 |                        0.068  |
| resnet18_cifar100_bs64_20e_1gpu      |                  1 | single      |       0.0628 |       0.0601 |                   0.0027 |                        0.0449 |
| resnet34_cifar100_bs32_20e_1gpu      |                  1 | single      |       0.0774 |       0.081  |                   0.0036 |                        0.0438 |
| resnet18_cifar100_bs32_50e_1gpu      |                  1 | single      |       0.0643 |       0.062  |                   0.0023 |                        0.0379 |


### DRAMA EWMA

| workload_id                      |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:---------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| maskrcnn_coco_bs8_1gpu           |                  1 | single      |       0.3486 |       0.2849 |                   0.0638 |                        0.2238 |
| dlrm_criteo_bs32768_1gpu         |                  1 | single      |       0.0237 |       0.02   |                   0.0037 |                        0.1827 |
| mobilenet_cifar100_bs64_50e_1gpu |                  1 | single      |       0.0024 |       0.0027 |                   0.0003 |                        0.1248 |
| gpt2_xl_wiki_bs2_1gpu            |                  1 | single      |       0.1626 |       0.183  |                   0.0204 |                        0.1116 |
| resnet34_cifar100_bs128_50e_1gpu |                  1 | single      |       0.0711 |       0.0649 |                   0.0063 |                        0.0965 |
| bert_large_wiki_bs8_1gpu         |                  1 | single      |       0.1277 |       0.139  |                   0.0113 |                        0.0815 |
| mobilenet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.0028 |       0.0026 |                   0.0002 |                        0.0786 |
| mobilenet_imagenet_bs64_1gpu     |                  1 | single      |       0.2518 |       0.235  |                   0.0168 |                        0.0713 |
| mobilenet_imagenet_bs128_1gpu    |                  1 | single      |       0.2644 |       0.2469 |                   0.0175 |                        0.071  |
| mobilenet_imagenet_bs32_1gpu     |                  1 | single      |       0.2053 |       0.1927 |                   0.0127 |                        0.0656 |


### DRAMA profile stat score

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


### DRAMA AEGIS profile risk

| workload_id                         |   source_gpu_count | gpu_label   |   value_200s |   value_full |   abs_error_200s_vs_full |   relative_error_200s_vs_full |
|:------------------------------------|-------------------:|:------------|-------------:|-------------:|-------------------------:|------------------------------:|
| mobilenet_cifar100_bs64_50e_1gpu    |                  1 | single      |       0.003  |       0.0037 |                   0.0007 |                        0.1847 |
| gpt2_xl_wiki_bs2_1gpu               |                  1 | single      |       0.2114 |       0.2415 |                   0.0301 |                        0.1245 |
| dlrm_criteo_bs32768_1gpu            |                  1 | single      |       0.0361 |       0.0395 |                   0.0034 |                        0.0864 |
| bert_large_wiki_bs8_1gpu            |                  1 | single      |       0.1478 |       0.1612 |                   0.0134 |                        0.0833 |
| resnet18_cifar100_bs64_50e_1gpu     |                  1 | single      |       0.0543 |       0.0507 |                   0.0036 |                        0.0709 |
| maskrcnn_coco_bs8_1gpu              |                  1 | single      |       0.4112 |       0.3889 |                   0.0223 |                        0.0573 |
| resnet34_cifar100_bs32_50e_1gpu     |                  1 | single      |       0.0632 |       0.06   |                   0.0033 |                        0.0545 |
| resnet34_cifar100_bs128_50e_1gpu    |                  1 | single      |       0.0793 |       0.0758 |                   0.0035 |                        0.0462 |
| efficientnet_cifar100_bs64_20e_1gpu |                  1 | single      |       0.0111 |       0.0116 |                   0.0005 |                        0.0459 |
| efficientnet_cifar100_bs32_50e_1gpu |                  1 | single      |       0.008  |       0.0084 |                   0.0003 |                        0.0411 |


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


## Profile score component breakdown

`profile_stat_score` is the equal-weight average of mean, median, mode, and max from the extracted solo-profile CSVs. It is not the AEGIS risk formula. `aegis_profile_risk` is only available when mean, median, p95, and EWMA are present.

| metric   | stat               |   n |   mean_200s |   mean_full |   mean_abs_error |   median_abs_error |   p95_abs_error |   mean_relative_error |
|:---------|:-------------------|----:|------------:|------------:|-----------------:|-------------------:|----------------:|----------------------:|
| smact    | mean               |  55 |      0.4139 |      0.4248 |           0.0163 |             0.0046 |          0.0315 |                0.0311 |
| smact    | median             |  55 |      0.439  |      0.4384 |           0.0048 |             0.001  |          0.0247 |                0.0175 |
| smact    | mode               |  55 |      0.3232 |      0.4319 |           0.1167 |             0.001  |          0.7194 |                0.1883 |
| smact    | max                |  55 |      0.5055 |      0.5173 |           0.0119 |             0.002  |          0.0363 |                0.0298 |
| smact    | profile_stat_score |  55 |      0.4204 |      0.4531 |           0.0354 |             0.0042 |          0.1936 |                0.061  |
| smact    | p95                |  55 |      0.4799 |      0.4821 |           0.005  |             0.0016 |          0.0095 |                0.011  |
| smact    | ewma               |  55 |      0.376  |      0.3706 |           0.013  |             0.0058 |          0.0463 |                0.0334 |
| smact    | aegis_profile_risk |  55 |      0.4272 |      0.429  |           0.0076 |             0.0037 |          0.0186 |                0.018  |
| smocc    | mean               |  55 |      0.1931 |      0.1971 |           0.0066 |             0.0024 |          0.0166 |                0.0314 |
| smocc    | median             |  55 |      0.202  |      0.2019 |           0.0022 |             0.001  |          0.013  |                0.0189 |
| smocc    | mode               |  55 |      0.1652 |      0.2026 |           0.0393 |             0.001  |          0.3155 |                0.1349 |
| smocc    | max                |  55 |      0.2384 |      0.2433 |           0.0049 |             0.001  |          0.0146 |                0.0257 |
| smocc    | profile_stat_score |  55 |      0.1997 |      0.2112 |           0.0123 |             0.002  |          0.0909 |                0.0465 |
| smocc    | p95                |  55 |      0.2266 |      0.2274 |           0.0022 |             0.0007 |          0.0064 |                0.0111 |
| smocc    | ewma               |  55 |      0.1744 |      0.1713 |           0.0059 |             0.003  |          0.0192 |                0.0332 |
| smocc    | aegis_profile_risk |  55 |      0.199  |      0.1994 |           0.0034 |             0.0021 |          0.0094 |                0.0187 |
| drama    | mean               |  55 |      0.1683 |      0.1705 |           0.0051 |             0.0016 |          0.0193 |                0.0339 |
| drama    | median             |  55 |      0.173  |      0.173  |           0.0017 |             0.001  |          0.0041 |                0.0244 |
| drama    | mode               |  55 |      0.155  |      0.1723 |           0.0208 |             0.001  |          0.1299 |                0.1105 |
| drama    | max                |  55 |      0.2086 |      0.2118 |           0.0032 |             0.001  |          0.0148 |                0.0213 |
| drama    | profile_stat_score |  55 |      0.1762 |      0.1819 |           0.0066 |             0.0008 |          0.0502 |                0.0386 |
| drama    | p95                |  55 |      0.1982 |      0.1988 |           0.0024 |             0.001  |          0.0093 |                0.0237 |
| drama    | ewma               |  55 |      0.1517 |      0.1473 |           0.0061 |             0.0012 |          0.0187 |                0.0385 |
| drama    | aegis_profile_risk |  55 |      0.1728 |      0.1724 |           0.003  |             0.0014 |          0.0117 |                0.0234 |


## Notes for paper analysis

- `lucid_style_class_200s` is a Lucid-style profile class, not an exact Lucid reproduction.
- `profile_stat_score` uses equal weights over mean, median, mode, and max from extracted solo-profile CSVs.
- `profile_stat_score` is per metric/GPU/window, not a workload-level AEGIS risk.
- `aegis_profile_risk` should only be used when mean, median, p95, and EWMA are available.
- For activity metrics on 2-GPU workloads, inspect `gpu_a` and `gpu_b` separately.
- For memory footprint on 2-GPU workloads, use sum columns when reasoning about total memory demand.
- Large 200s-vs-full mismatch indicates that a short profiling window may not represent the full run.
