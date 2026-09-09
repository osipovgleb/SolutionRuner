from solution_runner.pipelines.equations.numeric_decimal_product_ratio import (
    build_context_repair_plan,
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


def test_decimal_product_ratio_profiles_cover_profile_base_and_oge() -> None:
    profiles = all_group_profiles()
    for key in ("77392", "ege-base-77392", "oge-314236"):
        assert profiles[key].content_rule_key == "numeric-decimal-product-ratio"
