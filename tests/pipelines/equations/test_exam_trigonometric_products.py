"""Product identities, original ratio domains and fractional-angle progressions."""

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
    S,
    analyze,
    compile_equation,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import CIRCLES, read
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_products.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "560137": "7/6 4/3 3/2",
    "561175": "-11/6 -7/6",
    "561227": "-10/3 -8/3",
    "561740": "-7/6 -5/6",
    "562229": "-14/3 -9/2 -7/2",
    "562233": "4 13/3 5",
    "562936": "10/3",
    "562981": "10/3",
    "564702": "1 5/4 3/2 2 9/4 5/2 3",
}
RESIDUES = {
    "560137": "0 1/6 1/2 2/3 5/6 7/6 4/3 3/2 11/6",
    "561175": "1/6 5/6",
    "561227": "2/3 4/3",
    "561740": "1/2 5/6 7/6 3/2",
    "562229": "1/2 2/3 4/3 3/2",
    "562233": "0 1/3 1 5/3",
    "562936": "2/3 2 10/3",
    "562981": "2/3 2 10/3",
    "564702": "0 1/4 1/2 1 5/4 3/2",
}
ORIGINAL = {
    "560137": sp.sin(7 * X / 2) * sp.sin(X / 2)
    + sp.cos(7 * X / 2) * sp.cos(X / 2)
    - sp.cos(3 * X) ** 2,
    "561175": sp.tan(X) * (sp.cot(X) - sp.cos(X)) - 2 * sp.sin(X) ** 2,
    "561227": 2 * sp.cos(X) ** 2 - sp.cot(X) * (sp.sin(X) + sp.tan(X)),
    "561740": (sp.cos(X) - sp.sin(X)) ** 2
    + sp.sqrt(2) * sp.sin(3 * sp.pi / 4 - 2 * X)
    + sp.sqrt(3) * sp.cos(X),
    "562229": sp.cos(X)
    + 2 * sp.cos(2 * X - sp.pi / 3)
    - sp.sqrt(3) * sp.sin(2 * X)
    + 1,
    "562233": sp.sin(X) + sp.sqrt(2) * sp.sin(sp.pi / 4 - 2 * X) - sp.cos(2 * X),
    "562936": sp.sin(X / 4) ** 2 - sp.cos(X / 4) ** 2 - sp.sin(5 * sp.pi / 2 - X),
    "562981": sp.cos(X / 4) ** 2 - sp.sin(X / 4) ** 2 - sp.sin(3 * sp.pi / 2 - X),
    "564702": sp.cos(X / 2) * sp.sin(3 * X / 2)
    + sp.sin(X / 2) * sp.cos(3 * X / 2)
    - 4 * sp.sin(sp.pi + X) ** 2 * sp.cos(sp.pi - X) ** 2,
}
FACTORED = {
    "560137": sp.cos(3 * X) * (1 - sp.cos(3 * X)),
    "561175": -(sp.sin(X) + 1) * (2 * sp.sin(X) - 1),
    "561227": (sp.cos(X) - 1) * (2 * sp.cos(X) + 1),
    "561740": sp.cos(X) * (2 * sp.cos(X) + sp.sqrt(3)),
    "562229": sp.cos(X) * (2 * sp.cos(X) + 1),
    "562233": sp.sin(X) * (1 - 2 * sp.cos(X)),
    "562936": -(2 * sp.cos(X / 2) - 1) * (sp.cos(X / 2) + 1),
    "562981": (2 * sp.cos(X / 2) - 1) * (sp.cos(X / 2) + 1),
    "564702": sp.sin(2 * X) * (1 - sp.sin(2 * X)),
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
def test_independent_factorizations_and_complete_root_sets(c):
    task = c["task"]
    assert sp.trigsimp(sp.expand(sp.expand_trig(ORIGINAL[task] - FACTORED[task]))) == 0
    a = analysis(c)
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    period = 4 if task in ("562936", "562981") else 2
    roots = select(a.series, (0, period, True, False))[0]
    assert roots == tuple(map(sp.Rational, RESIDUES[task].split()))
    for q in roots:
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
        if task in ("561175", "561227"):
            assert sp.sin(q * sp.pi) != 0 and sp.cos(q * sp.pi) != 0
    assert "UNUSED" not in plan(c).solution_html


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


@pytest.mark.parametrize("task,value", [("561175", -1), ("561227", 1)])
def test_both_ratio_poles_are_recorded_before_cancellation(task, value):
    c = case(task)
    a = analysis(c)
    assert set(a.poles) == {S, C}
    assert a.branches[0].excluded == (value,)
    html = plan(c).solution_html
    assert html.index(r"(\sin x)\ne0") < html.index("В этой области")
    assert html.index(r"(\cos x)\ne0") < html.index("В этой области")
    assert "нарушает исходную область определения" in html
    assert "от −1 до 1" not in html


def test_crossed_domain_point_is_preserved_as_an_excluded_point():
    c = case("561175")
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    assert entry["crossed_domain"] == ["3/2"]
    assert next(m for m in entry["green_markers"] if m["angle"] == "3/2")["excluded"]
    assert "3/2" not in entry["residues"]
    assert sp.cos(3 * sp.pi / 2) == 0


@pytest.mark.parametrize(
    "task,lower,upper", [("562936", "11/8", "5/2"), ("562981", "7/4", "23/8")]
)
def test_parent_single_progression_and_inequalities_need_no_invented_figure(
    task, lower, upper
):
    c = case(task)
    a = analysis(c)
    assert a.merged and a.series == ((sp.Rational(2, 3), sp.Rational(4, 3)),)
    assert a.selection_method == "inequalities"
    assert c["context"]["normalized_content"]["assets"] == []
    html = plan(c).solution_html
    assert "одну арифметическую прогрессию" in html and "<img" not in html
    lo, hi = a.bounds[:2]
    assert (lo - sp.Rational(2, 3)) / sp.Rational(4, 3) == sp.Rational(lower)
    assert (hi - sp.Rational(2, 3)) / sp.Rational(4, 3) == sp.Rational(upper)


@pytest.mark.parametrize(
    "formula",
    [
        r"\tg 2x(\ctg x-\cos x)=0",
        r"\tg x+\sin x=0",
        r"\tg x(\ctg x-\cos \beta)=0",
        r"\ctg(x+\frac{\pi}{2})\sin x=0",
    ],
)
def test_unreviewed_ratio_products_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_equation(formula)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_source_markers_describe_computed_roots_and_crossed_domain_point(c):
    assets = c["context"]["normalized_content"]["assets"]
    if not assets:
        return
    entry = CIRCLES[assets[0]["asset_id"]]
    expected = set(map(sp.Rational, entry["residues"]))
    visible = {
        sp.Rational(m["angle"]) for m in entry["green_markers"] if not m.get("excluded")
    }
    assert visible == expected
    a = analysis(c)
    if entry.get("point_scope") == "selected":
        assert expected == {q % 2 for q in a.selected}
    else:
        assert expected == set(select(a.series, (0, 2, True, False))[0])
    html = plan(c).solution_html
    assert assets[0]["asset_id"] in html
    assert not get_handler(
        get_group_profile(c["group"]).content_rule_key
    ).diagram_specs(c["context"])


def test_explicit_product_in_parent_keeps_factoring_instead_of_discriminant():
    c = case("562229")
    assert analysis(c).factorization
    html = plan(c).solution_html
    assert "Вынесем общий множитель" in html and "D=" not in html
