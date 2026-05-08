#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch
from datasets import load_dataset
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader
from tqdm import tqdm
from transformers import AutoTokenizer, LlamaConfig, LlamaForCausalLM

from evaluation.workloads.training.common.faketensor_memory_estimation import (
    estimate_faketensor_memory,
    format_memory_gib,
)
from evaluation.workloads.training.common.summaries import generate_model_summary
from evaluation.workloads.training.common.timing import timed_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a Llama-3-width 8-layer causal LM on WikiText"
    )
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for training")
    parser.add_argument("--max_steps", type=int, default=50, help="Maximum number of training steps")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--max_length", type=int, default=512, help="Maximum token sequence length")
    parser.add_argument("--dtype", choices=["bf16", "fp16", "fp32"], default="bf16")
    parser.add_argument("--num_workers", type=int, default=0, help="Number of dataloader workers")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--report_every", type=int, default=10)

    parser.add_argument("--dataset_name", type=str, default="wikitext", help="Dataset name")
    parser.add_argument("--dataset_config", type=str, default="wikitext-2-raw-v1", help="Dataset config")
    parser.add_argument("--dataset_split", type=str, default="train", help="Dataset split")
    parser.add_argument("--tokenizer_name", type=str, default="gpt2", help="Tokenizer name")
    parser.add_argument("--cache_dir", type=str, default=None, help="Optional Hugging Face cache dir")

    parser.add_argument("--vocab_size", type=int, default=128256)
    parser.add_argument("--hidden_size", type=int, default=4096)
    parser.add_argument("--intermediate_size", type=int, default=14336)
    parser.add_argument("--num_hidden_layers", type=int, default=8)
    parser.add_argument("--num_attention_heads", type=int, default=32)
    parser.add_argument("--num_key_value_heads", type=int, default=8)

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
        help="Try FakeTensor memory estimation before training",
    )

    return parser.parse_args()


def resolve_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def resolve_dtype(name: str) -> torch.dtype:
    if name == "bf16":
        return torch.bfloat16
    if name == "fp16":
        return torch.float16
    return torch.float32


def build_tokenizer(args: argparse.Namespace):
    tokenizer = AutoTokenizer.from_pretrained(
        args.tokenizer_name,
        cache_dir=args.cache_dir,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def build_dataloader(args: argparse.Namespace, tokenizer) -> DataLoader:
    dataset = load_dataset(
        args.dataset_name,
        args.dataset_config,
        split=args.dataset_split,
        cache_dir=args.cache_dir,
    )

    dataset = dataset.filter(lambda x: len(str(x["text"]).strip()) > 0)

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            padding="max_length",
            max_length=args.max_length,
        )

    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
    )
    tokenized_dataset.set_format(type="torch", columns=["input_ids", "attention_mask"])

    return DataLoader(
        tokenized_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available(),
    )


def build_model(args: argparse.Namespace, device: torch.device) -> LlamaForCausalLM:
    config = LlamaConfig(
        vocab_size=args.vocab_size,
        hidden_size=args.hidden_size,
        intermediate_size=args.intermediate_size,
        num_hidden_layers=args.num_hidden_layers,
        num_attention_heads=args.num_attention_heads,
        num_key_value_heads=args.num_key_value_heads,
        max_position_embeddings=max(args.max_length, 512),
    )

    model = LlamaForCausalLM(config=config)
    dtype = resolve_dtype(args.dtype)
    return model.to(dtype=dtype).to(device)


def estimate_model_memory_bytes(
    model: LlamaForCausalLM,
    *,
    batch_size: int,
    max_length: int,
    vocab_size: int,
) -> int:
    if not torch.cuda.is_available():
        raise RuntimeError("FakeTensor memory estimation currently expects CUDA to be available")

    def input_builder():
        input_ids = torch.randint(
            0,
            vocab_size,
            (batch_size, max_length),
            dtype=torch.long,
            device="cuda",
        )
        return {
            "input_ids": input_ids,
            "attention_mask": torch.ones(
                batch_size,
                max_length,
                dtype=torch.long,
                device="cuda",
            ),
            "labels": input_ids.clone(),
        }

    def forward_call(fake_batch):
        return model.to("cuda")(**fake_batch).loss

    return estimate_faketensor_memory(
        model,
        input_builder=input_builder,
        forward_call=forward_call,
        run_backward=True,
    )


