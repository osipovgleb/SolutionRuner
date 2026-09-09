from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.algebraic_ratio_from_linear_fraction import (
    build_context_repair_plan,
)


def _context(formula: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "section_id": "condition:1", "html": f'<p><span data-inline-latex="\\frac{{a}}{{b}}"></span><span data-inline-latex="{formula}"></span></p>', "asset_keys": []},
        {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_solves_ratio_and_writes_decimal_answer() -> None:
    plan = build_context_repair_plan(_context(r"\frac{a+3b}{b+3a}=-8"))

    assert plan.answer == "-0,44"
    html = plan.transformations[0]["value"]["html"]
    assert r"a+3b=-8(b+3a)" in html
    assert r"a=-\frac{11}{25}b" in html
    assert r"\frac{a}{b}=\frac{(-\frac{11}{25})b}{b}" in html
    assert r"\frac{a}{b}=\frac{(-\frac{11}{25})b}{b}=-\frac{11}{25}=-0{,}44" in html
    assert "Приведем другое решение" not in html
    assert r"x=\frac{a}{b}" not in html


def test_solves_integer_ratio() -> None:
    plan = build_context_repair_plan(_context(r"\frac{2a+5b}{5a+2b}=1"))

    assert plan.answer == "1"
    html = plan.transformations[0]["value"]["html"]
    assert r"a=b\iff \frac{a}{b}=\frac{b}{b}=1" in html


def test_profile_is_registered() -> None:
    assert all_group_profiles()["26805"].content_rule_key == "algebraic-ratio-from-linear-fraction"
