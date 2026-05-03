from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
    
import argparse

import datasets
import torch
from transformers import (
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
    XLNetForSequenceClassification,
)

from evaluation.workloads.training.common.summaries import generate_model_summary
from evaluation.workloads.training.common.timing import timed_run

from evaluation.workloads.training.common.faketensor_memory_estimation import (
    estimate_faketensor_memory,
    format_memory_gib,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train XLNet-base-cased on WikiText")
    parser.add_argument("--model_name", type=str, default="xlnet-base-cased", help="Pretrained XLNet model name")
    parser.add_argument("--dataset_name", type=str, default="wikitext", help="Dataset name")
    parser.add_argument("--dataset_config", type=str, default="wikitext-2-raw-v1", help="Dataset config")
    parser.add_argument("--max_length", type=int, default=512, help="Maximum sequence length")
    parser.add_argument("--batch_size", type=int, default=8, help="Per-device batch size")
    parser.add_argument("--epochs", type=int, default=8, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--cache_dir", type=str, default=None, help="Optional Hugging Face cache dir")
    parser.add_argument("--output_dir", type=str, default="xlnet_output", help="Trainer output directory")
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
        "--run_evaluate",
        action="store_true",
        help="Run trainer.evaluate() after training when a validation split exists",
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


def build_tokenizer(args: argparse.Namespace):
    return AutoTokenizer.from_pretrained(
        args.model_name,
        use_fast=True,
        cache_dir=args.cache_dir,
    )


def build_datasets(args: argparse.Namespace, tokenizer):
    raw_datasets = datasets.load_dataset(
        args.dataset_name,
        args.dataset_config,
        cache_dir=args.cache_dir,
    )

    def tokenize_function(examples):
        result = tokenizer(
            examples["text"],
            truncation=True,
            max_length=args.max_length,
        )
        result["labels"] = [1] * len(result["input_ids"])
        return result

    tokenized_datasets = raw_datasets.map(
        tokenize_function,
        batched=True,
        remove_columns=raw_datasets["train"].column_names,
    )
    return tokenized_datasets


def build_model(args: argparse.Namespace, device: torch.device):
    model = XLNetForSequenceClassification.from_pretrained(
        args.model_name,
        cache_dir=args.cache_dir,
    )
    return model.to(device)

def estimate_model_memory_bytes(args: argparse.Namespace, model) -> int:
    if not torch.cuda.is_available():
        raise RuntimeError("FakeTensor memory estimation currently expects CUDA to be available")

    def input_builder():
        return {
            "input_ids": torch.randint(
                0,
                model.config.vocab_size,
                (args.batch_size, args.max_length),
                dtype=torch.long,
                device="cuda",
            ),
            "attention_mask": torch.ones(
                args.batch_size,
                args.max_length,
                dtype=torch.long,
                device="cuda",
            ),
            "labels": torch.ones(
                args.batch_size,
                dtype=torch.long,
                device="cuda",
            ),
        }

    def forward_call(fake_batch):
        return model.to("cuda")(**fake_batch).loss

    return estimate_faketensor_memory(
        model,
        input_builder=input_builder,
        forward_call=forward_call,
        run_backward=True,
    )

def maybe_generate_summary(args: argparse.Namespace, model, device: torch.device, tokenizer) -> None:
    if not (args.print_model_summary or args.summary_output is not None):
        return

    try:
        summary_inputs = {
            "input_ids": torch.randint(
                0,
                model.config.vocab_size,
                (args.batch_size, args.max_length),
                dtype=torch.long,
                device=device,
            ),
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
        print(f"Model summary failed: {exc}")


def build_training_arguments(args: argparse.Namespace) -> TrainingArguments:
    return TrainingArguments(
        output_dir=args.output_dir,
        overwrite_output_dir=True,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        save_strategy="no",
        logging_strategy="no",
        report_to=[],
        do_train=True,
        do_eval=False,
        remove_unused_columns=True,
    )


def main() -> None:
    args = parse_args()

    with timed_run() as total_timer:
        device = resolve_device()

        raw_tokenizer = build_tokenizer(args)
        tokenized_datasets = build_datasets(args, raw_tokenizer)
        model = build_model(args, device)
        maybe_generate_summary(args, model, device, raw_tokenizer)

        if args.print_faketensor_estimate:
            try:
                faketensor_bytes = estimate_model_memory_bytes(args, model)
                print(f"FakeTensor estimated peak memory: {format_memory_gib(faketensor_bytes):.4f} GiB")
            except Exception as exc:
                print(f"FakeTensor estimation failed for this XLNet workload: {exc}")


        data_collator = DataCollatorWithPadding(tokenizer=raw_tokenizer)
        training_args = build_training_arguments(args)

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_datasets["train"],
            eval_dataset=tokenized_datasets.get("validation"),
            processing_class=raw_tokenizer,
            data_collator=data_collator,
        )

        with timed_run() as train_timer:
            trainer.train()

            if args.run_evaluate and tokenized_datasets.get("validation") is not None:
                results = trainer.evaluate()
                print(f"Evaluation results: {results}")

    print(f"training_loop_time_s: {train_timer.elapsed_seconds:.2f}")
    print(f"end_to_end_time_s: {total_timer.elapsed_seconds:.2f}")


if __name__ == "__main__":
    main()