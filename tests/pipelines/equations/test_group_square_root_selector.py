"""Coverage for square-root equation groups 510159 and 510165."""

from __future__ import annotations

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.group_square_root_selector import (
    RULE,
    UnsupportedCondition,
    build_context_repair_plan,
)


def _context(formula: str, choice: str, *, split_instruction: bool = False) -> dict:
    instruction = f"Если уравнение имеет более одного корня, в ответе укажите {choice} из них."
    condition = (
        f'<p>Ре­ши­те урав­не­ние <span data-inline-latex="{formula}"></span>.</p>'
        + (f"<p>{instruction}</p>" if split_instruction else instruction)
    )
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {"key": "condition", "section_id": "condition:1", "asset_keys": [], "html": condition},
                {"key": "answer", "section_id": "answer:1", "asset_keys": [], "html": "<p></p>"},
            ],
        }
    }


def _solution(plan) -> str:
    return next(item["value"]["html"] for item in plan.transformations if "solution" in item["transformation_target_id"])


def test_groups_are_registered_on_the_shared_square_root_selector() -> None:
    handler = get_handler(RULE)

    assert get_group_profile("510159").content_rule_key == RULE
    assert get_group_profile("510165").content_rule_key == RULE
    assert handler.target.endswith("group_square_root_selector:build_context_repair_plan")


@pytest.mark.parametrize(
    ("formula", "choice", "split_instruction", "expected"),
    [
        (r"x^{2}=16", "больший", True, "4"),
        (r"x^{2}-4=0", "больший", True, "2"),
        (r"x^{2}-16=0", "меньший", False, "-4"),
    ],
)
def test_selects_requested_root_in_both_supported_forms(
    formula: str, choice: str, split_instruction: bool, expected: str
) -> None:
    plan = build_context_repair_plan(_context(formula, choice, split_instruction=split_instruction))

    assert plan.answer == expected
    assert f"x={expected}" in _solution(plan)


def test_shifted_form_uses_the_parent_solution_sequence() -> None:
    plan = build_context_repair_plan(_context(r"x^{2}-4=0", "больший", split_instruction=True))

    assert r"x^{2}-4=0\iff x^{2}=4\iff \left[\begin{aligned}x=-2\\x=2\end{aligned}\right." in _solution(plan)
    assert "наи­боль­ший ко­рень" in _solution(plan)


@pytest.mark.parametrize("formula", [r"x^{2}=12", r"x^{2}+4=0", r"x^{2}=0"])
def test_unsupported_forms_fail_closed(formula: str) -> None:
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(_context(formula, "больший"))