def maybe_generate_summary(
    *,
    args: argparse.Namespace,
    model: LlamaForCausalLM,
    device: torch.device,
) -> None:
    if not args.print_model_summary and args.summary_output is None:
        return

    try:
        summary_input_ids = torch.randint(
            0,
            args.vocab_size,
            (args.batch_size, args.max_length),
            dtype=torch.long,
            device=device,
        )
        summary_inputs = {
            "input_ids": summary_input_ids,
            "attention_mask": torch.ones(
                args.batch_size,
                args.max_length,
                dtype=torch.long,
                device=device,
            ),
        }
        generate_model_summary(
            model,
            input_data=summary_inputs,
            print_summary=args.print_model_summary,
            output_path=args.summary_output,
            verbose=0,
        )
    except Exception as exc:
        print(f"Model summary failed: {exc}", flush=True)


def maybe_print_faketensor_estimate(
    *,
    args: argparse.Namespace,
    model: LlamaForCausalLM,
) -> None:
    if not args.print_faketensor_estimate:
        return

    try:
        faketensor_bytes = estimate_model_memory_bytes(
            model,
            batch_size=args.batch_size,
            max_length=args.max_length,
            vocab_size=args.vocab_size,
        )
        print(
            f"FakeTensor estimated peak memory: {format_memory_gib(faketensor_bytes):.4f} GiB",
            flush=True,
        )
    except Exception as exc:
        print(f"FakeTensor estimation failed for this Llama workload: {exc}", flush=True)


def train_steps(
    *,
    args: argparse.Namespace,
    model: LlamaForCausalLM,
    train_dataloader: DataLoader,
    optimizer: AdamW,
    scheduler: CosineAnnealingLR,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    steps_run = 0

    progress = tqdm(train_dataloader, total=args.max_steps)

    for step, batch in enumerate(progress, start=1):
        if step > args.max_steps:
            break

        input_ids = batch["input_ids"].to(device, non_blocking=True)
        attention_mask = batch["attention_mask"].to(device, non_blocking=True)
        labels = input_ids.clone()

        optimizer.zero_grad(set_to_none=True)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )
        loss = outputs.loss

        loss.backward()
        optimizer.step()
        scheduler.step()

        loss_value = float(loss.detach().cpu())
        total_loss += loss_value
        steps_run += 1

        progress.set_description(f"step={step}/{args.max_steps} loss={loss_value:.4f}")

        if args.report_every > 0 and (step == 1 or step % args.report_every == 0):
            print(f"step={step} loss={loss_value:.4f}", flush=True)

    avg_loss = total_loss / steps_run if steps_run > 0 else 0.0
    print(f"Training completed. Steps: {steps_run}. Average loss: {avg_loss:.4f}", flush=True)
    return avg_loss


def main() -> None:
    args = parse_args()

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    torch.set_num_threads(1)

    with timed_run() as total_timer:
        device = resolve_device()

        tokenizer = build_tokenizer(args)
        train_dataloader = build_dataloader(args, tokenizer)
        model = build_model(args, device)

        maybe_generate_summary(args=args, model=model, device=device)
        maybe_print_faketensor_estimate(args=args, model=model)

        optimizer = AdamW(model.parameters(), lr=args.lr)
        scheduler = CosineAnnealingLR(optimizer, T_max=max(1, args.max_steps))

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats(device)

        with timed_run() as train_timer:
            avg_loss = train_steps(
                args=args,
                model=model,
                train_dataloader=train_dataloader,
                optimizer=optimizer,
                scheduler=scheduler,
                device=device,
            )

    if torch.cuda.is_available():
        peak_memory_mib = torch.cuda.max_memory_allocated(device) / (1024 * 1024)
        print(f"torch_peak_memory_allocated_mib: {peak_memory_mib:.2f}", flush=True)

    print(f"final_loss: {avg_loss:.4f}", flush=True)
    print(f"training_loop_time_s: {train_timer.elapsed_seconds:.2f}", flush=True)
    print(f"end_to_end_time_s: {total_timer.elapsed_seconds:.2f}", flush=True)


if __name__ == "__main__":
    main()
