"""Shared dashboard state classification."""

from datetime import UTC, datetime

from .catalogs import catalog_label as _catalog_label


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


_source_label = _catalog_label


def _system_column(
    *,
    registered: bool,
    has_run: bool,
    total: int,
    transformed: int,
    helpers: int,
    errors: int,
    blocked: int,
) -> str:
    if errors or blocked:
        return "issues"
    # A profile arriving through Git does not establish local runner readiness.
    if not has_run:
        return "queue"
    if 0 < total <= 5 and transformed >= total and helpers >= total:
        return "review"
    if total > 0 and helpers >= total:
        return "done"
    if has_run and transformed >= total > 0:
        return "work"
    if has_run:
        return "review"
    return "queue"
