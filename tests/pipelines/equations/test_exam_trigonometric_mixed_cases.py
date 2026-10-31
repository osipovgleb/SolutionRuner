"""Original domains, half angles and source parameters without stored answers or SVGs."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import read

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_mixed_cases.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
EXPECTED = {
    "634242": ("1/2 3/2", "13/2 15/2"),
    "634873": ("7/4", "-9/4 -1/4 7/4 15/4"),
    "635747": ("1/2", "1/2"),
    "636742": ("1/6 2/3 7/6 5/3", "13/6 8/3 19/6 11/3"),
    "639768": ("2/15 4/9 8/15 14/15 10/9 4/3 26/15 16/9", "2/15 4/9 8/15 14/15"),
    "645371": ("1/4 1/2 5/4 3/2", "-7/4 -3/2 -3/4 -1/2"),
}
ORIGINAL = {
    "634242": sp.cot(X) ** 4 - sp.cos(2 * X) ** 2 + 1,
    "634873": sp.sqrt(2) * sp.sin(2 * X) * sp.sin(X - sp.pi / 4)
    - 2 * sp.sin(3 * sp.pi / 4),
    "635747": s * (1 + c) - c * c - c - 1,
    "636742": (s**3 * sp.cos(3 * X) + c**3 * sp.sin(3 * X)) / sp.Abs(sp.sin(2 * X))
    - sp.Rational(3, 4),
    "639768": sp.cos(4 * X) + c / 2 - sp.sqrt(3) * s / 2,
    "645371": sp.sin(2 * X) - 2 * sp.sin(X - 3 * sp.pi / 2) ** 2,
}
POLES = {task: () for task in ORIGINAL}
POLES["634242"] = (s,)
POLES["636742"] = (sp.sin(2 * X),)


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(example):
    return next(
        s["html"]
        for s in case(example["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example):
    _, f, i, b = read(example["context"])
    return analyze(f, i, b, parent(example))


def plan(example, context=None):
    return get_handler(get_group_profile(example["group"]).content_rule_key).plan(
        PlanInput(context or example["context"], parent_solution_html=parent(example))
    )


def rational(text):
    return tuple(map(sp.Rational, text.split())) if isinstance(text, str) else text


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_the_existing_handler_and_actual_catalog_order(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 8, g["order"], "14")


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_root_sets_are_independently_expected(example):
    task = example["task"]
    a = analysis(example)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == rational(EXPECTED[task][0])
    assert a.selected == rational(EXPECTED[task][1])
    for q in (*roots, *a.selected):
        angle = q * sp.pi
        assert all(
            abs(complex(p.subs(X, angle).evalf(40))) > 1e-20 for p in POLES[task]
        )
        assert abs(complex(ORIGINAL[task].subs(X, angle).evalf(40))) < 1e-30
    # Check a dense independent lattice, including forbidden points and roots outside b).
    for k in range(360):
        q = sp.Rational(k, 180)
        angle = q * sp.pi
        allowed = all(
            abs(complex(p.subs(X, angle).evalf(30))) > 1e-18 for p in POLES[task]
        )
        zero = allowed and abs(complex(ORIGINAL[task].subs(X, angle).evalf(30))) < 1e-18
        assert (q in roots) == zero


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(example):
    original = deepcopy(example["context"])
    p = plan(example)
    assert (
        example["context"] == original and not original["normalized_content"]["assets"]
    )
    changed = deepcopy(original)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>не использовать</p>"
    assert (plan(example, changed).answer, plan(example, changed).solution_html) == (
        p.answer,
        p.solution_html,
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        next(
            s
            for s in changed["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        ).update(t["value"])
    assert plan(example, changed).transformations == ()
    handler = get_handler(get_group_profile(example["group"]).content_rule_key)
    assert handler.diagram_specs(original) == ()
    assert not BeautifulSoup(p.solution_html, "html.parser").find("img")


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def test_cotangent_fourth_power_keeps_zero_cosine_and_the_original_sine_pole():
    from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
    from solution_runner.pipelines.equations.exam_trigonometric_positive_factors import (
        positive,
    )

    a = analysis(case("634242"))
    p = plan(case("634242"))
    assert a.poles == (S,) and a.positive_factorization[-1] == "even"
    before, after, *_ = a.positive_factorization
    assert sp.rem(sp.expand(before - after), S * S + C * C - 1, S) == 0
    assert a.series == ((sp.Rational(1, 2), sp.S.One),)
    assert positive(S * S) is None and positive(S * S + C * C) == "even"
    assert positive(S + C + 1) is None and positive(S + C + 2) == "linear_corner"
    assert "неотрицательны" in p.solution_html and "одновременно" in p.solution_html


def test_positive_linear_factor_uses_the_parent_simultaneous_extrema_argument():
    a = analysis(case("635747"))
    p = plan(case("635747"))
    assert a.positive_factorization[-1] == "linear_corner"
    assert "сумма их квадратов равна 2 вместо 1" in p.solution_html
    assert r"\sqrt{2}" not in p.solution_html


def test_absolute_fraction_retains_both_strict_sign_cases_and_distinct_parameters():
    from solution_runner.pipelines.equations.exam_trigonometric_compile import S

    a = analysis(case("636742"))
    p = plan(case("636742"))
    assert a.absolute_fraction and a.strict_domain and a.poles == (S,)
    assert a.series == ((sp.Rational(1, 6), sp.S.One), (-sp.Rational(1, 3), sp.S.One))
    assert a.family_parameters == ("k", "n")
    roots = select(a.series, (0, 2, True, False))[0]
    assert sp.Rational(1, 3) not in roots and sp.Rational(5, 6) not in roots
    fs = formulas(p.solution_html)
    assert any(r"(\sin 2 x)>0" == f for f in fs) and any(
        r"(\sin 2 x)<0" == f for f in fs
    )
    assert any(r"x=\pi n - \frac{\pi}{3}" in f for f in fs)


def test_cosine_equality_proves_the_phase_and_preserves_source_family_order():
    a = analysis(case("639768"))
    p = plan(case("639768"))
    assert a.cosine_equality[:2] == (4, sp.Rational(1, 3))
    assert a.series == (
        (sp.Rational(4, 9), sp.Rational(2, 3)),
        (sp.Rational(2, 15), sp.Rational(2, 5)),
    )
    for branch in a.branches:
        for q in branch.residues:
            assert (
                sp.simplify(
                    sp.cos(sp.pi * (branch.angle_scale * q + branch.angle_shift))
                )
                == 0
            )
    assert "Косинусы противоположны" in p.solution_html and r"\pi\pm" in p.solution_html


def test_factorization_keeps_zero_cosine_before_dividing_in_the_other_branch():
    a = analysis(case("645371"))
    p = plan(case("645371"))
    assert a.series == ((sp.Rational(1, 2), sp.S.One), (sp.Rational(1, 4), sp.S.One))
    assert a.family_parameters == ("k", "n")
    fs = formulas(p.solution_html)
    assert r"k\in\{-2;-1\}" in fs and r"n\in\{-2;-1\}" in fs
    assert any(r"- \frac{9}{4}\le n \le- \frac{3}{4}" == f for f in fs)
    assert -sp.Rational(1, 2) in a.selected


def test_all_four_methods_follow_selection_inside_the_original_second_part():
    a = analysis(case("634873"))
    p = plan(case("634873"))
    assert a.four_methods and a.symmetric.sign == -1 and a.four_methods[2] == 0
    assert a.series == ((-sp.Rational(1, 4), sp.Integer(2)),)
    soup = BeautifulSoup(p.solution_html, "html.parser")
    parts = soup.select("li")
    first, second = map(str, parts[:2])
    assert "Примечание 1." not in first
    assert (
        second.index("Примечание 1.")
        < second.index("Приведём другое решение")
        < second.index("Приведём ещё одно решение")
    )
    fs = formulas(second)
    assert any("t^{3} - t^{2} + 2" in f for f in fs)
    assert "k=2m" in fs and "k=2m+1" in fs
    assert any(r"\sin\left(\frac{3 \pi}{2}+4\pi k\right)=-1" in f for f in fs)
    assert r"n=3 k - 1\in\mathbb Z" in fs
    assert "Эта система несовместна" in second and "вся серия посторонняя" in second


def test_four_method_certificates_recompute_signs_when_the_target_sign_changes():
    example = case("634873")
    _, f, i, b = read(example["context"])
    f = f.replace(r"=2\sin", r"=-2\sin")
    a = analyze(f, i, b, parent(example))
    assert a.four_methods[0] == -1 and a.four_methods[2] == 1
    assert select(a.series, (0, 2, True, False))[0] == (sp.Rational(3, 4),)
    assert a.selected == tuple(map(sp.Rational, ["-5/4", "3/4", "11/4", "19/4"]))


@pytest.mark.parametrize("changed", ("missing_last", "extra_method", "figure"))
def test_four_method_parent_cannot_silently_drop_or_invent_a_method(changed):
    from solution_runner.pipelines.equations.exam_trigonometric_four_methods import (
        split,
    )
    from solution_runner.pipelines.word_problems.common import UnsupportedCondition

    soup = BeautifulSoup(parent(case("634873")).replace("\xad", ""), "html.parser")
    if changed == "figure":
        soup.append(BeautifulSoup('<img src="/assets/unreviewed"/>', "html.parser"))
    elif changed == "extra_method":
        soup.append(BeautifulSoup("<p>Приведем еще одно решение.</p>", "html.parser"))
    else:
        marker = next(
            p for p in soup.find_all("p") if "Приведем еще одно решение" in p.get_text()
        )
        for node in list(marker.next_siblings):
            node.extract()
        marker.extract()
    with pytest.raises(UnsupportedCondition):
        split(str(soup))


@pytest.mark.parametrize(
    "formula",
    (
        r"\cos 4x+\frac{\cos x}{3}=\frac{\sqrt{3}}{2}\sin x",
        r"\cos (4x+\frac{\pi}{7})+\frac{\cos x}{2}=\frac{\sqrt{3}}{2}\sin x",
        r"\cos 4x+\frac{\cos x}{2}=\frac{\sqrt{3}}{2}\sin x+1",
    ),
)
def test_cosine_argument_equality_requires_its_exact_phase_and_amplitude(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_cosine_equality import (
        compile_equality,
    )
    from solution_runner.pipelines.word_problems.common import UnsupportedCondition

    with pytest.raises(UnsupportedCondition):
        compile_equality(formula)


@pytest.mark.parametrize(
    "formula",
    (
        r"\frac{\sin x}{|\sin 2x|}=\frac{3}{4}",
        r"\frac{\sin x\cos x}{|\sin 3x|}=\frac{3}{4}",
        r"\frac{\sin x\cos x}{|\sin x|\cos x}=\frac{3}{4}",
    ),
)
def test_absolute_fraction_requires_the_original_pole_and_the_numerator_identity(
    formula,
):
    from solution_runner.pipelines.equations.exam_trigonometric_absolute_fraction import (
        compile_fraction,
    )
    from solution_runner.pipelines.word_problems.common import UnsupportedCondition

    with pytest.raises(UnsupportedCondition):
        compile_fraction(formula)
