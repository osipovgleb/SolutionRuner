"""Persist and read dashboard apply state atomically."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def write_apply_state(state_dir: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(state)
    state_dir.mkdir(parents=True, exist_ok=True)
    target = state_dir / f"{payload['group_key']}.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(target)
    return payload


def read_apply_state(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None
