from __future__ import annotations

from pathlib import Path
import yaml


def load_yaml_job_spec(path: str) -> dict:
    with open(Path(path), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)