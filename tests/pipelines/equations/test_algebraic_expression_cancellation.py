from solution_runner.pipelines.equations.algebraic_expression_cancellation import (
    build_context_repair_plan,
)
from solution_runner.pipelines.core.group_profiles import all_group_profiles


def _context(formula: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{formula}"></span></p>', "asset_keys": []},
        {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_common_factor_form_has_factorization_and_substitution_methods() -> None:
    plan = build_context_repair_plan(_context(r"\frac{(11a)^{2}-11a}{11a^{2}-a}"))

    assert plan.answer == "11"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{11a(11a-1)}{a(11a-1)}=11" in html
    assert html.startswith("<center><p><span data-inline-latex=")
    assert html.endswith("</p></center>")
    assert "<b>Приведем другое решение</b>" in html
    assert "переменной" in html and "в ответе быть не может" in html
    assert r"\frac{11^{2}-11}{11-1}=\frac{121-11}{10}=\frac{110}{10}=11" in html


def test_difference_of_squares_reciprocals_has_both_methods() -> None:
    plan = build_context_repair_plan(_context(r"(49a^2-9)\cdot\left(\frac{1}{7a-3}-\frac{1}{7a+3}\right)"))

    assert plan.answer == "6"
    html = plan.transformations[0]["value"]["html"]
    assert r"(49a^2-9)\cdot\frac{7a+3-7a-3}{49a^2-9}=6" in html
    assert "Подставим, например, 5" in html
    assert "знаменателя положительны" not in html
    assert r"(49\cdot 5^2-9)\cdot\left(\frac{1}{7\cdot 5-3}-\frac{1}{7\cdot 5+3}\right)=(1225-9)\cdot\left(\frac{1}{32}-\frac{1}{38}\right)=1216\cdot\frac{38-32}{32\cdot 38}=1216\cdot\frac{6}{1216}=6" in html


def test_difference_of_squares_reciprocals_accepts_braced_square_exponent() -> None:
    plan = build_context_repair_plan(_context(r"(4a^{2}-9)\cdot(\frac{1}{2a-3}-\frac{1}{2a+3})"))

    assert plan.answer == "6"


def test_difference_of_squares_reciprocals_accepts_unit_coefficient() -> None:
    plan = build_context_repair_plan(_context(r"(a^{2}-4)\cdot(\frac{1}{a-2}-\frac{1}{a+2})"))

    assert plan.answer == "4"


def test_difference_of_squares_over_factor_has_both_methods() -> None:
    plan = build_context_repair_plan(_context(r"\frac{9x^{2}-4}{3x+2}-3x"))

    assert plan.answer == "-2"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{(3x-2)(3x+2)}{3x+2}-3x=3x-2-3x=-2" in html
    assert "переменной <span data-inline-latex=\"x\"></span>" in html
    assert r"\frac{9\cdot 1^2-4}{3\cdot 1+2}-3\cdot 1=\frac{5}{5}-3=1-3=-2" in html


def test_conjugate_product_minus_matching_square_has_both_methods() -> None:
    plan = build_context_repair_plan(_context(r"(2x-5)(2x+5)-4x^{2}"))

    assert plan.answer == "-25"
    html = plan.transformations[0]["value"]["html"]
    assert "Используем формулу разности квадратов" in html
    assert r"(2x-5)(2x+5)-4x^{2}=(2x)^{2}-25-4x^{2}=4x^{2}-25-4x^{2}=-25" in html
    assert r"(2\cdot1-5)(2\cdot1+5)-4\cdot1^{2}=(2-5)(2+5)-4=-3\cdot7-4=-25" in html
    assert all_group_profiles()["26811"].content_rule_key == "algebraic-expression-cancellation"


def test_conjugate_product_accepts_the_opposite_factor_order() -> None:
    plan = build_context_repair_plan(_context(r"(3x+4)(3x-4)-9x^{2}"))

    assert plan.answer == "-16"
    assert r"(3\cdot1+4)(3\cdot1-4)-9\cdot1^{2}=(3+4)(3-4)-9=7\cdot-1-9=-16" in plan.transformations[0]["value"]["html"]


def test_profile_is_registered() -> None:
    assert all_group_profiles()["26795"].content_rule_key == "algebraic-expression-cancellation"
    assert all_group_profiles()["26799"].content_rule_key == "algebraic-expression-cancellation"
    assert all_group_profiles()["26802"].content_rule_key == "algebraic-expression-cancellation"
