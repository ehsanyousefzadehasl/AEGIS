#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DISPLAY_NAMES = {
    "exclusive": "Exclusive",
    "OR-MAGM": "AEGIS",
    "EST-MAGM__horus": "AEGIS+HorusMem",
    "HORUS__horus": "Horus-style",
    "LUCID": "Lucid-style",
    "oracle-MAGM": "Oracle-MFM",
    "PROFILED-MAGM": "Profiled-MFM",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate ECDFs, completion curves, and summary "
            "tables from AEGIS policy runs."
        )
    )
    parser.add_argument(
        "--job-metrics",
        type=Path,
        nargs="+",
        required=True,
        help="One or more analysis/job_metrics.csv files.",
    )
    parser.add_argument(
        "--solo-profiles",
        type=Path,
        nargs="*",
        default=[],
        help=(
            "Optional solo-profile CSVs used to calculate "
            "normalized JCT."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )
    return parser.parse_args()


def display_name(run_label: str) -> str:
    return DISPLAY_NAMES.get(run_label, run_label)


def save_figure(
    figure: plt.Figure,
    output_dir: Path,
    stem: str,
) -> None:
    figure.tight_layout()

    for suffix in ["pdf", "png"]:
        figure.savefig(
            output_dir / f"{stem}.{suffix}",
            dpi=300,
            bbox_inches="tight",
        )

    plt.close(figure)


def ecdf(values: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    clean = pd.to_numeric(
        values,
        errors="coerce",
    ).dropna()

    clean = clean[np.isfinite(clean)]
    clean = clean[clean >= 0]

    x = np.sort(clean.to_numpy(dtype=float))

    if len(x) == 0:
        return np.array([]), np.array([])

    y = np.arange(1, len(x) + 1) / len(x)
    return x, y


def plot_ecdf(
    frame: pd.DataFrame,
    *,
    value_column: str,
    x_label: str,
    output_dir: Path,
    output_stem: str,
    log_x: bool = False,
) -> None:
    figure, axis = plt.subplots(figsize=(6.4, 4.2))

    for run_label, group in frame.groupby(
        "run_label",
        sort=True,
    ):
        x, y = ecdf(group[value_column])

        if len(x) == 0:
            continue

        axis.step(
            x,
            y,
            where="post",
            label=display_name(str(run_label)),
        )

    axis.set_xlabel(x_label)
    axis.set_ylabel("Fraction of jobs")
    axis.set_ylim(0.0, 1.01)
    axis.grid(True, alpha=0.3)
    axis.legend()

    if log_x:
        positive = pd.to_numeric(
            frame[value_column],
            errors="coerce",
        )
        if (positive > 0).any():
            axis.set_xscale("log")

    save_figure(
        figure,
        output_dir,
        output_stem,
    )


def _normalize_path(value: object) -> str:
    return Path(str(value)).expanduser().as_posix()


def load_solo_runtime_map(
    paths: list[Path],
) -> tuple[dict[str, float], dict[str, float]]:
    exact: dict[str, float] = {}
    basename: dict[str, float] = {}
    ambiguous_basenames: set[str] = set()

    for path in paths:
        frame = pd.read_csv(path)

        path_column = next(
            (
                column
                for column in ["task_path", "spec_path"]
                if column in frame.columns
            ),
            None,
        )

        if path_column is None:
            raise ValueError(
                f"{path}: expected task_path or spec_path"
            )

        runtime_column = "end_to_end_time_s"

        if runtime_column not in frame.columns:
            raise ValueError(
                f"{path}: missing required solo-runtime column "
                f"{runtime_column}"
            )

        for row in frame.itertuples(index=False):
            task_value = getattr(row, path_column)
            runtime_value = getattr(row, runtime_column)

            if pd.isna(task_value):
                raise ValueError(
                    f"{path}: encountered a missing workload path"
                )

            normalized = _normalize_path(task_value)

            runtime = pd.to_numeric(
                runtime_value,
                errors="coerce",
            )

            if pd.isna(runtime) or float(runtime) <= 0:
                raise ValueError(
                    f"{path}: invalid end_to_end_time_s for "
                    f"{normalized}: {runtime_value!r}"
                )

            runtime = float(runtime)

            normalized = _normalize_path(task_value)
            exact[normalized] = runtime

            name = Path(normalized).name

            previous = basename.get(name)
            if previous is not None and not np.isclose(
                previous,
                runtime,
            ):
                ambiguous_basenames.add(name)
            else:
                basename[name] = runtime

    for name in ambiguous_basenames:
        basename.pop(name, None)

    return exact, basename


def add_normalized_jct(
    frame: pd.DataFrame,
    solo_profile_paths: list[Path],
) -> pd.DataFrame:
    exact, basename = load_solo_runtime_map(
        solo_profile_paths
    )

    runtimes: list[float | None] = []
    missing: set[str] = set()

    for task_value in frame["task_file"]:
        normalized = _normalize_path(task_value)

        runtime = exact.get(normalized)

        if runtime is None:
            runtime = basename.get(
                Path(normalized).name
            )

        if runtime is None:
            missing.add(normalized)

        runtimes.append(runtime)

    if missing:
        formatted = "\n".join(sorted(missing))

        raise ValueError(
            "Missing solo runtimes for these workloads:\n"
            f"{formatted}"
        )

    result = frame.copy()
    result["solo_runtime_s"] = runtimes
    result["normalized_jct"] = (
        pd.to_numeric(result["jct_s"], errors="raise")
        / result["solo_runtime_s"]
    )

    return result


def plot_completion_progress(
    frame: pd.DataFrame,
    *,
    output_dir: Path,
) -> None:
    prepared = frame.copy()

    prepared["submitted_at"] = pd.to_datetime(
        prepared["submitted_at"],
        utc=True,
        errors="raise",
    )
    prepared["completed_at"] = pd.to_datetime(
        prepared["completed_at"],
        utc=True,
        errors="coerce",
    )

    run_keys = [
        "experiment_name",
        "run_label",
        "run_dir",
    ]

    run_curves: dict[str, list[np.ndarray]] = {}
    maximum_elapsed = 0.0

    elapsed_by_run: dict[tuple, np.ndarray] = {}

    for key, group in prepared.groupby(
        run_keys,
        dropna=False,
        sort=True,
    ):
        start = group["submitted_at"].min()

        elapsed = (
            group["completed_at"] - start
        ).dt.total_seconds().dropna()

        values = np.sort(
            elapsed.to_numpy(dtype=float)
        )

        elapsed_by_run[key] = values

        if len(values):
            maximum_elapsed = max(
                maximum_elapsed,
                float(values[-1]),
            )

    if maximum_elapsed <= 0:
        raise ValueError(
            "No valid completion timestamps were found"
        )

    grid = np.linspace(
        0.0,
        maximum_elapsed,
        400,
    )

    for key, values in elapsed_by_run.items():
        run_label = str(key[1])

        fractions = np.searchsorted(
            values,
            grid,
            side="right",
        ) / len(values)

        run_curves.setdefault(
            run_label,
            [],
        ).append(fractions)

    figure, axis = plt.subplots(figsize=(6.4, 4.2))

    for run_label, curves in sorted(
        run_curves.items()
    ):
        matrix = np.vstack(curves)
        mean_curve = matrix.mean(axis=0)

        line = axis.plot(
            grid / 3600.0,
            mean_curve,
            label=display_name(run_label),
        )[0]

        if len(curves) > 1:
            lower = np.quantile(
                matrix,
                0.10,
                axis=0,
            )
            upper = np.quantile(
                matrix,
                0.90,
                axis=0,
            )

            axis.fill_between(
                grid / 3600.0,
                lower,
                upper,
                alpha=0.15,
                color=line.get_color(),
            )

    axis.set_xlabel("Elapsed experiment time (hours)")
    axis.set_ylabel("Fraction of jobs completed")
    axis.set_ylim(0.0, 1.01)
    axis.grid(True, alpha=0.3)
    axis.legend()

    save_figure(
        figure,
        output_dir,
        "completion_progress",
    )


def build_run_summary(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    prepared = frame.copy()

    for column in [
        "jct_s",
        "initial_queue_wait_s",
        "failed_attempt_count",
        "recovered_attempt_count",
        "total_recovery_queue_wait_s",
    ]:
        prepared[column] = pd.to_numeric(
            prepared[column],
            errors="coerce",
        )

    prepared["submitted_at"] = pd.to_datetime(
        prepared["submitted_at"],
        utc=True,
        errors="raise",
    )
    prepared["completed_at"] = pd.to_datetime(
        prepared["completed_at"],
        utc=True,
        errors="coerce",
    )

    rows = []

    for (
        experiment_name,
        run_label,
        run_dir,
    ), group in prepared.groupby(
        [
            "experiment_name",
            "run_label",
            "run_dir",
        ],
        dropna=False,
        sort=True,
    ):
        start = group["submitted_at"].min()
        end = group["completed_at"].max()

        makespan_s = (
            float((end - start).total_seconds())
            if pd.notna(end)
            else np.nan
        )

        completed = group[
            "completed_successfully"
        ].fillna(False).astype(bool)

        rows.append(
            {
                "experiment_name": experiment_name,
                "run_label": run_label,
                "display_name": display_name(
                    str(run_label)
                ),
                "run_dir": run_dir,
                "job_count": int(len(group)),
                "completed_job_count": int(
                    completed.sum()
                ),
                "completion_fraction": float(
                    completed.mean()
                ),
                "makespan_s": makespan_s,
                "jct_mean_s": float(
                    group["jct_s"].mean()
                ),
                "jct_p50_s": float(
                    group["jct_s"].quantile(0.50)
                ),
                "jct_p95_s": float(
                    group["jct_s"].quantile(0.95)
                ),
                "jct_p99_s": float(
                    group["jct_s"].quantile(0.99)
                ),
                "queue_wait_mean_s": float(
                    group[
                        "initial_queue_wait_s"
                    ].mean()
                ),
                "queue_wait_p95_s": float(
                    group[
                        "initial_queue_wait_s"
                    ].quantile(0.95)
                ),
                "failed_attempt_count": int(
                    group[
                        "failed_attempt_count"
                    ].fillna(0).sum()
                ),
                "recovered_attempt_count": int(
                    group[
                        "recovered_attempt_count"
                    ].fillna(0).sum()
                ),
                "total_recovery_queue_wait_s": float(
                    group[
                        "total_recovery_queue_wait_s"
                    ].fillna(0).sum()
                ),
            }
        )

    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()

    for path in args.job_metrics:
        if not path.is_file():
            raise FileNotFoundError(path)

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    frames = [
        pd.read_csv(path)
        for path in args.job_metrics
    ]

    frame = pd.concat(
        frames,
        ignore_index=True,
    )

    required_columns = {
        "experiment_name",
        "run_label",
        "run_dir",
        "task_file",
        "submitted_at",
        "completed_at",
        "initial_queue_wait_s",
        "jct_s",
        "completed_successfully",
        "failed_attempt_count",
        "recovered_attempt_count",
        "total_recovery_queue_wait_s",
    }

    missing = required_columns - set(frame.columns)

    if missing:
        raise ValueError(
            "Job metrics are missing columns: "
            f"{sorted(missing)}"
        )

    plot_ecdf(
        frame,
        value_column="jct_s",
        x_label="Job completion time (seconds)",
        output_dir=args.output_dir,
        output_stem="jct_ecdf",
        log_x=True,
    )

    plot_ecdf(
        frame,
        value_column="initial_queue_wait_s",
        x_label="Initial queue wait (seconds)",
        output_dir=args.output_dir,
        output_stem="queue_wait_ecdf",
        log_x=True,
    )

    plot_completion_progress(
        frame,
        output_dir=args.output_dir,
    )

    if args.solo_profiles:
        normalized = add_normalized_jct(
            frame,
            args.solo_profiles,
        )

        plot_ecdf(
            normalized,
            value_column="normalized_jct",
            x_label="Normalized JCT (JCT / solo runtime)",
            output_dir=args.output_dir,
            output_stem="normalized_jct_ecdf",
            log_x=True,
        )

        normalized[
            [
                "experiment_name",
                "run_label",
                "task_file",
                "jct_s",
                "solo_runtime_s",
                "normalized_jct",
            ]
        ].to_csv(
            args.output_dir
            / "normalized_jct_values.csv",
            index=False,
        )

    recovery_values = pd.to_numeric(
        frame["total_recovery_queue_wait_s"],
        errors="coerce",
    )

    recovered = frame.loc[
        recovery_values > 0
    ].copy()

    if not recovered.empty:
        plot_ecdf(
            recovered,
            value_column="total_recovery_queue_wait_s",
            x_label="Recovery queue wait (seconds)",
            output_dir=args.output_dir,
            output_stem="recovery_queue_wait_ecdf",
            log_x=True,
        )

    run_summary = build_run_summary(frame)

    run_summary.to_csv(
        args.output_dir / "policy_run_summary.csv",
        index=False,
    )

    print(
        f"Wrote figures and tables to "
        f"{args.output_dir}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
