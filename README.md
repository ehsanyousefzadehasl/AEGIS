# AEGIS

### Launching evaluation

```bash
cd /home/ehyo/AEGIS
set -o pipefail

python evaluation/experiments/run_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation_corrected_philly.yaml \
  --launch 2>&1 |
tee -a evaluation/experiments/results/final_representative_evaluation_resume_corrected.log

python evaluation/experiments/run_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation_corrected_saturn_remaining.yaml \
  --launch 2>&1 |
tee -a evaluation/experiments/results/final_representative_evaluation_resume_corrected.log

python evaluation/experiments/run_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation_corrected_venus.yaml \
  --launch 2>&1 |
tee -a evaluation/experiments/results/final_representative_evaluation_resume_corrected.log
```


evaluation summarization

```bash
python evaluation/experiments/analyze_evaluation_manifest.py \
  --manifest evaluation/experiments/manifests/final_representative_evaluation.yaml \
  --refresh
```


```bash
python evaluation/experiments/analyze_estimator_sensitivity.py --refresh
```