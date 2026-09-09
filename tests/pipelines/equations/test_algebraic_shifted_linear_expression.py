from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.algebraic_shifted_linear_expression import (
    build_context_repair_plan,
)


def _context(target: str, equality: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{target}"></span><span data-inline-latex="{equality}"></span></p>', "asset_keys": []},
        {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_adds_the_constant_difference_after_deriving_zero() -> None:
    plan = build_context_repair_plan(_context(r"61a-11b+50", r"\frac{2a-7b+5}{7a-2b+5}=9"))

    assert plan.answer == "10"
    html = plan.transformations[0]["value"]["html"]
    assert r"61a-11b+40=0" in html
    assert "отличаются на" in html
    assert r"61a-11b+40+10=0+10\iff 61a-11b+50=10" in html


def test_subtracts_when_the_requested_constant_is_smaller() -> None:
    plan = build_context_repair_plan(_context(r"21a-14b-20", r"\frac{3a-4b+2}{4a-3b+2}=6"))

    assert plan.answer == "-30"
    html = plan.transformations[0]["value"]["html"]
    assert r"21a-14b+10-30=0-30\iff 21a-14b-20=-30" in html


def test_reduces_a_common_factor_before_shifting() -> None:
    plan = build_context_repair_plan(_context(r"30a-10b-13", r"\frac{3a-7b+4}{7a-3b+4}=9"))

    assert plan.answer == "-29"
    html = plan.transformations[0]["value"]["html"]
    assert r"60a-20b+32=0\iff 30a-10b+16=0" in html
    assert r"30a-10b+16-29=0-29\iff 30a-10b-13=-29" in html


def test_omits_a_zero_constant() -> None:
    plan = build_context_repair_plan(_context(r"a+b+2", r"\frac{2a-5b+2}{5a-2b+2}=1"))

    html = plan.transformations[0]["value"]["html"]
    assert r"3a+3b=0\iff a+b=0" in html
    assert r"a+b+2=0+2\iff a+b+2=2" in html
    assert "+0" not in html


def test_profile_is_registered() -> None:
    assert all_group_profiles()["26806"].content_rule_key == "algebraic-shifted-linear-expression"
