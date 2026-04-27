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
    parser.add_argument("--model", type=str, default="maskrcnn_resnet50_fpn")
    parser.add_argument("--output_dir", type=str, default="runs")
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
        "-b",
        str(args.batch_size),
        "--output-dir",
        args.output_dir,
        *args.extra_args,
    ]

    print("Running:", " ".join(cmd))
    with timed_run() as timer:
        subprocess.run(cmd, check=True)

    print(f"\nExecution time: {timer.elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()