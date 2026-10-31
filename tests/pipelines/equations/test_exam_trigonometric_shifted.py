"""Keep a shifted quadratic function, full root sets and audited figure scope."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import C, S, analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import CIRCLES, read
from solution_runner.pipelines.equations.exam_trigonometric_shifted import parent_angle
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_shifted.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "671346": "17/4 19/4 11/2",
    "674433": "-7/3",
    "674804": "10/3",
    "679826": "31/12 47/12",
    "680000": "-8/3 -5/2 -3/2",
    "680774": "5/2 7/2 23/6",
    "681158": "-7/4 -5/4 -3/4",
    "681295": "-11/3 -10/3 -8/3",
    "681292": "5/6 7/6 7/4",
    "681587": "-5/4 -3/4 -1/3",
}
RESIDUES = {
    "671346": "1/4 3/4 3/2",
    "674433": "1/3 5/3",
    "674804": "2/3 4/3",
    "679826": "1/4 7/12 23/12",
    "680000": "1/2 2/3 4/3 3/2",
    "680774": "1/6 1/2 3/2 11/6",
    "681158": "1/4 3/4 5/4 7/4",
    "681295": "1/3 2/3 4/3 5/3",
    "681292": "1/4 5/6 7/6 7/4",
    "681587": "1/3 3/4 5/4 5/3",
}
ORIGINAL = {
    "671346": 1 / sp.sin(X) ** 2
    - (1 - sp.sqrt(2)) / sp.cos(sp.pi / 2 + X)
    - sp.sqrt(2),
    "674433": 8 * sp.sin(X) ** 2 - 6 * sp.cos(X) - 3,
    "674804": 6 * sp.sin(X) ** 2 + 5 * sp.cos(X) - 2,
    "679826": 2 * (sp.sqrt(2) * sp.sin(X) - sp.sin(X - sp.pi / 4)) ** 2
    - 3 * sp.cos(X - sp.pi / 4)
    + 1,
    "680000": 2 * sp.sin(X + sp.pi / 3)
    - 2 * sp.sqrt(3) * sp.sin(X) ** 2
    - sp.sin(X)
    + 2 * sp.sqrt(3),
    "680774": 2 * sp.sin(X - sp.pi / 3) - 2 * sp.sin(X) ** 2 - sp.sin(X) + 2,
    "681158": sp.cos(2 * X) + sp.Rational(1, 2) - sp.cos(X) ** 2,
    "681295": sp.cos(2 * X) + sp.Rational(3, 4) - sp.cos(X) ** 2,
    "681292": 2
    - 2 * sp.cos(sp.pi + 2 * X)
    - sp.sqrt(8) * sp.cos(X)
    - sp.sqrt(6)
    + sp.sqrt(12) * sp.cos(X),
    "681587": 2
    - 2 * sp.cos(sp.pi + 2 * X)
    - sp.sqrt(4) * sp.cos(X)
    - sp.sqrt(2)
    + sp.sqrt(8) * sp.cos(X),
}
FACTORED = {
    "671346": -(sp.sin(X) + 1) * (sp.sqrt(2) * sp.sin(X) - 1) / sp.sin(X) ** 2,
    "674433": -(2 * sp.cos(X) - 1) * (4 * sp.cos(X) + 5),
    "674804": -(2 * sp.cos(X) + 1) * (3 * sp.cos(X) - 4),
    "679826": (sp.cos(X - sp.pi / 4) - 1) * (2 * sp.cos(X - sp.pi / 4) - 1),
    "680000": sp.sqrt(3) * sp.cos(X) * (2 * sp.cos(X) + 1),
    "680774": sp.cos(X) * (2 * sp.cos(X) - sp.sqrt(3)),
    "681158": sp.cos(X) ** 2 - sp.Rational(1, 2),
    "681295": sp.cos(X) ** 2 - sp.Rational(1, 4),
    "681292": (2 * sp.cos(X) - sp.sqrt(2)) * (2 * sp.cos(X) + sp.sqrt(3)),
    "681587": (2 * sp.cos(X) - 1) * (2 * sp.cos(X) + sp.sqrt(2)),
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
def test_original_equations_and_complete_root_sets_are_independent(c):
    task = c["task"]
    assert sp.trigsimp(sp.expand(sp.expand_trig(ORIGINAL[task] - FACTORED[task]))) == 0
    a = analysis(c)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == tuple(map(sp.Rational, RESIDUES[task].split()))
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    for q in roots:
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
        if a.poles:
            assert sp.sin(q * sp.pi) != 0


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
def test_circle_scope_uses_actual_x_and_preserves_the_source_svg(c):
    a = analysis(c)
    asset = c["context"]["normalized_content"]["assets"][0]
    entry = CIRCLES[asset["asset_id"]]
    visible = {sp.Rational(m["angle"]) for m in entry["green_markers"]}
    expected = (
        {q % 2 for q in a.selected}
        if entry.get("point_scope") == "selected"
        else set(select(a.series, (0, 2, True, False))[0])
    )
    assert visible == expected == set(map(sp.Rational, entry["residues"]))
    assert tuple(map(sp.Rational, entry["labels"])) == a.selected
    assert asset["asset_id"] in plan(c).solution_html


def test_parent_shifted_cosine_remains_the_quadratic_variable_without_a_new_parameter():
    c = case("679826")
    a = analysis(c)
    assert a.translation == -sp.Rational(1, 4) and a.shifted_notation
    assert a.preferred == C and a.reduced == 2 * C * C - 3 * C + 1
    assert a.series == (
        (sp.Rational(1, 4), 2),
        (sp.Rational(7, 12), 2),
        (sp.Rational(-1, 12), 2),
    )
    html = plan(c).solution_html
    assert r"\cos \left(x - \frac{\pi}{4}\right)" in html
    assert 'data-inline-latex="t=' not in html and "Сделаем замену угла" not in html
    assert (
        html.index(r"\sin(x)=")
        < html.index("Выразим исходную переменную")
        < html.index("С помощью числовой окружности")
    )
    assert r"- \frac{\pi}{12}" in plan(c).answer


@pytest.mark.parametrize(
    "task,rejected", [("674433", -sp.Rational(5, 4)), ("674804", sp.Rational(4, 3))]
)
def test_nonexistent_cosine_levels_are_rejected_without_losing_the_valid_child(
    task, rejected
):
    c = case(task)
    a = analysis(c)
    assert rejected in a.branches[0].candidates and rejected not in a.branches[0].values
    assert "от −1 до 1" in plan(c).solution_html


def test_reciprocal_sine_retains_its_original_pole_and_all_three_root_families():
    c = case("671346")
    a = analysis(c)
    assert a.preferred == S and a.reciprocal is not None
    assert set(a.branches[0].values) == {-1, sp.sqrt(2) / 2}
    html = plan(c).solution_html
    assert html.index(r"(\sin x)\ne0") < html.index(r"t=\frac{1}{(\sin x)}")
    assert a.selected[-1] == a.bounds[1]


def test_square_child_uses_the_parent_cosine_method_and_merges_all_periodic_roots():
    a = analysis(case("681295"))
    assert a.preferred == C and a.branches[0].variable == C
    assert set(a.branches[0].values) == {sp.Rational(-1, 2), sp.Rational(1, 2)}
    assert a.series == ((sp.Rational(1, 3), 1), (sp.Rational(2, 3), 1))


@pytest.mark.parametrize(
    "argument",
    [r"x-\frac{\pi}{7}", r"2x-\frac{\pi}{4}", r"a-\frac{\pi}{4}", r"x+\frac{7\pi}{3}"],
)
def test_unreviewed_parent_shifted_arguments_fail_closed(argument):
    with pytest.raises(UnsupportedCondition):
        parent_angle('<span data-inline-latex="\\cos(' + argument + ')=1"></span>')


def test_conflicting_parent_shifted_angles_fail_closed():
    html = r'<span data-inline-latex="\cos(x-\frac{\pi}{4})=1"></span><span data-inline-latex="\cos(x+\frac{\pi}{4})=\frac{1}{2}"></span>'
    with pytest.raises(UnsupportedCondition):
        parent_angle(html)


@pytest.mark.parametrize("task", ["680000", "680774"])
def test_unknown_selection_instruction_is_not_discarded(task):
    c = case(task)
    ctx = deepcopy(c["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    section["html"] = section["html"].replace("Ука", "Выберите некоторые корни. Ука", 1)
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
