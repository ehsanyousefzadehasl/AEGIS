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
        description="Run facebookresearch DLRM on Criteo Terabyte"
    )
    parser.add_argument("--raw_data_file", type=str, default="/raid/datasets/criteo/data/day")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--num_batches", type=int, default=10000)
    parser.add_argument("--mini_batch_size", type=int, default=32768)
    parser.add_argument("--learning_rate", type=float, default=0.05)
    parser.add_argument("--num_workers", type=int, default=16)
    parser.add_argument("--print_model_summary", action="store_true")
    parser.add_argument("--summary_output", type=str, default=None)
    parser.add_argument("--print_faketensor_estimate", action="store_true")
    parser.add_argument("--extra_args", nargs=argparse.REMAINDER, default=[])
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dlrm_py = (
        REPO_ROOT
        / "evaluation"
        / "workloads"
        / "training"
        / "third_party"
        / "dlrm"
        / "dlrm_s_pytorch.py"
    )

    cmd = [
        sys.executable,
        str(dlrm_py),
        "--data-set",
        "terabyte",
        "--raw-data-file",
        args.raw_data_file,
        "--loss-function",
        "bce",
        "--round-targets",
        "True",
        "--learning-rate",
        str(args.learning_rate),
        "--mini-batch-size",
        str(args.mini_batch_size),
        "--nepochs",
        str(args.epochs),
        "--num-batches",
        str(args.num_batches),
        "--arch-sparse-feature-size",
        "64",
        "--arch-mlp-bot",
        "13-512-256-128-64",
        "--arch-mlp-top",
        "1024-512-256-1",
        "--use-gpu",
        "--memory-map",
        "--dataset-multiprocessing",
        "--print-time",
        "--print-freq",
        "100",
        "--num-workers",
        str(args.num_workers),
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