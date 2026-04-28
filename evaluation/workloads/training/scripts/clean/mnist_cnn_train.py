from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
    
import argparse

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from evaluation.workloads.training.common.faketensor_memory_estimation import (
    estimate_faketensor_memory,
    format_memory_gib,
)
from evaluation.workloads.training.common.summaries import generate_model_summary
from evaluation.workloads.training.common.timing import timed_run


class Net(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = F.relu(x)
        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a simple CNN on MNIST")
    parser.add_argument("--batch-size", type=int, default=64, metavar="N", help="input batch size for training")
    parser.add_argument("--test-batch-size", type=int, default=1000, metavar="N", help="input batch size for testing")
    parser.add_argument("--epochs", type=int, default=14, metavar="N", help="number of epochs to train")
    parser.add_argument("--lr", type=float, default=1.0, metavar="LR", help="learning rate")
    parser.add_argument("--gamma", type=float, default=0.7, metavar="M", help="learning rate step gamma")
    parser.add_argument("--no-cuda", action="store_true", default=False, help="disable CUDA training")
    parser.add_argument("--no-mps", action="store_true", default=False, help="disable macOS GPU training")
    parser.add_argument("--dry-run", action="store_true", default=False, help="quickly check a single pass")
    parser.add_argument("--seed", type=int, default=1, metavar="S", help="random seed")
    parser.add_argument("--log-interval", type=int, default=10, metavar="N", help="batches between training logs")
    parser.add_argument("--save-model", action="store_true", default=False, help="save the trained model")
    parser.add_argument("--data-root", type=str, default="evaluation/data", help="root directory for MNIST")
    parser.add_argument("--num-workers", type=int, default=1, help="number of dataloader workers")
    parser.add_argument("--print-model-summary", action="store_true", help="print model summary before training")
    parser.add_argument("--summary-output", type=str, default=None, help="optional path to save model summary")
    parser.add_argument(
        "--print-faketensor-estimate",
        action="store_true",
        help="print FakeTensor memory estimate before training",
    )
    return parser.parse_args()


def resolve_device(args: argparse.Namespace) -> torch.device:
    use_cuda = not args.no_cuda and torch.cuda.is_available()
    use_mps = not args.no_mps and torch.backends.mps.is_available()

    if use_cuda:
        return torch.device("cuda")
    if use_mps:
        return torch.device("mps")
    return torch.device("cpu")


def build_dataloaders(args: argparse.Namespace, device: torch.device) -> tuple[DataLoader, DataLoader]:
    train_kwargs = {"batch_size": args.batch_size, "shuffle": True}
    test_kwargs = {"batch_size": args.test_batch_size, "shuffle": False}

    if device.type == "cuda":
        cuda_kwargs = {
            "num_workers": args.num_workers,
            "pin_memory": True,
        }
        train_kwargs.update(cuda_kwargs)
        test_kwargs.update(cuda_kwargs)
    else:
        base_kwargs = {"num_workers": args.num_workers}
        train_kwargs.update(base_kwargs)
        test_kwargs.update(base_kwargs)

    transform = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,)),
        ]
    )

    train_dataset = datasets.MNIST(
        root=args.data_root,
        train=True,
        download=True,
        transform=transform,
    )
    test_dataset = datasets.MNIST(
        root=args.data_root,
        train=False,
        download=True,
        transform=transform,
    )

    train_loader = DataLoader(train_dataset, **train_kwargs)
    test_loader = DataLoader(test_dataset, **test_kwargs)
    return train_loader, test_loader


def build_model(device: torch.device) -> nn.Module:
    return Net().to(device)


def estimate_model_memory_bytes(model: nn.Module, batch_size: int) -> int:
    if not torch.cuda.is_available():
        raise RuntimeError("FakeTensor memory estimation currently expects CUDA to be available")

    def input_builder():
        return torch.rand(batch_size, 1, 28, 28, requires_grad=True).to("cuda")

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
    args: argparse.Namespace,
    model: nn.Module,
    device: torch.device,
    train_loader: DataLoader,
    optimizer: optim.Optimizer,
    epoch: int,
) -> None:
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader, start=1):
        data = data.to(device)
        target = target.to(device)

        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()

        if args.log_interval > 0 and batch_idx % args.log_interval == 0:
            print(
                f"Train Epoch: {epoch} "
                f"[{batch_idx * len(data)}/{len(train_loader.dataset)} "
                f"({100.0 * batch_idx / len(train_loader):.0f}%)]\t"
                f"Loss: {loss.item():.6f}"
            )
            if args.dry_run:
                break


def evaluate(
    *,
    model: nn.Module,
    device: torch.device,
    test_loader: DataLoader,
) -> None:
    model.eval()
    test_loss = 0.0
    correct = 0

    with torch.no_grad():
        for data, target in test_loader:
            data = data.to(device)
            target = target.to(device)

            output = model(data)
            test_loss += F.nll_loss(output, target, reduction="sum").item()
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)
    accuracy = 100.0 * correct / len(test_loader.dataset)

    print(
        f"\nTest set: Average loss: {test_loss:.4f}, "
        f"Accuracy: {correct}/{len(test_loader.dataset)} ({accuracy:.0f}%)\n"
    )


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)

    with timed_run() as total_timer:
        device = resolve_device(args)
        train_loader, test_loader = build_dataloaders(args, device)
        model = build_model(device)

        if args.print_model_summary or args.summary_output is not None:
            summary_input = torch.rand(args.batch_size, 1, 28, 28, device=device)
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

        optimizer = optim.Adadelta(model.parameters(), lr=args.lr)
        scheduler = StepLR(optimizer, step_size=1, gamma=args.gamma)

        with timed_run() as train_timer:
            for epoch in range(1, args.epochs + 1):
                train_one_epoch(
                    args=args,
                    model=model,
                    device=device,
                    train_loader=train_loader,
                    optimizer=optimizer,
                    epoch=epoch,
                )
                evaluate(
                    model=model,
                    device=device,
                    test_loader=test_loader,
                )
                scheduler.step()

        if args.save_model:
            torch.save(model.state_dict(), "mnist_cnn.pt")

    print(f"training_loop_time_s: {train_timer.elapsed_seconds:.2f}")
    print(f"end_to_end_time_s: {total_timer.elapsed_seconds:.2f}")


if __name__ == "__main__":
    main()