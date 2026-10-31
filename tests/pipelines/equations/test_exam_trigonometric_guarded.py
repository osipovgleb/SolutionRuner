"""Strict radical domains, guarded division, symmetric modules and original poles."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    C,
    S,
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_absolute import (
    compile_absolute,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import CIRCLES, read
from solution_runner.pipelines.equations.exam_trigonometric_division import (
    proof as division_proof,
)
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
)
from solution_runner.pipelines.equations.exam_trigonometric_radical_quotient import (
    compile_quotient,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_guarded.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "642952": "-10/3 -3 -2",
    "647164": "5/8 3/4 7/8",
    "652637": "-1/4 1/6 1/4",
    "656542": "-3/4 -7/12 -1/4 -1/12 1/4 5/12 3/4 11/12",
    "659588": "3/4 1 9/8 5/4 3/2",
    "669110": "1/6 5/6",
}
RESIDUES = {
    "642952": "0 1/3 2/3 1",
    "647164": "1/8 1/4 3/8 5/8 3/4 7/8 9/8 5/4 11/8 13/8 7/4 15/8",
    "652637": "1/6 1/4 7/4",
    "656542": "1/4 5/12 3/4 11/12 5/4 17/12 7/4 23/12",
    "659588": "0 1/8 1/4 1/2 5/8 3/4 1 9/8 5/4 3/2 13/8 7/4",
    "669110": "1/6 5/6",
}
ORIGINAL = {
    "642952": 2 * sp.sin(X) ** 3 + sp.sqrt(3) * sp.cos(X) ** 2 - sp.sqrt(3),
    "647164": 2 * sp.cos(2 * X) ** 2
    - 4 * sp.cos(2 * X) ** 2 * sp.sin(X) ** 2
    + sp.sin(2 * X - sp.pi / 2),
    "652637": (2 * sp.sin(X) ** 2 + 2 * sp.sin(X) * sp.cos(2 * X) - 1)
    / sp.sqrt(sp.cos(X)),
    "656542": sp.Abs(sp.cot(2 * X) ** 2 + 8 * sp.sqrt(-sp.cot(2 * X)) - 3)
    - sp.Abs(sp.cot(2 * X) ** 2 - 8 * sp.sqrt(-sp.cot(2 * X)) - 3),
    "659588": sp.cos(sp.pi / 2 - 9 * X / 2) * sp.cos(X / 2)
    + sp.sin(sp.pi + X / 2) * sp.cos(9 * X / 2)
    - sp.sin(4 * X) ** 2,
    "669110": (3 * sp.sin(X) - 4) / (sp.sin(X) - 1)
    + 1 / (sp.sin(X) ** 2 - sp.sin(X))
    - 1,
}
FACTORED = {
    "642952": sp.sin(X) ** 2 * (2 * sp.sin(X) - sp.sqrt(3)),
    "647164": sp.cos(2 * X) * (2 * sp.cos(2 * X) ** 2 - 1),
    "652637": -(2 * sp.sin(X) ** 2 - 1) * (2 * sp.sin(X) - 1) / sp.sqrt(sp.cos(X)),
    "659588": sp.sin(4 * X) * (1 - sp.sin(4 * X)),
    "669110": (2 * sp.sin(X) - 1) / sp.sin(X),
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for s in case(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_existing_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 4, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_equations_and_complete_domain_filtered_roots_are_independent(c):
    task = c["task"]
    if task in FACTORED:
        difference = sp.trigsimp(
            sp.expand(sp.expand_trig(ORIGINAL[task] - FACTORED[task]))
        )
        if difference != 0:
            numerator = sp.fraction(sp.together(difference))[0]
            polynomial = numerator.xreplace({sp.sin(X): S, sp.cos(X): C})
            difference = sp.rem(polynomial, S * S + C * C - 1, S)
        assert difference == 0
    a = analysis(c)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == tuple(map(sp.Rational, RESIDUES[task].split()))
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    for q in roots:
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
        if task == "652637":
            assert sp.cos(q * sp.pi) > 0
        if task == "656542":
            assert sp.sin(2 * q * sp.pi) != 0 and -sp.cot(2 * q * sp.pi) >= 0
        if task == "669110":
            assert sp.sin(q * sp.pi) not in (0, 1)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    ctx = deepcopy(c["context"])
    before = deepcopy(ctx)
    p = plan(c, ctx)
    assert ctx == before
    assert p.condition_html == next(
        s["html"]
        for s in ctx["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>UNUSED9999</p>"
    assert plan(c, ctx) == p
    for t in p.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert plan(c, ctx).transformations == ()
    assert not get_handler(
        get_group_profile(c["group"]).content_rule_key
    ).diagram_specs(c["context"])


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_circles_mark_every_domain_valid_root_and_no_figures_are_invented(c):
    assets = c["context"]["normalized_content"]["assets"]
    if not assets:
        assert "<img" not in plan(c).solution_html
        return
    a = analysis(c)
    entry = CIRCLES[assets[0]["asset_id"]]
    visible = {sp.Rational(m["angle"]) for m in entry["green_markers"]}
    assert (
        visible
        == set(select(a.series, (0, 2, True, False))[0])
        == set(map(sp.Rational, entry["residues"]))
    )
    assert tuple(map(sp.Rational, entry["labels"])) == a.selected
    assert assets[0]["asset_id"] in plan(c).solution_html


def test_zero_cosine_branch_is_kept_before_guarded_division_and_open_selection():
    c = case("647164")
    a = analysis(c)
    assert a.scale == 2 and a.division and a.doubled
    assert a.bounds[2:] == (False, False)
    assert set(a.branches[0].values) == {0, -sp.sqrt(2) / 2, sp.sqrt(2) / 2}
    assert sp.Rational(1, 4) in select(a.series, (0, 2, True, False))[0]
    html = plan(c).solution_html
    assert html.index("Сначала сохраним") < html.index(
        "только в этой ветви можно разделить"
    )
    assert r"(\cos 2 x)\ne0" in html
    assert r"\sin^4" not in html and "D=" not in html
    assert a.series[0] == (sp.Rational(1, 4), sp.Rational(1, 2))
    bad = replace(a.branches[0], polynomial=C * C + 1)
    with pytest.raises(UnsupportedCondition):
        division_proof(bad, "2x", 2)


def test_radical_denominator_requires_positive_radicand_and_removes_left_half_circle():
    c = case("652637")
    a = analysis(c)
    assert a.strict_domain and a.domain == C
    assert not {sp.Rational(3, 4), sp.Rational(5, 4), sp.Rational(5, 6)} & set(
        a.residues
    )
    html = plan(c).solution_html
    assert html.index(r"(\cos x)&gt;0") < html.index("числителя в нуль")
    assert "строгому условию на знаменатель" in html
    _, _, interval, bounds = read(c["context"])
    empty = analyze(r"\frac{\cos x}{\sqrt{\cos x}}=0", interval, bounds, parent(c))
    assert empty.residues == () and empty.series == () and empty.selected == ()


def test_absolute_value_transformation_is_equivalent_on_the_nonnegative_domain():
    c = case("656542")
    a = analysis(c)
    assert a.scale == 2 and a.absolute == (1, -3, 8) and a.poles == (S,)
    assert set(a.branches[0].values) == {0, -sp.sqrt(3)}
    assert a.series == (
        (sp.Rational(1, 4), sp.Rational(1, 2)),
        (sp.Rational(-1, 12), sp.Rational(1, 2)),
    )
    t = sp.Symbol("t", nonnegative=True)
    left, right = t * t + 8 * sp.sqrt(t) - 3, t * t - 8 * sp.sqrt(t) - 3
    assert sp.expand(left**2 - right**2 - 32 * sp.sqrt(t) * (t * t - 3)) == 0
    for value in (0, 1, sp.sqrt(3), 2):
        actual = sp.simplify((sp.Abs(left) - sp.Abs(right)).subs(t, value))
        assert (actual == 0) == (value in (0, sp.sqrt(3)))
    html = plan(c).solution_html
    assert (
        html.index(r"\sin(2 x)\ne0")
        < html.index(r"t\ge0")
        < html.index("совпадают или противоположны")
        < html.index("Отрицательное значение исключаем")
    )


def test_common_denominator_keeps_the_cancelled_pole_and_the_rejected_parameter():
    c = case("669110")
    a = analysis(c)
    assert a.substitution == "t" and a.fraction is not None and a.reciprocal is None
    assert set(a.poles) == {S - 1, S * S - S}
    assert a.branches[0].excluded == (1,)
    assert sp.expand(a.raw - (2 * S * S - 3 * S + 1)) == 0
    html = plan(c).solution_html
    assert (
        html.index("ограничения исходных дробей")
        < html.index("общему знаменателю без потери")
        < html.index("Это значение нарушает область определения")
    )
    assert "от −1 до 1" not in html


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{\sin x}{\sqrt{\cos x+1}}=0",
        r"\frac{\sin x}{\sqrt{\cos x+\sin x}}=0",
        r"\frac{\sin x}{\sqrt{\cos x}}=1",
        r"\frac{\sin x}{\sqrt{\cos x}}+1=0",
    ],
)
def test_unreviewed_radical_quotients_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_quotient(formula)


@pytest.mark.parametrize(
    "formula",
    [
        r"|\ctg^2 2x+8\sqrt{-\ctg 2x}-3|=0",
        r"|\ctg^2 2x+8\sqrt{-\ctg 2x}-3|=|\ctg^2 2x-8\sqrt{\ctg 2x}-3|",
        r"|\ctg^3 2x+8\sqrt{-\ctg 2x}-3|=|\ctg^3 2x-8\sqrt{-\ctg 2x}-3|",
        r"|\ctg^2 2x+8\sqrt{-\ctg 2x}+r-3|=|\ctg^2 2x-8\sqrt{-\ctg 2x}-r-3|",
        r"|\ctg^2(2\alpha)+8\sqrt{-\ctg 2x}-3|=|\ctg^2(2\alpha)-8\sqrt{-\ctg 2x}-3|",
    ],
)
def test_unreviewed_absolute_equations_and_placeholder_injection_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_absolute(formula)


@pytest.mark.parametrize(
    "formula", [r"\frac{1}{\sin x+\cos x}=0", r"\frac{1}{\sin^3x-1}=0"]
)
def test_unreviewed_function_denominators_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, S, 1)


def test_numeric_radical_coefficient_keeps_the_existing_polynomial_method():
    c = case("642952")
    _, _, interval, bounds = read(c["context"])
    result = analyze(r"\frac{\sin x}{\sqrt{2}}=0", interval, bounds, parent(c))
    assert not result.strict_domain and result.domain is None
    assert result.series == ((0, 1),)
    assert result.selected == (-3, -2)
