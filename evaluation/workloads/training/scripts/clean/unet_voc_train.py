from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import segmentation_models_pytorch as smp
import torch
import torch.utils.data as data
from PIL import Image
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import VOCSegmentation
from tqdm.auto import tqdm

from evaluation.workloads.training.common.faketensor_memory_estimation import (
    estimate_faketensor_memory,
    format_memory_gib,
)
from evaluation.workloads.training.common.summaries import generate_model_summary
from evaluation.workloads.training.common.timing import timed_run


class VOCSeg(data.Dataset):
    def __init__(
        self,
        root: str,
        *,
        year: str = "2012",
        image_set: str = "train",
        img_size: int = 512,
        download: bool = False,
    ) -> None:
        self.base = VOCSegmentation(
            root=root,
            year=year,
            image_set=image_set,
            download=download,
        )
        self.img_size = img_size
        self.img_tf = transforms.Compose(
            [
                transforms.Resize((img_size, img_size)),
                transforms.ToTensor(),
            ]
        )
        self.mask_tf = transforms.Compose(
            [
                transforms.Resize((img_size, img_size), interpolation=Image.NEAREST),
            ]
        )

    def __len__(self) -> int:
        return len(self.base)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        img, mask = self.base[index]
        img = self.img_tf(img)
        mask = np.array(self.mask_tf(mask), dtype=np.int64)
        mask[mask == 255] = 0
        return img, torch.from_numpy(mask)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train U-Net on Pascal VOC segmentation")
    parser.add_argument("--root", type=str, default="/raid/datasets", help="Root directory containing VOC data")
    parser.add_argument("--year", type=str, default="2012", help="VOC year")
    parser.add_argument("--epochs", type=int, default=90, help="Number of training epochs")
    parser.add_argument("--batch_size", "--bs", type=int, default=8, help="Batch size")
    parser.add_argument("--size", type=int, default=512, help="Square image resize dimension")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--amp", action="store_true", help="Enable mixed precision")
    parser.add_argument("--num_workers", type=int, default=8, help="Number of dataloader workers")
    parser.add_argument("--download", action="store_true", help="Download VOC if missing")
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
        default=0,
        help="Report running loss every N batches (0 disables explicit periodic reporting)",
    )
    return parser.parse_args()


def resolve_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def build_dataloaders(args: argparse.Namespace, device: torch.device) -> tuple[DataLoader, DataLoader]:
    train_dataset = VOCSeg(
        args.root,
        year=args.year,
        image_set="train",
        img_size=args.size,
        download=args.download,
    )
    val_dataset = VOCSeg(
        args.root,
        year=args.year,
        image_set="val",
        img_size=args.size,
        download=args.download,
    )

    pin_memory = device.type == "cuda"

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=pin_memory,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=pin_memory,
    )
    return train_loader, val_loader


def build_model(device: torch.device) -> torch.nn.Module:
    model = smp.Unet(
        encoder_name="resnet34",
        in_channels=3,
        classes=21,
    )
    return model.to(device)


def estimate_model_memory_bytes(model: torch.nn.Module, batch_size: int, image_size: int) -> int:
    if not torch.cuda.is_available():
        raise RuntimeError("FakeTensor memory estimation currently expects CUDA to be available")

    def input_builder():
        return torch.rand(batch_size, 3, image_size, image_size, requires_grad=True).to("cuda")

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
    model: torch.nn.Module,
    loader: DataLoader,
    loss_fn,
    optimizer: torch.optim.Optimizer,
    scaler: torch.amp.GradScaler,
    device: torch.device,
    use_amp: bool,
    report_every: int,
) -> float:
    model.train(True)
    total = 0.0
    count = 0

    pbar = tqdm(loader, total=len(loader), desc=f"train {epoch}", leave=False)
    for batch_idx, (x, y) in enumerate(pbar, start=1):
        x = x.to(device, non_blocking=device.type == "cuda")
        y = y.to(device, non_blocking=device.type == "cuda")

        optimizer.zero_grad(set_to_none=True)

        with torch.amp.autocast(device_type=device.type, enabled=use_amp and device.type == "cuda"):
            logits = model(x)
            loss = loss_fn(logits, y)

        if device.type == "cuda":
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()

        total += loss.item() * x.size(0)
        count += x.size(0)

        running = total / max(1, count)
        pbar.set_postfix({"loss": f"{running:.4f}"})

        if report_every > 0 and batch_idx % report_every == 0:
            print(f"epoch {epoch} batch {batch_idx}: train_dice_loss={running:.4f}")

    return total / max(1, count)


def evaluate(
    *,
    epoch: int,
    model: torch.nn.Module,
    loader: DataLoader,
    loss_fn,
    device: torch.device,
) -> float:
    model.train(False)
    total = 0.0
    count = 0

    pbar = tqdm(loader, total=len(loader), desc=f"val {epoch}", leave=False)
    with torch.no_grad():
        for x, y in pbar:
            x = x.to(device, non_blocking=device.type == "cuda")
            y = y.to(device, non_blocking=device.type == "cuda")

            logits = model(x)
            loss = loss_fn(logits, y)

            total += loss.item() * x.size(0)
            count += x.size(0)
            pbar.set_postfix({"loss": f"{(total / max(1, count)):.4f}"})

    return total / max(1, count)


def main() -> None:
    args = parse_args()
    device = resolve_device()

    print(f"Using device: {device}")
    print(f"AMP enabled: {args.amp and device.type == 'cuda'}")

    train_loader, val_loader = build_dataloaders(args, device)
    model = build_model(device)

    if args.print_model_summary or args.summary_output is not None:
        summary_input = torch.rand(args.batch_size, 3, args.size, args.size, device=device)
        generate_model_summary(
            model,
            input_data=summary_input,
            print_summary=args.print_model_summary,
            output_path=args.summary_output,
            verbose=0,
        )

    if args.print_faketensor_estimate:
        faketensor_bytes = estimate_model_memory_bytes(model, args.batch_size, args.size)
        print(f"FakeTensor estimated peak memory: {format_memory_gib(faketensor_bytes):.4f} GiB")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    loss_fn = smp.losses.DiceLoss(mode="multiclass")
    scaler = torch.amp.GradScaler(device.type, enabled=args.amp and device.type == "cuda")

    with timed_run() as timer:
        for epoch in range(1, args.epochs + 1):
            train_loss = train_one_epoch(
                epoch=epoch,
                model=model,
                loader=train_loader,
                loss_fn=loss_fn,
                optimizer=optimizer,
                scaler=scaler,
                device=device,
                use_amp=args.amp,
                report_every=args.report_every,
            )
            val_loss = evaluate(
                epoch=epoch,
                model=model,
                loader=val_loader,
                loss_fn=loss_fn,
                device=device,
            )
            print(f"epoch {epoch}: train_dice_loss={train_loss:.4f} val_dice_loss={val_loss:.4f}")

    print(f"\nExecution time: {timer.elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()