from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.algebraic_proportional_linear_ratio import build_context_repair_plan


def _context(target: str, ratio: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{target}"></span><span data-inline-latex="{ratio}"></span></p>', "asset_keys": []},
        {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_substitutes_a_from_the_given_ratio_and_cancels() -> None:
    plan = build_context_repair_plan(_context(r"\frac{a+9b+16}{a+3b+8}", r"\frac{a}{b}=3"))

    assert plan.answer == "2"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{a}{b}=3\iff a=3b" in html
    assert r"\frac{12b+16}{6b+8}=\frac{2(6b+8)}{6b+8}=2" in html


def test_accepts_an_implicit_unit_coefficient_of_b() -> None:
    plan = build_context_repair_plan(_context(r"\frac{a+5b+22}{a+b+11}", r"\frac{a}{b}=3"))

    assert plan.answer == "2"


def test_group_is_registered() -> None:
    assert all_group_profiles()["26807"].content_rule_key == "algebraic-proportional-linear-ratio"
