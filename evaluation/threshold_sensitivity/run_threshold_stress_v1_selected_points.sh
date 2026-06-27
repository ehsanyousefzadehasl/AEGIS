#!/usr/bin/env bash
set -euo pipefail

PLAN="evaluation/threshold_sensitivity/plans/threshold_stress_v1/progressive_trial_plan.jsonl"
ROOT="evaluation/threshold_sensitivity/results/threshold_stress_v1_selected_points"
SOLO="evaluation/profiling/solo/extracted/solo_profile_results_1gpu.csv"
WORKDIR="/home/ehyo/AEGIS"

# Edit thresholds here: name:tau_smact:tau_smocc:tau_drama
THRESHOLDS=(
  "conservative_0p00_0p00_0p00:0.00:0.00:0.00"
  "selected_0p65_0p35_0p50:0.65:0.35:0.50"
  "permissive_0p80_0p20_0p20:0.80:0.20:0.20"
  "admitall_1p00_1p00_1p00:1.00:1.00:1.00"
)

mkdir -p "$ROOT"

for item in "${THRESHOLDS[@]}"; do
  IFS=":" read -r name tau_smact tau_smocc tau_drama <<< "$item"
  out="$ROOT/$name"
  mkdir -p "$out"

  echo
  echo "======================================================================"
  echo "Running $name"
  echo "tau_smact=$tau_smact tau_smocc=$tau_smocc tau_drama=$tau_drama"
  echo "output=$out"
  echo "======================================================================"

  python evaluation/threshold_sensitivity/runners/run_progressive_threshold_trials.py \
    --plan-jsonl "$PLAN" \
    --output-dir "$out" \
    --workdir "$WORKDIR" \
    --execute-progressive-trial \
    --cleanup-after-observation \
    --window-seconds 30 \
    --summary-windows mean,p95,ema \
    --ttfk-timeout 300 \
    --window-timeout 300 \
    --poll-seconds 2 \
    --trial-timeout-seconds 14400 \
    --solo-runtime-csv "$SOLO" \
    --tau-smact "$tau_smact" \
    --tau-smocc "$tau_smocc" \
    --tau-drama "$tau_drama"
done
