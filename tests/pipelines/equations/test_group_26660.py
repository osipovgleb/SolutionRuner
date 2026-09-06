import pytest

from solution_runner.pipelines.equations.group_26660 import UnsupportedCondition, build_context_repair_plan


def _context(formula: str, *, answer: str = "", solution: str = "") -> dict:
    sections = [{"key": "condition", "section_id": "condition:1", "asset_keys": [], "html": f'<p>Най­ди­те ко­рень урав­не­ния <span data-inline-latex="{formula}"></span>.</p>'}]
    if answer:
        sections.append({"key": "answer", "section_id": "answer:1", "asset_keys": [], "html": f'<p>{answer}</p>'})
    if solution:
        sections.append({"key": "solution", "section_id": "solution:1", "asset_keys": [], "html": solution})
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": sections}}


@pytest.mark.parametrize(("formula", "answer"), [
    (r"\sqrt{\frac{6}{4x-54}}=\frac{1}{7}", "87"),
    (r"\sqrt{\frac{10}{4x-58}}=\frac{1}{7}", "137"),
    (r"\sqrt{\frac{5}{20-6x}}=\frac{1}{10}", "-80"),
    (r"\sqrt{\frac{5}{3-2x}}=\frac{1}{9}", "-201"),
    (r"\sqrt{\frac{2x+5}{3}}=5", "35"),
    (r"\sqrt{\frac{2x+23}{13}}=5", "151"),
])
def test_solves_the_audited_square_then_proportion_form(formula: str, answer: str) -> None:
    plan = build_context_repair_plan(_context(formula))
    assert plan.answer == answer
    assert r"\iff \frac" in plan.solution_html


@pytest.mark.parametrize(
    ("formula", "answer"),
    [
        (r"\sqrt{\frac{1}{15-4x}}=0{,}2", "-2,5"),
        (r"\sqrt{\frac{3}{19-7x}}=0{,}2", "-8"),
        (r"\sqrt{\frac{6}{4x-54}}=\frac{2}{7}", "31,875"),
    ],
)
def test_normalizes_decimal_or_fractional_right_side_before_squaring(formula: str, answer: str) -> None:
    context = _context(formula)
    context["normalized_content"]["sections"][0]["html"] = (
        f'<p>Решите уравнение <span data-inline-latex="{formula}"></span>.</p>'
    )
    plan = build_context_repair_plan(context)
    assert plan.answer == answer
    assert r"=\frac{1}{5}" in plan.solution_html if "0{,}2" in formula else True


def test_hides_unit_minus_coefficient_in_published_latex() -> None:
    plan = build_context_repair_plan(_context(r"\sqrt{\frac{1}{7-x}}=0{,}5"))
    assert "-x" in plan.solution_html
    assert "-1x" not in plan.solution_html


def test_hides_positive_unit_coefficient_in_published_latex() -> None:
    plan = build_context_repair_plan(_context(r"\sqrt{\frac{1}{x+3}}=0{,}5"))
    assert "x+3" in plan.solution_html
    assert "1x" not in plan.solution_html


def test_does_not_repeat_an_unchanged_integral_right_side() -> None:
    plan = build_context_repair_plan(_context(r"\sqrt{\frac{2x+5}{3}}=5"))
    assert plan.solution_html.count(r"\sqrt{\frac{2x+5}{3}}=5") == 1
