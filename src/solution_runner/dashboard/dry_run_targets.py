"""Select eligible targets for dashboard dry-runs."""

from __future__ import annotations

import secrets
from collections.abc import Callable, Mapping, Sequence
from typing import Any


class NoDryRunTarget(ValueError):
    """The requested sample has no task eligible for this registered runner."""


def _source_problem_id(item: Mapping[str, Any]) -> str:
    value = item.get("source_problem_id")
    if value:
        return str(value)
    return str(item.get("name") or "").removeprefix("Задача ").strip()


def _problem_id(item: Mapping[str, Any]) -> str:
    return str(item.get("uuid") or item.get("problem_id") or item.get("id") or "")


def _child_rows(
    children: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if isinstance(children, Mapping):
        rows = children.get("children")
        if not isinstance(rows, list):
            rows = children.get("items")
    else:
        rows = children
    return [item for item in rows or [] if isinstance(item, Mapping)]


def _select_problem(
    children: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    mode: str,
    *,
    choose: Callable[[Sequence[Mapping[str, Any]]], Mapping[str, Any]] = secrets.choice,
    excluded_problem_ids: set[str] | frozenset[str] = frozenset(),
    requested_problem_id: str | None = None,
) -> Mapping[str, Any] | None:
    if mode == "all":
        return None
    problems = [
        item
        for item in _child_rows(children)
        if _problem_id(item)
        and _source_problem_id(item)
        and _problem_id(item) not in excluded_problem_ids
    ]
    if not problems:
        raise NoDryRunTarget("group has no source problems")
    if mode == "parent":
        return problems[0]
    if mode == "problem":
        selected = next(
            (item for item in problems if _problem_id(item) == requested_problem_id),
            None,
        )
        if selected is None:
            raise NoDryRunTarget("requested problem is not eligible in this group")
        return selected
    if mode == "random":
        if len(problems) < 2:
            raise NoDryRunTarget("group has no eligible child problem")
        return choose(problems[1:])
    raise ValueError("unknown dry-run mode")
