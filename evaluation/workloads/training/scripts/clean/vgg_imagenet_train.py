from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
from torchvision import datasets, models
from tqdm import tqdm

from evaluation.workloads.training.common.faketensor_memory_estimation import (
    estimate_faketensor_memory,
    format_memory_gib,
)
from evaluation.workloads.training.common.summaries import generate_model_summary
from evaluation.workloads.training.common.timing import timed_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train VGG16 on ImageNet")
    parser.add_argument("--batch_size", "--batch-size", type=int, default=32, help="Batch size for training")
    parser.add_argument("--epochs", "--num_epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--lr", "--learning_rate", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--weight_decay", type=float, default=0.0, help="Weight decay for optimizer")
    parser.add_argument(
        "--data_dir",
        type=str,
        default="/raid/datasets/imagenet",
        help="ImageNet root directory containing train/ and val/ subdirectories",
    )
    parser.add_argument("--num_workers", type=int, default=4, help="Number of dataloader workers")
    parser.add_argument(
        "--meta_cache_dir",
        type=str,
        default=None,
        help="Legacy no-op argument kept for compatibility",
    )
    parser.add_argument(
        "--print_model_summary",
        action="store_true",
        help="Print model summary before training",
    )
    parser.add_argument(
        "--summary_output",
        type=str,
        default=None,
        help="Optional path to save model summary",
    )
    parser.add_argument(
        "--print_faketensor_estimate",
        action="store_true",
        help="Print FakeTensor memory estimate before training",
    )
    parser.add_argument(
        "--report_every",
        type=int,
        default=100,
        help="Report training progress every N batches",
    )
    return parser.parse_args()


def build_transforms() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


def build_dataloaders(args: argparse.Namespace) -> tuple[DataLoader, DataLoader]:
    transform = build_transforms()

    train_dir = Path(args.data_dir) / "train"
    val_dir = Path(args.data_dir) / "val"

    train_dataset = datasets.ImageFolder(root=str(train_dir), transform=transform)
    val_dataset = datasets.ImageFolder(root=str(val_dir), transform=transform)

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )
    return train_loader, val_loader


def build_model(device: torch.device) -> nn.Module:
    model = models.vgg16(weights=None)
    model.classifier[6] = nn.Linear(model.classifier[6].in_features, 1000)
    return model.to(device)


def estimate_model_memory_bytes(model: nn.Module, batch_size: int) -> int:
    if not torch.cuda.is_available():
        raise RuntimeError("FakeTensor memory estimation currently expects CUDA to be available")

    def input_builder():
        return torch.rand(batch_size, 3, 224, 224, requires_grad=True).to("cuda")

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
) -> float:
    model.train()
    running_loss = 0.0

    progress_bar = tqdm(train_loader, desc=f"Epoch [{epoch}]", unit="batch")
    for batch_idx, (inputs, labels) in enumerate(progress_bar, start=1):
        inputs = inputs.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()

        if report_every > 0 and batch_idx % report_every == 0:
            progress_bar.set_postfix({"loss": running_loss / batch_idx})

    epoch_loss = running_loss / len(train_loader)
    print(f"Epoch [{epoch}] Train Loss: {epoch_loss:.4f}")
    return epoch_loss


def evaluate(
    *,
    model: nn.Module,
    val_loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    model.eval()
    val_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)

            outputs = model(inputs)
            loss = criterion(outputs, labels)

            val_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    avg_val_loss = val_loss / len(val_loader)
    accuracy = 100.0 * correct / total
    print(f"Validation Loss: {avg_val_loss:.4f}, Accuracy: {accuracy:.2f}%")
    return accuracy


def main() -> None:
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_loader, val_loader = build_dataloaders(args)
    model = build_model(device)

    if args.print_model_summary or args.summary_output is not None:
        summary_input = torch.rand(args.batch_size, 3, 224, 224, device=device)
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
    optimizer = optim.Adam(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )

    with timed_run() as timer:
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
                val_loader=val_loader,
                criterion=criterion,
                device=device,
            )

    print(f"\nExecution time: {timer.elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()