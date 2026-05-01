from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.workloads.training.common.timing import timed_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run torchvision Mask R-CNN reference training on COCO"
    )
    parser.add_argument("--data_path", type=str, default="/raid/datasets/coco")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=0.0025)
    parser.add_argument("--model", type=str, default="maskrcnn_resnet50_fpn")
    parser.add_argument("--output_dir", type=str, default="runs")
    parser.add_argument("--print_model_summary", action="store_true")
    parser.add_argument("--summary_output", type=str, default=None)
    parser.add_argument("--print_faketensor_estimate", action="store_true")
    parser.add_argument("--extra_args", nargs=argparse.REMAINDER, default=[])
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    train_py = (
        REPO_ROOT
        / "evaluation"
        / "workloads"
        / "training"
        / "third_party"
        / "vision"
        / "references"
        / "detection"
        / "train.py"
    )

    cmd = [
        sys.executable,
        str(train_py),
        "--dataset",
        "coco",
        "--data-path",
        args.data_path,
        "--model",
        args.model,
        "--epochs",
        str(args.epochs),
        "--lr",
        str(args.lr),
        "-b",
        str(args.batch_size),
        "--output-dir",
        args.output_dir,
        "--print_model_summary" if args.print_model_summary else None,
        "--summary_output" if args.summary_output is not None else None,
        args.summary_output if args.summary_output is not None else None,
        "--print_faketensor_estimate" if args.print_faketensor_estimate else None,
        *args.extra_args,
    ]
    cmd = [x for x in cmd if x is not None]

    print("Running:", " ".join(cmd))
    with timed_run() as timer:
        subprocess.run(cmd, check=True)

    print(f"\nExecution time: {timer.elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()