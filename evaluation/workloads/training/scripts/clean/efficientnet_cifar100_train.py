from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
    
import argparse

import torch
import torch.nn as nn
import torch.optim as optim
from timm import create_model
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from evaluation.workloads.training.common.faketensor_memory_estimation import (
    estimate_faketensor_memory,
    format_memory_gib,
)
from evaluation.workloads.training.common.summaries import generate_model_summary
from evaluation.workloads.training.common.timing import timed_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train EfficientNet-B0 on CIFAR-100")
    parser.add_argument("--batch_size", type=int, default=64, help="Batch size for training")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--weight_decay", type=float, default=1e-4, help="Weight decay for AdamW")
    parser.add_argument("--data_root", type=str, default="evaluation/data", help="Root directory for CIFAR-100")
    parser.add_argument("--num_workers", type=int, default=4, help="Number of dataloader workers")
    parser.add_argument("--print_model_summary", action="store_true", help="Print model summary before training")
    parser.add_argument("--summary_output", type=str, default=None, help="Optional path to save model summary")
    parser.add_argument(
        "--print_faketensor_estimate",
        action="store_true",
        help="Print FakeTensor memory estimate before training",
    )
    parser.add_argument("--report_every", type=int, default=100, help="Print training progress every N batches")
    return parser.parse_args()


def build_transforms() -> tuple[transforms.Compose, transforms.Compose]:
    transform_train = transforms.Compose(
        [
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ]
    )

    transform_test = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
        ]
    )
    return transform_train, transform_test


def build_dataloaders(args: argparse.Namespace) -> tuple[DataLoader, DataLoader]:
    transform_train, transform_test = build_transforms()

    train_dataset = datasets.CIFAR100(
        root=args.data_root,
        train=True,
        download=True,
        transform=transform_train,
    )
    test_dataset = datasets.CIFAR100(
        root=args.data_root,
        train=False,
        download=True,
        transform=transform_test,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )
    return train_loader, test_loader


def build_model(device: torch.device) -> nn.Module:
    model = create_model("efficientnet_b0", pretrained=False, num_classes=100)
    return model.to(device)


def estimate_model_memory_bytes(model: nn.Module, batch_size: int) -> int:
    if not torch.cuda.is_available():
        raise RuntimeError("FakeTensor memory estimation currently expects CUDA to be available")

    def input_builder():
        return torch.rand(batch_size, 3, 32, 32, requires_grad=True).to("cuda")

    def forward_call(fake_input):
        return model.to("cuda")(fake_input)

    return estimate_faketensor_memory(
        model,
        input_builder=input_builder,
        forward_call=forward_call,
        run_backward=True,
    )


def train_one_epoch(
    *,
    epoch: int,
    model: nn.Module,
    train_loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    report_every: int,
) -> None:
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (inputs, targets) in enumerate(train_loader, start=1):
        inputs = inputs.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()

        if report_every > 0 and batch_idx % report_every == 0:
            print(
                f"Train Epoch: {epoch} "
                f"[{batch_idx * len(inputs)}/{len(train_loader.dataset)}] "
                f"Loss: {loss.item():.4f} | Acc: {100.0 * correct / total:.2f}%"
            )


def evaluate(
    *,
    model: nn.Module,
    test_loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    model.eval()
    test_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, targets in test_loader:
            inputs = inputs.to(device)
            targets = targets.to(device)

            outputs = model(inputs)
            loss = criterion(outputs, targets)

            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

    accuracy = 100.0 * correct / total
    print(f"Test Loss: {test_loss / len(test_loader):.4f} | Test Acc: {accuracy:.2f}%")
    return accuracy


def main() -> None:
    args = parse_args()

    with timed_run() as total_timer:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        train_loader, test_loader = build_dataloaders(args)
        model = build_model(device)

        if args.print_model_summary or args.summary_output is not None:
            summary_input = torch.rand(args.batch_size, 3, 32, 32, device=device)
            generate_model_summary(
                model,
                input_data=summary_input,
                print_summary=args.print_model_summary,
                output_path=args.summary_output,
                verbose=0,
            )

        if args.print_faketensor_estimate:
            faketensor_bytes = estimate_model_memory_bytes(model, args.batch_size)
            print(f"FakeTensor estimated peak memory: {format_memory_gib(faketensor_bytes):.4f} GiB")

        criterion = nn.CrossEntropyLoss()
        optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10)

        with timed_run() as train_timer:
            for epoch in range(1, args.epochs + 1):
                train_one_epoch(
                    epoch=epoch,
                    model=model,
                    train_loader=train_loader,
                    criterion=criterion,
                    optimizer=optimizer,
                    device=device,
                    report_every=args.report_every,
                )
                evaluate(
                    model=model,
                    test_loader=test_loader,
                    criterion=criterion,
                    device=device,
                )
                scheduler.step()

    print(f"training_loop_time_s: {train_timer.elapsed_seconds:.2f}")
    print(f"end_to_end_time_s: {total_timer.elapsed_seconds:.2f}")


if __name__ == "__main__":
    main()