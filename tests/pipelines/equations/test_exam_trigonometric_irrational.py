"""Original radical domains, all parent methods and finite complete root sets."""

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_bounded_log import (
    compile_log,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.equations.exam_trigonometric_radical_equation import (
    CIRCLE,
    compile_radical,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_irrational.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
EXPECTED = {
    "532656": ("2/3", "8/3"),
    "546982": ("2/3", "-16/3 -10/3 -4/3"),
    "624602": ("3/2", "7/2"),
    "635085": ("1/4", "17/4 25/4"),
    "635565": ("-7/6 1/6 5/6", "-7/6"),
    "637853": ("5/3", "-7/3"),
}
ORIGINAL = {
    "532656": (4 * sp.sin(3 * sp.pi / 2 + X) * (c - 1) + 3) / sp.sqrt(s),
    "546982": s * sp.sqrt(3 - sp.tan(3 * X / 2) ** 2) - c - 2,
    "624602": sp.sqrt(sp.cos(2 * X) - sp.sin(5 * X)) + 2 * c,
    "635085": s**3 * (1 + sp.cot(X)) + c**3 * (1 + sp.tan(X)) - 2 * sp.sqrt(s * c),
    "635565": 2 * (sp.log(s) / sp.log(4)) ** 2
    - X * X
    + 21
    - sp.sqrt(25 - X * X) ** 2
    - 7 * sp.log(s) / sp.log(4),
    "637853": (4 * s * s + 12 * c - 9) / sp.sqrt(-2 * sp.tan(X)),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(example):
    return next(
        s["html"]
        for s in case(example["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example, formula=None):
    _, f, i, b = read(example["context"])
    return analyze(formula or f, i, b, parent(example))


def plan(example, context=None):
    return get_handler(get_group_profile(example["group"]).content_rule_key).plan(
        PlanInput(context or example["context"], parent_solution_html=parent(example))
    )


def original_value(key, x):
    sn, cs = math.sin(x), math.cos(x)
    if key == "532656":
        return (
            None
            if sn <= 1e-10
            else (4 * math.sin(3 * math.pi / 2 + x) * (cs - 1) + 3) / math.sqrt(sn)
        )
    if key == "546982":
        if abs(math.cos(3 * x / 2)) < 1e-10:
            return None
        rad = 3 - math.tan(3 * x / 2) ** 2
        return None if rad < -1e-10 else sn * math.sqrt(max(rad, 0)) - cs - 2
    if key == "624602":
        rad = math.cos(2 * x) - math.sin(5 * x)
        return None if rad < -1e-10 else math.sqrt(max(rad, 0)) + 2 * cs
    if key == "635085":
        if abs(sn * cs) < 1e-10 or sn * cs < 0:
            return None
        return sn**3 * (1 + cs / sn) + cs**3 * (1 + sn / cs) - 2 * math.sqrt(sn * cs)
    if key == "635565":
        if sn <= 1e-10 or abs(x) > 5:
            return None
        log = math.log(sn, 4)
        return 2 * log * log - x * x + 21 - math.sqrt(25 - x * x) ** 2 - 7 * log
    if abs(cs) < 1e-10 or -2 * math.tan(x) <= 1e-10:
        return None
    return (4 * sn * sn + 12 * cs - 9) / math.sqrt(-2 * math.tan(x))


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_one_rule_with_exact_catalog_coordinates(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"], "14")


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_root_sets_follow_the_original_equation_and_domain(
    example,
):
    key = example["task"]
    a = analysis(example)
    full = (
        a.finite_roots
        if a.finite_roots is not None
        else select(a.series, (0, 2, True, False))[0]
    )
    assert full == tuple(map(sp.Rational, EXPECTED[key][0].split()))
    assert a.selected == tuple(map(sp.Rational, EXPECTED[key][1].split()))
    for q in (*full, *a.selected):
        assert sp.simplify(ORIGINAL[key].subs(X, q * sp.pi)) == 0
        assert original_value(key, float(q) * math.pi) is not None
    window = (
        a.finite_roots
        if a.finite_roots is not None
        else select(a.series, (-2, 2, True, True))[0]
    )
    for k in range(-48, 49):
        q = sp.Rational(k, 24)
        value = original_value(key, float(q) * math.pi)
        assert (q in window) == (value is not None and abs(value) < 1e-8)


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(example):
    original = deepcopy(example["context"])
    p = plan(example)
    assert example["context"] == original
    changed = deepcopy(original)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>Не использовать.</p>"
    other = plan(example, changed)
    assert (other.answer, other.solution_html) == (p.answer, p.solution_html)
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith(("asset:", "section:condition"))
        item = next(
            s
            for s in changed["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        )
        item.update(t["value"])
    assert plan(example, changed).transformations == ()
    assert not original["normalized_content"]["assets"]
    assert not BeautifulSoup(p.solution_html, "html.parser").find("img")
    assert (
        get_handler(get_group_profile(example["group"]).content_rule_key).diagram_specs(
            original
        )
        == ()
    )


def test_all_three_half_tangent_methods_stay_after_selection_in_their_original_sections():
    example = case("546982")
    a = analysis(example)
    p = plan(example)
    assert a.radical_notes == (False, "half_tangent")
    expected = -(C + 1) * (2 * C + 1) ** 2 * (5 * C * C - 6 * C + 2)
    assert sp.rem(a.radical_equation.squared - expected, CIRCLE, S) == 0
    assert all(
        sp.simplify(pole.subs(C, v)) == 0
        for v in (-1, sp.Rational(1, 2))
        for pole in a.poles
    )
    assert a.residues == (sp.Rational(2, 3),)
    soup = BeautifulSoup(p.solution_html, "html.parser")
    parts = soup.find("ol").find_all("li", recursive=False)
    assert "тройного" in parts[0].get_text() and "половинного" in parts[0].get_text()
    alternative = soup.select_one(
        'section[data-solution-title="Альтернативное решение."]'
    )
    assert alternative is not None and alternative.find_parent("ol") is None
    assert (
        "неположительна" in alternative.get_text()
        and "неотрицательна" in alternative.get_text()
    )
    tex = [
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    ]
    assert r"20t^{5}+16t^{4}-15t^{3}-9t^{2}+4t+2=0" in tex
    assert "Приведём идею другого решения" in p.solution_html
    assert (
        p.solution_html.index("</ol>")
        < p.solution_html.index("Приведём идею")
        < p.solution_html.index('data-solution-title="Альтернативное')
    )


def test_missing_third_method_and_unknown_extra_method_are_not_silently_dropped():
    example = case("546982")
    _, f, i, b = read(example["context"])
    soup = BeautifulSoup(parent(example), "html.parser")
    soup.select_one(
        'section[data-solution-title="Альтернативное решение."]'
    ).decompose()
    with pytest.raises(UnsupportedCondition, match="both the rational-cosine"):
        analyze(f, i, b, str(soup))
    with pytest.raises(UnsupportedCondition, match="exactly one reviewed"):
        analyze(f, i, b, parent(example) + "<p>Приведём ещё одно решение.</p>")


def test_amgm_and_positive_tangent_alternative_keep_their_place_and_exclude_third_quadrant():
    example = case("635085")
    a = analysis(example)
    p = plan(example)
    assert a.radical_notes == (True, "amgm") and set(a.poles) == {S, C}
    assert sp.Rational(5, 4) not in a.residues
    assert sp.simplify(ORIGINAL["635085"].subs(X, 5 * sp.pi / 4)) != 0
    soup = BeautifulSoup(p.solution_html, "html.parser")
    parts = soup.find("ol").find_all("li", recursive=False)
    assert "полный квадрат" in parts[0].get_text()
    assert "Приведём другое решение" in parts[1].get_text()
    assert "положительный косинус" in parts[1].get_text()
    assert not soup.find("section")


@pytest.mark.parametrize("multiple", [3, 7])
def test_odd_angle_extremum_updates_old_index_parity_and_keeps_zero_radical(multiple):
    example = case("624602")
    formula = rf"\sqrt{{\cos2x-\sin{multiple}x}}=-2\cos x"
    a = analysis(example, formula)
    assert a.residues == (sp.Rational(1, 2),) and a.selected == (sp.Rational(5, 2),)
    assert a.radical_equation.multiple == multiple
    _, _, html = render(a, "")
    assert "Подходят чётные" in html and r"k=2n+0" in html
    assert "Граница области определения сохраняется" in html


def test_denominator_radical_ratio_retains_the_original_cosine_pole_and_integer_n():
    a = analysis(case("637853"))
    p = plan(case("637853"))
    assert a.radical_ratio[0] == -2 * S / C and a.poles == (C,) and a.strict_domain
    assert a.series == ((-sp.Rational(1, 3), sp.Integer(2)),)
    assert "квадрат положителен" in p.solution_html
    tex = " ".join(
        n["data-inline-latex"]
        for n in BeautifulSoup(p.solution_html, "html.parser").select(
            "[data-inline-latex]"
        )
    )
    assert " k" not in tex and " n" in tex


def test_progression_length_only_bounds_the_number_of_roots_then_checks_actual_indices():
    example = case("532656")
    a = analysis(example)
    p = plan(example)
    assert a.selection_method == "progressions" and a.strict_domain
    assert "не превосходит 2" in p.solution_html
    assert a.selected == (sp.Rational(8, 3),)


def test_bounded_logarithm_full_answer_is_finite_and_wider_selection_cannot_leak_roots():
    example = case("635565")
    a = analysis(example)
    assert a.bounded_log.bounds == (-5, 5)
    assert a.finite_roots == (-sp.Rational(7, 6), sp.Rational(1, 6), sp.Rational(5, 6))
    _, f, _, _ = read(example["context"])
    wide = analyze(f, r"[-10;10]", (-10, 10, True, True), parent(example))
    assert wide.selected == a.finite_roots and wide.finite_roots == a.finite_roots
    answer, _, html = render(wide, "")
    assert r"\in\mathbb Z" not in answer.split("; б)")[0]
    assert "полное множество корней" in html and "Из полного конечного" in html
    changed = analysis(example, f.replace("25", "4").replace("+21", "+0"))
    assert (
        changed.bounded_log.bounds == (-2, 2)
        and changed.finite_roots == (sp.Rational(1, 6),)
        and changed.selected == ()
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"\sin x\sqrt{4-\tg^{2}\frac{3x}{2}}-\cos x=2",
        r"\sin x\sqrt{3-\tg\frac{3x}{2}}-\cos x=2",
        r"\frac{\sin x}{\cos x}\sqrt{3-\tg^{2}\frac{3x}{2}}-\cos x=2",
    ],
)
def test_unreviewed_half_angle_radicals_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_radical(formula, "half_tangent")


def test_bounded_logarithm_rejects_an_unsquared_radical_and_hidden_variable_pole():
    _, f, _, _ = read(case("635565")["context"])
    with pytest.raises(UnsupportedCondition):
        compile_log(f.replace(r"(\sqrt{25-x^{2}})^{2}", r"\sqrt{25-x^{2}}"))
    with pytest.raises(UnsupportedCondition):
        compile_log(f.replace("-x^{2}+21", r"-x^{2}+21+x^{-1}-x^{-1}"))


@pytest.mark.parametrize(
    "bounds,expected",
    [
        ((-16 * sp.pi / 3, 2, False, True), (-sp.Rational(10, 3), -sp.Rational(4, 3))),
        (
            (-17, -4 * sp.pi / 3, True, False),
            (-sp.Rational(16, 3), -sp.Rational(10, 3)),
        ),
    ],
)
def test_numeric_index_certificates_handle_an_open_endpoint_that_is_a_root(
    bounds, expected
):
    example = case("546982")
    _, f, _, _ = read(example["context"])
    a = analyze(f, r"\text{изменённый промежуток}", bounds, parent(example))
    assert a.selected == expected
    _, _, html = render(a, "")
    assert r"3<\pi<\frac{22}{7}" in [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
