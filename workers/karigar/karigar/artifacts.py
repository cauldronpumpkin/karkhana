from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_artifact(path: Path, data: dict[str, Any]) -> Path:
    """Write a normalized JSON artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_text_artifact(path: Path, content: str) -> Path:
    """Write a text artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def normalize_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
