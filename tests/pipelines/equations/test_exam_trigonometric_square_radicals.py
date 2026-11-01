"""Perfect squares preserve absolute values, sine range and parent methods."""

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
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_compile import S
from solution_runner.pipelines.equations.exam_trigonometric_square_radicals import (
    compile_squares,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_square_radicals.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
ORIGINAL = {
    "654698": sp.sqrt((sp.sin(3 * X) - 2) ** 2)
    - sp.sqrt(9 * sp.sin(3 * X) ** 2 - 24 * sp.sin(3 * X) + 16)
    + 4,
    "672191": sp.sqrt(
        12 * sp.sin(X) - sp.Rational(9, 2) * sp.cos(2 * X) + sp.Rational(17, 2)
    )
    - sp.Rational(9, 8)
    - 4 * sp.sin(X)
    - sp.cos(X) ** 2 / 2,
}
EXPECTED = {"654698": ("1/2 7/6 11/6", "-1/6 1/2"), "672191": ("1/6 5/6", "1/6 5/6")}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(example):
    return next(
        s["html"]
        for s in example["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example):
    _, f, i, b = read(example["context"])
    return analyze(f, i, b, parent(example))


def plan(example, context=None):
    return get_handler(get_group_profile(example["group"]).content_rule_key).plan(
        PlanInput(context or example["context"], parent_solution_html=parent(example))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_the_same_runner_and_exact_catalog_coordinates(g):
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
def test_complete_and_selected_roots_satisfy_the_original_equation(example):
    key = example["task"]
    a = analysis(example)
    full = select(a.series, (0, 2, True, False))[0]
    assert full == tuple(map(sp.Rational, EXPECTED[key][0].split()))
    assert a.selected == tuple(map(sp.Rational, EXPECTED[key][1].split()))
    for q in (*full, *a.selected):
        assert sp.simplify(ORIGINAL[key].subs(X, q * sp.pi)) == 0
    value = sp.lambdify(X, ORIGINAL[key], modules="math")
    window = select(a.series, (-2, 2, True, True))[0]
    for k in range(-48, 49):
        q = sp.Rational(k, 24)
        assert (q in window) == (abs(value(float(q) * math.pi)) < 1e-8)


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
    for transformation in p.transformations:
        key = transformation["transformation_target_id"]
        assert not key.startswith(("asset:", "section:condition"))
        section = next(
            s
            for s in changed["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        )
        section.update(transformation["value"])
    assert plan(example, changed).transformations == ()
    assert not original["normalized_content"]["assets"]
    assert not BeautifulSoup(p.solution_html, "html.parser").find("img")
    assert (
        get_handler(get_group_profile(example["group"]).content_rule_key).diagram_specs(
            original
        )
        == ()
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def test_both_fixed_sign_squares_keep_the_parent_angle_and_series_offset():
    e = case("654698")
    a = analysis(e)
    p = plan(e)
    assert a.scale == 3 and a.square_radicals.signs == (-1, -1)
    assert a.square_radicals.linears == (S - 2, 3 * S - 4)
    assert a.series == ((sp.Rational(-1, 6), sp.Rational(2, 3)),)
    assert a.selection_method == "inequalities"
    text = " ".join(formulas(p.solution_html)[1:])
    assert r"\sin3x" in "".join(text.split())
    assert r"\left|" in text and "нумерацию" in p.solution_html
    assert "На всём диапазоне" in p.solution_html


def test_crossing_absolute_value_checks_both_quadratics_and_negative_right_side():
    e = case("672191")
    a = analysis(e)
    p = plan(e)
    d = a.square_radicals
    assert d.signs == (0,)
    assert d.candidates == (
        (sp.Rational(1, 2), sp.Rational(3, 2)),
        (sp.Rational(-1, 2), sp.Rational(29, 2)),
    )
    assert d.accepted == (sp.Rational(1, 2),)
    assert a.selection_method == "progressions"
    assert "Правая часть отрицательна" in p.solution_html
    fs = formulas(p.solution_html)
    assert any("29" in f for f in fs)
    assert any(r"\notin[-1;1]" in f for f in fs)
    assert any(r"\ge0" in f for f in fs)
    assert "не превосходит 1" in p.solution_html


def test_same_square_certificate_handles_a_different_base_angle_and_coefficients():
    c = compile_squares(r"\sqrt{(\sin 2x-3)^2}-\sqrt{(2\sin 2x-5)^2}=-3")
    assert c.scale == 2 and c.raw == S + 1
    assert c.square_radicals.signs == (-1, -1)
    c = compile_squares(r"\sqrt{(2\sin 3x+1)^2}=1")
    assert c.scale == 3 and sp.expand(c.raw - S * (S + 1)) == 0
    assert set(c.square_radicals.accepted) == {0, -1}


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{\sin^2 x+1}=1",
        r"\sqrt{(\sin x+1/2)^2}-\sqrt{(2\sin x-1/2)^2}=1",
        r"\sqrt{(\tg x-2)^2}=1",
        r"\sqrt{(\sin x-2)^2}/\cos x=1",
        r"\sqrt{(\sin x-2)^2}+r=1",
        r"\sqrt{(\sin x-2)^2}*\sqrt{(\sin x-3)^2}=1",
    ],
)
def test_unreviewed_radicals_poles_and_undeclared_symbols_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_squares(formula)
