"""Load the human-readable catalog registry used by the local dashboard."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CATALOGS_PATH = Path(__file__).resolve().parents[3] / "config/catalogs.json"


def load_catalogs(path: Path = DEFAULT_CATALOGS_PATH) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(catalog_id): str(name).strip()
        for catalog_id, name in payload.items()
        if str(catalog_id).strip() and str(name).strip()
    }


def catalog_label(catalog_id: str) -> str:
    return load_catalogs().get(catalog_id, f"Каталог {catalog_id[:8]}")
