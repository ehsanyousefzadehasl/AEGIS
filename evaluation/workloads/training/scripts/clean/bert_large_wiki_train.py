from __future__ import annotations

import argparse

import torch
from datasets import load_dataset
from torch.optim import AdamW
from torch.utils.data import DataLoader
from tqdm import tqdm
from transformers import (
    BertConfig,
    BertForMaskedLM,
    BertTokenizer,
    DataCollatorForLanguageModeling,
)

from evaluation.workloads.training.common.faketensor_memory_estimation import (
    estimate_faketensor_memory,
    format_memory_gib,
)
from evaluation.workloads.training.common.summaries import generate_model_summary
from evaluation.workloads.training.common.timing import timed_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train BERT-large MLM on WikiText")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size for training")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--max_length", type=int, default=512, help="Maximum sequence length")
    parser.add_argument("--num_workers", type=int, default=0, help="Number of dataloader workers")
    parser.add_argument("--dataset_name", type=str, default="wikitext", help="Dataset name")
    parser.add_argument("--dataset_config", type=str, default="wikitext-2-raw-v1", help="Dataset config")
    parser.add_argument("--dataset_split", type=str, default="train", help="Dataset split")
    parser.add_argument("--tokenizer_name", type=str, default="bert-large-cased", help="Tokenizer name")
    parser.add_argument("--cache_dir", type=str, default=None, help="Optional Hugging Face cache dir")
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
    parser.add_argument(
        "--report_every",
        type=int,
        default=100,
        help="Report training progress every N steps",
    )
    return parser.parse_args()


def resolve_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def build_tokenizer(args: argparse.Namespace) -> BertTokenizer:
    return BertTokenizer.from_pretrained(
        args.tokenizer_name,
        cache_dir=args.cache_dir,
    )


def build_dataloader(args: argparse.Namespace, tokenizer: BertTokenizer) -> DataLoader:
    dataset = load_dataset(
        args.dataset_name,
        args.dataset_config,
        split=args.dataset_split,
        cache_dir=args.cache_dir,
    )

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=args.max_length,
            return_special_tokens_mask=True,
        )

    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=0.15,
    )

    return DataLoader(
        tokenized_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=data_collator,
        num_workers=args.num_workers,
    )


def build_model(tokenizer: BertTokenizer, max_length: int, device: torch.device) -> BertForMaskedLM:
    config = BertConfig(
        vocab_size=tokenizer.vocab_size,
        hidden_size=1024,
        num_hidden_layers=24,
        num_attention_heads=16,
        intermediate_size=4096,
        max_position_embeddings=max_length,
        type_vocab_size=2,
        hidden_act="gelu",
        initializer_range=0.02,
        layer_norm_eps=1e-12,
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
    )
    model = BertForMaskedLM(config=config)
    return model.to(device)


def estimate_model_memory_bytes(
    model: BertForMaskedLM,
    *,
    batch_size: int,
    max_length: int,
    vocab_size: int,
) -> int:
    if not torch.cuda.is_available():
        raise RuntimeError("FakeTensor memory estimation currently expects CUDA to be available")

    def input_builder():
        return {
            "input_ids": torch.randint(
                0,
                vocab_size,
                (batch_size, max_length),
                dtype=torch.long,
                device="cuda",
            ),
            "attention_mask": torch.ones(
                batch_size,
                max_length,
                dtype=torch.long,
                device="cuda",
            ),
        }

    def forward_call(fake_batch):
        return model.to("cuda")(**fake_batch).logits

    return estimate_faketensor_memory(
        model,
        input_builder=input_builder,
        forward_call=forward_call,
        run_backward=True,
    )


def train_one_epoch(
    *,
    epoch: int,
    model: BertForMaskedLM,
    train_dataloader: DataLoader,
    optimizer: AdamW,
    device: torch.device,
    report_every: int,
) -> float:
    model.train()
    total_loss = 0.0

    for step, batch in enumerate(tqdm(train_dataloader), start=1):
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)

        optimizer.zero_grad()

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
        )
        loss = outputs.loss

        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        if report_every > 0 and step % report_every == 0:
            print(f"epoch={epoch} step={step} loss={loss.item():.4f}")

    avg_loss = total_loss / len(train_dataloader)
    print(f"Epoch {epoch} completed. Average loss: {avg_loss:.4f}")
    return avg_loss


def main() -> None:
    args = parse_args()
    device = resolve_device()

    tokenizer = build_tokenizer(args)
    train_dataloader = build_dataloader(args, tokenizer)
    model = build_model(tokenizer, args.max_length, device)

    if args.print_model_summary or args.summary_output is not None:
        try:
            summary_inputs = {
                "input_ids": torch.randint(
                    0,
                    tokenizer.vocab_size,
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

    if args.print_faketensor_estimate:
        try:
            faketensor_bytes = estimate_model_memory_bytes(
                model,
                batch_size=args.batch_size,
                max_length=args.max_length,
                vocab_size=tokenizer.vocab_size,
            )
            print(f"FakeTensor estimated peak memory: {format_memory_gib(faketensor_bytes):.4f} GiB")
        except Exception as exc:
            print(f"FakeTensor estimation failed for this BERT-large workload: {exc}")

    optimizer = AdamW(model.parameters(), lr=args.lr)

    with timed_run() as timer:
        for epoch in range(1, args.epochs + 1):
            train_one_epoch(
                epoch=epoch,
                model=model,
                train_dataloader=train_dataloader,
                optimizer=optimizer,
                device=device,
                report_every=args.report_every,
            )

    print(f"\nExecution time: {timer.elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()