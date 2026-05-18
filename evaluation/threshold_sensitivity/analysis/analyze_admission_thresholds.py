#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_OUTPUT_DIR = Path("evaluation/threshold_sensitivity/admission_threshold_sweeps")


def parse_grid(text: str) -> list[float]:
    values = []
    for item in str(text).split(","):
        item = item.strip()
        if item:
            values.append(float(item))
    return values


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sweep admission thresholds over progressive collocation observations."
    )
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--smact-thresholds", default="0.60,0.65,0.70,0.75,0.80,0.85,0.90")
    p.add_argument("--smocc-thresholds", default="0.25,0.30,0.35,0.40,0.45,0.50,0.55,0.60")
    p.add_argument("--drama-thresholds", default="0.20,0.25,0.30,0.35,0.40,0.45,0.50")
    p.add_argument(
        "--unsafe-slowdown",
        type=float,
        default=1.20,
        help="A collocation is considered unsafe if max_slowdown >= this value.",
    )
    return p.parse_args()


def normalize_input(df: pd.DataFrame) -> pd.DataFrame:
    required = {
        "smact_risk",
        "smocc_risk",
        "drama_risk",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    out = df.copy()

    for col in ["smact_risk", "smocc_risk", "drama_risk"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    if "max_slowdown" in out.columns:
        out["max_slowdown"] = pd.to_numeric(out["max_slowdown"], errors="coerce")
    elif "slowdown" in out.columns:
        out["max_slowdown"] = pd.to_numeric(out["slowdown"], errors="coerce")
    else:
        out["max_slowdown"] = pd.NA

    if "oom" in out.columns:
        out["oom"] = out["oom"].fillna(False).astype(bool)
    else:
        out["oom"] = False

    return out.dropna(subset=["smact_risk", "smocc_risk", "drama_risk"])


def would_reject(
    df: pd.DataFrame,
    *,
    tau_smact: float,
    tau_smocc: float,
    tau_drama: float,
) -> pd.Series:
    return (
        (df["smact_risk"] >= tau_smact)
        & (
            (df["smocc_risk"] >= tau_smocc)
            | (df["drama_risk"] >= tau_drama)
        )
    )


def summarize_threshold_tuple(
    df: pd.DataFrame,
    *,
    tau_smact: float,
    tau_smocc: float,
    tau_drama: float,
    unsafe_slowdown: float,
) -> dict:
    reject = would_reject(
        df,
        tau_smact=tau_smact,
        tau_smocc=tau_smocc,
        tau_drama=tau_drama,
    )
    allow = ~reject

    unsafe = df["max_slowdown"] >= unsafe_slowdown

    allowed = df[allow]
    rejected = df[reject]

    unsafe_allowed = df[allow & unsafe]
    safe_rejected = df[reject & ~unsafe]

    return {
        "tau_smact": tau_smact,
        "tau_smocc": tau_smocc,
        "tau_drama": tau_drama,
        "n": int(len(df)),
        "allowed_count": int(allow.sum()),
        "rejected_count": int(reject.sum()),
        "allowed_rate": float(allow.mean()) if len(df) else 0.0,
        "rejected_rate": float(reject.mean()) if len(df) else 0.0,
        "unsafe_count": int(unsafe.sum()),
        "unsafe_allowed_count": int(len(unsafe_allowed)),
        "unsafe_allowed_rate": float(len(unsafe_allowed) / len(allowed)) if len(allowed) else 0.0,
        "safe_rejected_count": int(len(safe_rejected)),
        "safe_rejected_rate": float(len(safe_rejected) / len(rejected)) if len(rejected) else 0.0,
        "mean_slowdown_allowed": float(allowed["max_slowdown"].mean()) if len(allowed) and allowed["max_slowdown"].notna().any() else None,
        "p95_slowdown_allowed": float(allowed["max_slowdown"].quantile(0.95)) if len(allowed) and allowed["max_slowdown"].notna().any() else None,
        "max_slowdown_allowed": float(allowed["max_slowdown"].max()) if len(allowed) and allowed["max_slowdown"].notna().any() else None,
    }


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    if df.empty:
        return "_No rows._\n"

    view = df.loc[:, [c for c in columns if c in df.columns]].head(max_rows).copy()

    lines = []
    lines.append("| " + " | ".join(view.columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(view.columns)) + " |")

    for _, row in view.iterrows():
        vals = []
        for col in view.columns:
            value = row[col]
            if isinstance(value, float):
                vals.append(f"{value:.4f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")

    return "\n".join(lines) + "\n"


def write_summary_md(results: pd.DataFrame, output_dir: Path, unsafe_slowdown: float) -> None:
    path = output_dir / "admission_threshold_sweep_summary.md"

    ranked = results.sort_values(
        [
            "unsafe_allowed_rate",
            "p95_slowdown_allowed",
            "allowed_rate",
        ],
        ascending=[True, True, False],
    )

    balanced = results[
        (results["unsafe_allowed_rate"] <= 0.05)
        & (results["allowed_rate"] > 0)
    ].sort_values(
        ["allowed_rate", "p95_slowdown_allowed"],
        ascending=[False, True],
    )

    lines = ["# Admission Threshold Sweep Summary\n"]
    lines.append(
        "This sweep evaluates the rule: reject a GPU if "
        "`smact_risk >= tau_smact AND (smocc_risk >= tau_smocc OR drama_risk >= tau_drama)`.\n"
    )

    lines.append(
        f"Unsafe cases are defined only by slowdown: `max_slowdown >= {unsafe_slowdown}`. "
        "OOM is intentionally excluded because this study assumes memory feasibility is handled separately "
        "by the hard memory-admission constraint.\n"
    )
    
    lines.append("\n## Top conservative threshold tuples\n")
    lines.append(
        markdown_table(
            ranked,
            [
                "tau_smact",
                "tau_smocc",
                "tau_drama",
                "allowed_rate",
                "unsafe_allowed_rate",
                "p95_slowdown_allowed",
                "max_slowdown_allowed",
                "safe_rejected_rate",
            ],
            max_rows=20,
        )
    )

    lines.append("\n## Candidate balanced threshold tuples\n")
    lines.append(
        markdown_table(
            balanced,
            [
                "tau_smact",
                "tau_smocc",
                "tau_drama",
                "allowed_rate",
                "unsafe_allowed_rate",
                "p95_slowdown_allowed",
                "max_slowdown_allowed",
                "safe_rejected_rate",
            ],
            max_rows=20,
        )
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    args = parse_args()

    input_csv = Path(args.input_csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = normalize_input(pd.read_csv(input_csv))

    rows = []
    for tau_smact in parse_grid(args.smact_thresholds):
        for tau_smocc in parse_grid(args.smocc_thresholds):
            for tau_drama in parse_grid(args.drama_thresholds):
                rows.append(
                    summarize_threshold_tuple(
                        df,
                        tau_smact=tau_smact,
                        tau_smocc=tau_smocc,
                        tau_drama=tau_drama,
                        unsafe_slowdown=float(args.unsafe_slowdown),
                    )
                )

    results = pd.DataFrame(rows)

    output_csv = output_dir / "admission_threshold_sweep.csv"
    results.to_csv(output_csv, index=False)
    print(f"wrote {output_csv}")

    write_summary_md(results, output_dir, unsafe_slowdown=float(args.unsafe_slowdown))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())