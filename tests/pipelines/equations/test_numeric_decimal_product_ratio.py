from solution_runner.pipelines.equations.numeric_decimal_product_ratio import (
    build_context_repair_plan,
    build_simple_decimal_product_plan,
)
from solution_runner.pipelines.core.group_profiles import all_group_profiles


def _context(formula: str) -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "title": "Условие",
                    "section_id": "condition:1",
                    "html": f'<p><span data-inline-latex="{formula}"></span></p>',
                    "asset_keys": [],
                },
                {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
            ],
        }
    }


def test_decimal_product_ratio_cancels_matching_integer_factors() -> None:
    plan = build_context_repair_plan(
        _context(r"\frac{1{,}23\cdot45{,}7}{12{,}3\cdot0{,}457}")
    )

    assert plan.answer == "10"
    html = plan.transformations[0]["value"]["html"]
    assert "Умно" in html
    assert r"\frac{123\cdot457\cdot10}{123\cdot457}" in html


def test_decimal_product_ratio_handles_a_single_denominator_factor() -> None:
    plan = build_context_repair_plan(_context(r"\frac{4{,}8\cdot0{,}4}{0{,}6}"))

    assert plan.answer == "3,2"
    assert r"\frac{48\cdot4}{60}" in plan.transformations[0]["value"]["html"]


def test_decimal_product_ratio_corrects_an_inverted_decimal_answer() -> None:
    plan = build_context_repair_plan(_context(r"\frac{1{,}46\cdot47{,}6}{0{,}146\cdot4{,}76}"))

    assert plan.answer == "100"


def test_simple_decimal_product_keeps_existing_parent_solution() -> None:
    context = _context(r"2{,}1\cdot9{,}6")
    context["normalized_content"]["sections"][1]["html"] = "<p>20,16</p>"
    context["normalized_content"]["sections"].append(
        {"key": "solution", "title": "Решение", "html": "<p>Исходное решение.</p>", "asset_keys": []}
    )

    plan = build_simple_decimal_product_plan(context)

    assert plan.answer == "20,16"
    assert plan.transformations == ()


def test_simple_decimal_product_uses_parent_wording_when_solution_missing() -> None:
    plan = build_simple_decimal_product_plan(_context(r"2{,}1\cdot9{,}6"))

    assert plan.answer == "20,16"
    assert "Умножим 21 на 96, получим 2016" in plan.transformations[0]["value"]["html"]
    assert "2,1 · 9,6 = 20,16" in plan.transformations[0]["value"]["html"]


def test_simple_decimal_product_reads_plain_text_condition() -> None:
    context = _context("0")
    context["normalized_content"]["sections"][0]["html"] = "<p>Найдите значение выражения 1,6 · 5,1.</p>"

    assert build_simple_decimal_product_plan(context).answer == "8,16"


def test_decimal_product_ratio_profiles_cover_profile_and_base() -> None:
    profiles = all_group_profiles()
    for key in ("77392", "ege-base-77392"):
        assert profiles[key].content_rule_key == "numeric-decimal-product-ratio"
    assert profiles["349924"].content_rule_key == "numeric-simple-decimal-product"
