from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_jsonl_event(
    *,
    event_path: str | Path,
    record: dict[str, Any],
) -> None:
    path = Path(event_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, sort_keys=True)
        f.write("\n")