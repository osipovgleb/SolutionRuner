from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from solution_runner.pipelines.core.models import GroupProfile
from solution_runner.pipelines.grid_polygon.runner_probe import (
    RunnerProbeError,
    _resolved_problem_id,
    answers_match,
    probe_context,
    stored_answer,
)


def _profile(group: str, rule: str | None, *, workflow: str = "content_rule") -> GroupProfile:
    return GroupProfile(
        catalog_snapshot_id="catalog",
        snapshot_theme_id="theme",
        source_group_id=f"group-{group}",
        group_key=group,
        group_order_index=0,
        theme_title="Theme",
        theme_order_index=0,
        expected_vertices=None,
        strategy_key=None,
        workflow_kind=workflow,  # type: ignore[arg-type]
        content_rule_key=rule,  # type: ignore[arg-type]
    )


def _context(answer: str | None = "32") -> dict[str, Any]:
    sections: list[dict[str, Any]] = [
        {"key": "condition", "html": "<p>Condition</p>", "asset_keys": []},
        {"key": "solution", "html": "<p>Template</p>", "asset_keys": []},
    ]
    if answer is not None:
        sections.append(
            {"key": "answer", "html": f"<p><span>{answer}</span></p>", "asset_keys": []}
        )
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "sections": sections,
            "assets": [],
        }
    }


@dataclass(frozen=True)
class _Plan:
    answer: str


def test_probe_tries_each_unique_content_rule_once_and_reports_only_answer_matches() -> None:
    calls: list[str] = []

    def build(_context: dict[str, Any], *, content_rule_key: str, **_kwargs: Any) -> _Plan:
        calls.append(content_rule_key)
        if content_rule_key == "reject":
            raise ValueError("condition grammar mismatch")
        return _Plan("32" if content_rule_key == "match" else "31")

    report = probe_context(
        _context(),
        problem_id="problem",
        profiles=(
            _profile("1", "match"),
            _profile("2", "match"),
            _profile("3", "mismatch"),
            _profile("4", "reject"),
            _profile("5", None, workflow="geometry"),
        ),
        plan_builder=build,
    )

    assert calls == ["match", "mismatch", "reject"]
    assert report.unique_rules_tried == 3
    assert report.registered_content_profiles == 4
    assert report.skipped_geometry_profiles == 1
    assert report.answer_mismatches == 1
    assert [(item.content_rule_key, item.registered_groups) for item in report.candidates] == [
        ("match", ("1", "2"))
    ]
    assert report.rejections[0].reason == "condition grammar mismatch"


def test_task_without_stored_answer_is_rejected_before_any_runner() -> None:
    called = False

    def build(*_args: Any, **_kwargs: Any) -> _Plan:
        nonlocal called
        called = True
        return _Plan("1")

    with pytest.raises(RunnerProbeError, match="no stored answer"):
        probe_context(
            _context(None),
            problem_id="problem",
            profiles=(_profile("1", "match"),),
            plan_builder=build,
        )
    assert called is False


def test_answer_comparison_accepts_common_numeric_and_latex_forms() -> None:
    assert answers_match("32,0°", "32")
    assert answers_match(r"\frac{1}{2}", "1/2")
    assert answers_match(r"3\sqrt{2}", "3√2")
    assert not answers_match("31", "32")


def test_stored_answer_reads_inline_latex_when_span_has_no_visible_text() -> None:
    context = _context(None)
    context["normalized_content"]["sections"].append(
        {
            "key": "answer",
            "html": '<p><span data-inline-latex="\\frac{1}{2}"></span></p>',
            "asset_keys": [],
        }
    )
    assert stored_answer(context) == r"\frac{1}{2}"


def test_source_lookup_selects_exact_task_instead_of_partial_match() -> None:
    payload = {
        "matches": [
            {"problem": {"uuid": "wanted", "name": "Задача 60757"}},
            {"problem": {"uuid": "other", "name": "Задача 660757"}},
        ]
    }
    assert _resolved_problem_id(payload, "60757") == "wanted"


def test_source_lookup_rejects_multiple_exact_tasks() -> None:
    payload = {
        "matches": [
            {"problem": {"uuid": "first", "name": "Задача 1"}},
            {"problem": {"uuid": "second", "name": "Задача 1"}},
        ]
    }
    with pytest.raises(RunnerProbeError, match="one exact task"):
        _resolved_problem_id(payload, "1")
