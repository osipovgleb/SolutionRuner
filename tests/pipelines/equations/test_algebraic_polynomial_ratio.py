from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.algebraic_polynomial_ratio import build_context_repair_plan


def _context(definition: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{definition}"></span></p>', "asset_keys": []},
        {"key": "answer", "title": "Ответ", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_plus_form_calculates_b_and_inverse_before_ratio() -> None:
    plan = build_context_repair_plan(_context(r"p(b)=(b+\frac{3}{b})(3b+\frac{1}{b})"))

    assert plan.answer == "1"
    html = plan.transformations[0]["value"]["html"]
    assert r"p(b)=(b+\frac{3}{b})(3b+\frac{1}{b})" in html
    assert r"p(\frac{1}{b})=(\frac{1}{b}+\frac{3}{\frac{1}{b}})(\frac{3}{b}+\frac{1}{\frac{1}{b}})=(\frac{1}{b}+3b)(\frac{3}{b}+b)" in html
    assert r"\frac{p(b)}{p(\frac{1}{b})}=\frac{(b+\frac{3}{b})(3b+\frac{1}{b})}{(\frac{1}{b}+3b)(\frac{3}{b}+b)}=1" in html
    assert "<b>Приведем другое решение</b>" in html
    assert "Подставим, например, 1" in html
    assert r"\frac{(1+\frac{3}{1})(1\cdot 3+\frac{1}{1})}{(\frac{1}{1}+1\cdot 3)(\frac{3}{1}+1)}=\frac{4\cdot 4}{4\cdot 4}=1" in html


def test_minus_form_is_supported() -> None:
    plan = build_context_repair_plan(_context(r"p(b)=(b-\frac{9}{b})(-9b+\frac{1}{b})"))

    assert plan.answer == "1"
    html = plan.transformations[0]["value"]["html"]
    assert r"p(b)=(b-\frac{9}{b})(-9b+\frac{1}{b})" in html
    assert r"p(\frac{1}{b})=(\frac{1}{b}-\frac{9}{\frac{1}{b}})(-\frac{9}{b}+\frac{1}{\frac{1}{b}})=(\frac{1}{b}-9b)(-\frac{9}{b}+b)" in html


def test_profile_is_registered() -> None:
    assert all_group_profiles()["26803"].content_rule_key == "algebraic-polynomial-reciprocal-ratio"
