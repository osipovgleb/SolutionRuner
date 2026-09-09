from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.algebraic_power_cancellation import (
    build_context_repair_plan,
)


def _context(formula: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{formula}"></span></p>', "asset_keys": []},
        {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_power_cancellation_has_parent_and_substitution_methods() -> None:
    plan = build_context_repair_plan(_context(r"\frac{(5a^{2})^{3}\cdot(6b)^{2}}{(30a^{3}b)^{2}}"))

    assert plan.answer == "5"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{5^{3}a^{6}\cdot6^{2}b^{2}}{30^{2}a^{6}b^{2}}" in html
    assert "<p><b>Приведем другое решение</b></p>" in html
    assert r"\frac{(5\cdot1^{2})^{3}\cdot(6\cdot1)^{2}}{(30\cdot1^{3}\cdot1)^{2}}" in html


def test_profile_is_registered() -> None:
    assert all_group_profiles()["26797"].content_rule_key == "algebraic-power-cancellation"
