from __future__ import annotations

from pathlib import Path


def format_window_suffix(seconds: float) -> str:
    value = float(seconds)
    if value.is_integer():
        return f"w{int(value)}s"
    return f"w{str(value).replace('.', 'p')}s"


def safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "._-+" else "_" for c in value)


def markdown_table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "_No rows._"

    lines = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")

    for row in rows:
        values = [str(row.get(col, "")) for col in columns]
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def relative_link(path: Path, start: Path) -> str:
    try:
        return path.relative_to(start).as_posix()
    except ValueError:
        return path.as_posix()
