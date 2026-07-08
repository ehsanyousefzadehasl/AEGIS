# Threshold sweep report

Sweep root: `evaluation/threshold_sensitivity/results/threshold_sweep_v1_fixed_grid`

## Recommended setting

- Thresholds: SMACT=0.50, SMOCC=0.20, DRAMA=0.40
- Mean throughput gain: 1.679
- Worst max slowdown: 1.076
- P95 max slowdown: 1.075
- Total admission deferrals: 1193
- Feasible under selected budgets: True

## Selection rule

Feasible means completion_fraction >= 1.0, no started-job failures, max_slowdown <= 2.0, and p95_max_slowdown <= 2.0.

## Main files

- `tables/threshold_sweep_trials_combined.csv`
- `tables/threshold_sweep_summary.csv`
- `tables/threshold_settings_ranked.csv`
- `tables/threshold_settings_feasible.csv`
- `tables/per_trial_sensitivity.csv`
- `figures/threshold_grid_throughput_vs_slowdown.png`
- `figures/rejection_diagnostics.png`
- `figures/per_sequence_throughput_and_slowdown.png`
- `figures/paper_threshold_tradeoff_with_deferrals.png`
- `figures/paper_threshold_tradeoff_tails_with_deferrals.png`
