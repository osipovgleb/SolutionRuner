"""Angle translations, reciprocal cosine identities and the parent's base angle."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    C,
    T,
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import CIRCLES, read
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
)
from solution_runner.pipelines.equations.exam_trigonometric_translation import (
    parent_method,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_translations.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "564902": "-4/3 -2/3",
    "621225": "-4/3 0",
    "624080": "9/4",
    "624114": "10/3",
    "628241": "7/4 7/3 11/4",
    "628272": "9/4 8/3 13/4",
    "628914": "-1/4 -1/6 1/6 1/4 3/4 5/6",
    "630034": "9/2 14/3 16/3 11/2",
}
RESIDUES = {
    "564902": "2/3 4/3",
    "621225": "0 2/3",
    "624080": "1/4 3/4",
    "624114": "4/3 5/3",
    "628241": "1/3 3/4 4/3 7/4",
    "628272": "1/4 2/3 5/4 5/3",
    "628914": "1/6 1/4 3/4 5/6 7/6 5/4 7/4 11/6",
    "630034": "1/2 2/3 4/3 3/2",
}
ORIGINAL = {
    "564902": 7 * sp.sin(2 * X - 5 * sp.pi / 2) + 9 * sp.cos(X) + 1,
    "621225": sp.cos(2 * X + sp.pi / 3) + 4 * sp.sin(X + sp.pi / 6) - sp.Rational(5, 2),
    "624080": 4 * sp.cos(X) ** 2 - 1 + sp.sqrt(2) * sp.cos(sp.pi / 2 + X),
    "624114": 2 * sp.cos(X) ** 2 + 1 - sp.sqrt(3) * sp.cos(7 * sp.pi / 2 - X),
    "628241": 1 / sp.cos(X) ** 2
    + sp.tan(X)
    + sp.sqrt(3) * sp.tan(sp.pi - X)
    - sp.sqrt(3)
    - 1,
    "628272": 1 / sp.cos(X) ** 2
    + sp.sqrt(3) * sp.tan(X)
    + sp.tan(2 * sp.pi - X)
    - sp.sqrt(3)
    - 1,
    "628914": sp.sin(2 * X) ** 2 - sp.cos(2 * X) - 4 * sp.sin(X) ** 4,
    "630034": sp.cos(X)
    + 2 * sp.sin(2 * X + sp.pi / 6)
    + 1
    - sp.sqrt(3) * sp.sin(2 * X),
}
FACTORED = {
    "564902": -14 * sp.cos(X) ** 2 + 9 * sp.cos(X) + 8,
    "621225": -2
    * (sp.sin(X + sp.pi / 6) - sp.Rational(1, 2))
    * (sp.sin(X + sp.pi / 6) - sp.Rational(3, 2)),
    "624080": -(sp.sqrt(2) * sp.sin(X) - 1) * (2 * sp.sqrt(2) * sp.sin(X) + 3),
    "624114": -(2 * sp.sin(X) + sp.sqrt(3)) * (sp.sin(X) - sp.sqrt(3)),
    "628241": (sp.tan(X) + 1) * (sp.tan(X) - sp.sqrt(3)),
    "628272": (sp.tan(X) - 1) * (sp.tan(X) + sp.sqrt(3)),
    "628914": sp.cos(2 * X) * (1 - 2 * sp.cos(2 * X)),
    "630034": sp.cos(X) * (2 * sp.cos(X) + 1),
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
def test_original_equations_and_complete_root_sets_are_independently_expected(c):
    task = c["task"]
    assert sp.trigsimp(sp.expand(sp.expand_trig(ORIGINAL[task] - FACTORED[task]))) == 0
    a = analysis(c)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == tuple(map(sp.Rational, RESIDUES[task].split()))
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    for q in roots:
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
        if a.preferred == T:
            assert sp.cos(q * sp.pi) != 0


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
def test_circle_scope_and_labels_match_actual_x_after_any_angle_substitution(c):
    a = analysis(c)
    identifier = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[identifier]
    visible = {sp.Rational(m["angle"]) for m in entry["green_markers"]}
    expected = (
        {q % 2 for q in a.selected}
        if entry.get("point_scope") == "selected"
        else set(select(a.series, (0, 2, True, False))[0])
    )
    assert visible == expected == set(map(sp.Rational, entry["residues"]))
    assert tuple(map(sp.Rational, entry["labels"])) == a.selected
    assert identifier in plan(c).solution_html


def test_angle_translation_is_reversed_before_the_circle_and_final_answer():
    c = case("621225")
    a = analysis(c)
    assert a.translation == sp.Rational(1, 6) and a.scale == 1
    assert a.residues == (sp.Rational(1, 6), sp.Rational(5, 6))
    assert set(a.branches[0].candidates) == {sp.Rational(1, 2), sp.Rational(3, 2)}
    assert a.branches[0].values == (sp.Rational(1, 2),)
    html = plan(c).solution_html
    assert (
        html.index("t=x+")
        < html.index(r"(\sin t)=\frac{3}{2}")
        < html.index("Сделаем обратную замену")
        < html.index("С помощью числовой окружности")
    )
    assert r"x=t-(\frac{\pi}{6})" in html
    assert r"\cos(2 t)" in html and r"(\sin x)" not in html
    assert "t=" not in plan(c).answer
    assert "от −1 до 1" in html


@pytest.mark.parametrize("task", ["628241", "628272"])
def test_reciprocal_cosine_keeps_its_pole_and_parent_factorization(task):
    c = case(task)
    a = analysis(c)
    assert a.preferred == T and a.poles == (C,) and a.factorization
    assert a.reciprocal is None
    assert all(b.variable == T for b in a.branches)
    html = plan(c).solution_html
    assert (
        html.index(r"\cos x\ne0")
        < html.index(r"\frac{1}{\cos^2x}")
        < html.index("Разложим квадратный трёхчлен")
    )
    assert "D=" not in html
    assert not any(sp.cos(q * sp.pi) == 0 for q in a.selected)


def test_parent_double_angle_is_not_replaced_by_a_different_single_angle_factorization():
    c = case("628914")
    a = analysis(c)
    assert a.preferred == C and a.scale == 2 and a.doubled
    assert len(a.branches) == 1 and a.branches[0].variable == C
    assert set(a.branches[0].values) == {0, sp.Rational(1, 2)}
    html = plan(c).solution_html
    assert "формулой понижения степени" in html
    assert r"(\cos 2 x)" in html and "делим углы и периоды каждой серии на 2" in html


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{1}{\cos x}+\tg x=0",
        r"\frac{1}{\sin^2x}+\tg x=0",
        r"\frac{1}{\cos^2(2x)}+\tg x=0",
        r"\frac{1}{\cos^2x}+\tg(x+\frac{\pi}{2})=0",
    ],
)
def test_unreviewed_reciprocal_tangent_equations_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, T, 1)


@pytest.mark.parametrize(
    "formula", [r"t=x^2", r"t=x+\frac{\pi}{7}", r"t=x+\frac{7\pi}{3}", r"t=x+\sin x"]
)
def test_unreviewed_angle_translations_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        parent_method('<span data-inline-latex="' + formula + '"></span>')


def test_conflicting_parent_angle_translations_fail_closed():
    with pytest.raises(UnsupportedCondition):
        parent_method(
            r'<span data-inline-latex="t=x+\frac{\pi}{6}"></span><span data-inline-latex="t=x+\frac{\pi}{3}"></span>'
        )
