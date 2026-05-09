# Paper Artifacts

This folder is a curated index for paper-writing. It does not replace the raw experiment outputs; it points to the stable analysis tables and figures.

## Source locations

### Solo profile anchor analyses

- Activity-filtered solo profile analysis: `evaluation/profiling/solo/analysis/`
- First-memory anchored solo profile analysis: `evaluation/profiling/solo/analysis_first_memory_anchor/`
- Launch anchored solo profile analysis: `evaluation/profiling/solo/analysis_launch_anchor/`

### First-observed-GPU-activity threshold-window analysis

- Suite directory: `evaluation/threshold_sensitivity/solo_runs/combined_1gpu_threshold_windows_with_llama_20260509_202117`
- Window analysis: `evaluation/threshold_sensitivity/solo_runs/combined_1gpu_threshold_windows_with_llama_20260509_202117/window_analysis`
- Summaries: `evaluation/threshold_sensitivity/summaries/`
- Figures: `evaluation/figures/first_gpu_activity_windows_w(30, 40, 60, 120)s_vs_w200s/`

## Curated files

- `claims_and_evidence.md`: paper-facing claims and where the evidence lives.
- `figure_index.md`: figure paths grouped by experiment.
- `tables/solo_profile_anchor_comparison.md`: launch vs first-memory vs activity-filtered comparison.
- `tables/first_gpu_activity_window_stability.md`: stability of shorter windows vs 200s.
- `tables/risk_component_ablation_rollup.md`: mean/median/p95/EWMA/risk ablation.
- `tables/memory_safety_summary.md`: 200s-window memory peak vs full-run peak and workload memory requirement.
- `figure_gallery.md`: visual gallery of selected generated figures.
- `tables/solo_profile_memory_peak_summary.md`: 200s observed memory peak vs full-run observed memory peak from solo profiles.
- `tables/first_gpu_activity_memory_stability.md`: first-GPU-activity memory usage windows vs the 200s reference.
- `tables/first_gpu_activity_delay_summary.md`: delay from dispatch to first observed GPU activity.

## Terminology note

The current threshold-window pipeline uses a first-observed-GPU-activity anchor. Some internal CSV columns may still use legacy names such as `ttfk_wait_seconds`; interpret those as wait time until the job is first observed as active on GPU, not as exact CUDA-kernel-launch instrumentation.
