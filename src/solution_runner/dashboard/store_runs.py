"""Discover and summarize dashboard run history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return [item for item in payload["results"] if isinstance(item, dict)]
    return []


def _count_status(items: list[dict[str, Any]], *statuses: str) -> int:
    accepted = set(statuses)
    return sum(item.get("status") in accepted for item in items)


def discover_latest_runs(var_dir: Path) -> tuple[dict[str, dict[str, Any]], int]:
    latest: dict[str, dict[str, Any]] = {}
    warnings = 0
    if not var_dir.exists():
        return latest, warnings
    for summary_path in var_dir.glob("**/runs/*/summary.json"):
        summary = _read_json(summary_path)
        if not isinstance(summary, dict) or not summary.get("group_key"):
            warnings += 1
            continue
        group_key = str(summary["group_key"])
        run_name = summary_path.parent.name
        apply_items = _results(_read_json(summary_path.parent / "apply-results.json"))
        if not apply_items:
            apply_items = _results(
                _read_json(summary_path.parent / "solution-results.json")
            )
        helper_items = _results(
            _read_json(summary_path.parent / "helpers-results.json")
        )
        is_apply = (
            bool(summary.get("apply"))
            or (summary_path.parent / "apply-results.json").is_file()
            or any(
                item.get("status") in {"applied", "already_complete"}
                for item in apply_items
            )
        )
        targeted = summary.get("targeted")
        rank = (
            4
            if is_apply and targeted is False
            else 3
            if is_apply and targeted is None
            else 2
            if is_apply
            else 1
            if targeted is False
            else 0
        )
        previous = latest.get(group_key)
        if previous is not None and (
            previous["rank"] > rank
            or (previous["rank"] == rank and previous["run_name"] >= run_name)
        ):
            continue
        errors = max(
            int(summary.get("failed_stage_results", 0) or 0),
            _count_status(apply_items, "failed")
            + _count_status(helper_items, "failed"),
        )
        latest[group_key] = {
            "run_name": run_name,
            "status": str(summary.get("status", "unknown")),
            "total": int(summary.get("targets", 0) or 0),
            "transformed": _count_status(apply_items, "applied", "already_complete"),
            "helpers": _count_status(helper_items, "applied", "already_complete"),
            "errors": errors,
            "blocked": _count_status(apply_items, "blocked")
            + _count_status(helper_items, "blocked"),
            "is_apply": is_apply,
            "rank": rank,
        }
    return latest, warnings
