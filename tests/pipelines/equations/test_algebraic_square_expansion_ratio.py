from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.algebraic_square_expansion_ratio import (
    build_context_repair_plan,
)


def _context(formula: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{formula}"></span></p>', "asset_keys": []},
        {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_expands_a_difference_inside_the_square() -> None:
    plan = build_context_repair_plan(_context(r"(4x^{2}+y^{2}-(2x-y)^{2})\colon(2xy)"))

    assert plan.answer == "2"
    html = plan.transformations[0]["value"]["html"]
    assert r"-(4x^{2}-4xy+y^{2})" in html
    assert r"\frac{4xy}{2xy}=2" in html
    assert "<b>Приведём другое решение</b>" in html
    assert "это задание первой части" in html
    assert "должны сократиться" in html
    assert "сократиться. </p><p>Подставим" in html
    assert r"x=1,\;y=1" in html


def test_preserves_the_negative_denominator() -> None:
    plan = build_context_repair_plan(_context(r"(x^{2}+16y^{2}-(x+4y)^{2})\colon(-4xy)"))

    assert plan.answer == "2"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{-8xy}{-4xy}=2" in html


def test_accepts_a_denominator_without_parentheses() -> None:
    plan = build_context_repair_plan(_context(r"(25x^{2}+y^{2}-(5x+y)^{2})\colon 2xy"))

    assert plan.answer == "-5"


def test_changes_the_default_when_it_would_zero_the_binomial() -> None:
    plan = build_context_repair_plan(_context(r"(x^{2}+y^{2}-(x-y)^{2})\colon 2xy"))

    html = plan.transformations[0]["value"]["html"]
    assert r"x=2,\;y=1" in html
    assert r"(1\cdot2-1\cdot1)^{2}" in html


def test_profile_is_registered() -> None:
    assert all_group_profiles()["26808"].content_rule_key == "algebraic-square-expansion-ratio"
