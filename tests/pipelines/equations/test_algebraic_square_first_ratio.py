from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.algebraic_square_expansion_ratio import build_context_repair_plan


def _context(formula: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{formula}"></span></p>', "asset_keys": []},
        {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_expands_a_fraction_form_and_adds_the_alternative() -> None:
    plan = build_context_repair_plan(_context(r"\frac{(3x+2y)^{2}-9x^{2}-4y^{2}}{6xy}"))

    assert plan.answer == "2"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{12xy}{6xy}=2" in html
    assert "это задание первой части" in html
    assert r"x=1,\;y=1" in html


def test_accepts_a_colon_form_and_avoids_zero_in_a_difference() -> None:
    plan = build_context_repair_plan(_context(r"((2x-y)^{2}-4x^{2}-y^{2})\colon 2xy"))

    assert plan.answer == "-2"
    html = plan.transformations[0]["value"]["html"]
    assert r"x=1,\;y=1" in html


def test_profile_is_registered() -> None:
    assert all_group_profiles()["26809"].content_rule_key == "algebraic-square-expansion-ratio"


def test_expands_conjugate_squares_and_registers_the_same_handler() -> None:
    plan = build_context_repair_plan(_context(r"\frac{(4x-3y)^{2}-(4x+3y)^{2}}{4xy}"))

    assert plan.answer == "-12"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{-48xy}{4xy}=-12" in html
    assert r"((4x-3y)-(4x+3y))" in html
    assert r"(4x)^{2}-2\cdot4x\cdot3y+(3y)^{2}" in html
    assert r"\frac{(4-3)^{2}-(4+3)^{2}}{4}" in html
    assert "Используем формулу разности квадратов" in html
    assert "Используем формулу квадрата суммы и разности" in html
    assert html.count("Приведём другое решение") == 2
    assert r"x=1,\;y=1" in html
    assert all_group_profiles()["26810"].content_rule_key == "algebraic-square-expansion-ratio"
