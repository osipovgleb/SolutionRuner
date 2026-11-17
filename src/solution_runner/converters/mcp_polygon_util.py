"""Shared deterministic batching and checkpoint utilities."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


def _chunks(values: Sequence[str], size: int) -> Iterator[list[str]]:
    """Yield stable fixed-size list chunks."""

    for start in range(0, len(values), size):
        yield list(values[start : start + size])


def _bounded_map_ordered[T, R](
    values: Sequence[T],
    worker: Callable[[T], R],
    *,
    max_workers: int,
) -> tuple[R, ...]:
    """Run a sliding worker window and return results in input order."""

    if max_workers <= 0:
        raise ValueError("max_workers must be positive")
    if max_workers == 1 or len(values) <= 1:
        return tuple(map(worker, values))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return tuple(executor.map(worker, values))


def _sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest for *data*."""

    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest for one local file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Replace one local JSON checkpoint atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _new_totals() -> Counter[str]:
    """Return an empty run counter with documented keys populated lazily."""

    return Counter()
