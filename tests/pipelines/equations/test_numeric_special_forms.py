from fractions import Fraction

from solution_runner.pipelines.equations.numeric_special_forms import (
    _finish,
    build_conjugate_product_plan,
    build_fraction_division_plan,
    build_square_difference_plan,
)


def _context(formula: str) -> dict:
    return {"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "section_id": "condition:1", "html": f'<p><span data-inline-latex="{formula}"></span></p>', "asset_keys": []},
        {"key": "answer", "section_id": "answer:1", "html": "<p></p>", "asset_keys": []},
    ]}}


def test_square_difference_division_uses_parent_identity() -> None:
    plan = build_square_difference_plan(_context(r"(432^{2}-568^{2})\colon1000"))
    assert plan.answer == "-136"
    assert r"\frac{(432-568)(432+568)}{1000}" in plan.transformations[0]["value"]["html"]


def test_fraction_division_converts_and_finishes_as_decimal() -> None:
    plan = build_fraction_division_plan(_context(r"1\frac{1}{5}\colon\frac{3}{2}"))
    assert plan.answer == "0,8"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{6}{5}\cdot\frac{2}{3}" in html
    assert r"\frac{4}{5}=\frac{8}{10}=0{,}8" in html


def test_fraction_runner_accepts_product_and_cancels_before_multiplying() -> None:
    plan = build_fraction_division_plan(_context(r"\frac{15}{2}\cdot\frac{7}{5}"))

    assert plan.answer == "10,5"
    html = plan.transformations[0]["value"]["html"]
    assert r"\frac{3}{2}\cdot\frac{7}{1}" in html
    assert r"\frac{21}{2}=\frac{105}{10}=10{,}5" in html


def test_conjugate_product_uses_the_difference_of_squares() -> None:
    plan = build_conjugate_product_plan(_context(r"(\sqrt{11}-3)(\sqrt{11}+3)"))
    assert plan.answer == "2"
    assert r"(\sqrt{11})^{2}-3^{2}=11-9=2" in plan.transformations[0]["value"]["html"]


def test_conjugate_runner_accepts_two_radical_terms_and_dot() -> None:
    plan = build_conjugate_product_plan(_context(r"(\sqrt{7}-\sqrt{5})\cdot(\sqrt{7}+\sqrt{5})"))

    assert plan.answer == "2"
    assert r"(\sqrt{7})^{2}-(\sqrt{5})^{2}=7-5=2" in plan.transformations[0]["value"]["html"]


def test_radical_factor_runner_simplifies_before_multiplying() -> None:
    from solution_runner.pipelines.equations.numeric_special_forms import build_radical_factor_plan

    plan = build_radical_factor_plan(_context(r"(\sqrt{50}-\sqrt{2})\cdot\sqrt{2}"))

    assert plan.answer == "8"
    assert r"(5\sqrt{2}-\sqrt{2})\cdot\sqrt{2}" in plan.transformations[0]["value"]["html"]


def test_conjugate_profile_routes_radical_factor_form_to_its_planner() -> None:
    plan = build_conjugate_product_plan(_context(r"(\sqrt{50}-\sqrt{2})\cdot\sqrt{2}"))

    assert plan.answer == "8"


def test_finish_makes_negative_terminating_fraction_explicit() -> None:
    assert _finish(Fraction(-2, 5)) == ("-\\frac{2}{5}", "\\frac{-4}{10}", "-0{,}4")


def test_finish_uses_required_power_of_ten_for_all_2_and_5_denominators() -> None:
    assert _finish(Fraction(1, 8)) == ("\\frac{1}{8}", "\\frac{125}{1000}", "0{,}125")
    assert _finish(Fraction(1, 25)) == ("\\frac{1}{25}", "\\frac{4}{100}", "0{,}04")


def _root_context(formula: str) -> dict:
    context = _context(formula)
    context['normalized_content']['sections'][0]['html'] = (
        f'<p>Найдите значение выражения <span data-inline-latex="{formula}"></span>.</p>'
    )
    return context


def test_root_product_factors_and_pairs_roots_in_parent_style() -> None:
    from solution_runner.pipelines.equations.numeric_special_forms import build_root_product_plan
    from bs4 import BeautifulSoup

    plan = build_root_product_plan(_root_context(r'3\sqrt{19}\cdot3\sqrt{2}\cdot\sqrt{38}'))
    assert plan.answer == '342'
    soup = BeautifulSoup(plan.transformations[0]['value']['html'], 'html.parser')
    lines = [span['data-inline-latex'] for span in soup.select('center span')]
    assert len(lines) == 6
    assert r'\sqrt{2\cdot19}' in lines[1]
    assert r'(\sqrt{19})^{2}' in lines[3]
    assert lines[-2:] == [r'=3\cdot3\cdot2\cdot19', '=342']


def test_root_product_handles_two_roots_and_existing_radical_difference() -> None:
    from solution_runner.pipelines.equations.numeric_special_forms import build_root_product_plan

    assert build_root_product_plan(_root_context(r'\sqrt{45}\cdot\sqrt{605}')).answer == '165'
    assert build_root_product_plan(_root_context(r'(\sqrt{45}-\sqrt{5})\cdot\sqrt{5}')).answer == '10'
    assert build_root_product_plan(_root_context(r'\sqrt{11}\cdot\sqrt{18}\cdot\sqrt{22}')).answer == '66'
    assert build_root_product_plan(_root_context(r'\sqrt{11}\cdot\sqrt{32}\cdot\sqrt{22}')).answer == '88'


def test_root_product_rejects_ambiguous_or_irrational_input() -> None:
    import pytest
    from solution_runner.pipelines.equations.numeric_special_forms import build_root_product_plan
    from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError

    for formula in (
        r'\sqrt{11 * 18 * \text{thesquarerootof} 22}',
        r'\sqrt{11 * 32 * thesquarerootof22}',
        r'\sqrt{2}\cdot\sqrt{3}',
        r'\sqrt{-2}\cdot\sqrt{-2}',
        r'\sqrt{2}+\sqrt{2}',
    ):
        with pytest.raises(RightTrianglePlanError):
            build_root_product_plan(_root_context(formula))


def test_root_product_is_idempotent_after_local_transformations() -> None:
    from solution_runner.pipelines.equations.numeric_special_forms import build_root_product_plan

    context = _root_context(r'5\sqrt{11}\cdot2\sqrt{2}\cdot\sqrt{22}')
    plan = build_root_product_plan(context)
    assert plan.answer == '220'
    for change in plan.transformations:
        key = 'solution' if change['value']['title'] == 'Решение' else 'answer'
        sections = context['normalized_content']['sections']
        sections[:] = [section for section in sections if section['key'] != key]
        sections.append(dict(change['value'], key=key, section_id=f'{key}:1'))
    assert build_root_product_plan(context).transformations == ()


def test_group_137285_uses_root_product_and_preserves_editorial_solutions() -> None:
    from solution_runner.pipelines.core.group_profiles import all_group_profiles

    profile = all_group_profiles()['137285']
    assert profile.source_group_id == 'e7e4fee3-dbff-4c84-91c0-8b085d15e96e'
    assert profile.content_rule_key == 'numeric-root-product'
    assert profile.existing_solution_policy == 'preserve'
