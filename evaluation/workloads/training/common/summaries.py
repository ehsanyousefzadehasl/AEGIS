from __future__ import annotations

from pathlib import Path
from typing import Any

from torchinfo import summary


def generate_model_summary(
    model,
    input_data: Any,
    *,
    print_summary: bool = False,
    output_path: str | None = None,
    **summary_kwargs,
) -> str:
    result = summary(model, input_data=input_data, **summary_kwargs)
    text = str(result)

    if print_summary:
        print(text)

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")

    return text