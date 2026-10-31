"""Parent methods preserve reciprocal domains, scaled angles and complete root sets."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    C,
    S,
    analyze,
    canonical,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
    methods,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_methods.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
A = sp.acos(sp.Rational(3, 4)) / sp.pi
B = sp.atan(2) / sp.pi
SELECTED = {
    "519514": (3 + A, 4),
    "519540": (sp.Rational(5, 2) + A, sp.Rational(7, 2)),
    "500212": (-sp.Rational(14, 3),),
    "510829": (-sp.Rational(11, 3), -3),
    "511404": (-sp.Rational(5, 6), -sp.Rational(1, 2), sp.Rational(1, 2)),
    "500386": (sp.Rational(13, 6),),
    "519634": (sp.Rational(7, 3),),
    "517262": (sp.Rational(5, 2), 3, sp.Rational(7, 2)),
    "656573": (-sp.Rational(7, 2), -3, -2),
    "656574": (-sp.Rational(3, 2), -1, -sp.Rational(1, 2)),
    "505428": (
        sp.Rational(8, 3),
        sp.Rational(11, 4),
        sp.Rational(11, 3),
        sp.Rational(15, 4),
    ),
    "511407": (sp.Rational(5, 4), 1 + B),
    "507583": (sp.Rational(9, 8), sp.Rational(5, 4), sp.Rational(11, 8)),
}
FULL_PERIOD = {
    "519514": (0, 1 - A, 1 + A),
    "519540": (sp.Rational(1, 2) - A, sp.Rational(1, 2) + A, sp.Rational(3, 2)),
    "500212": (sp.Rational(2, 3), sp.Rational(4, 3)),
    "510829": (sp.Rational(1, 3), 1, 3, sp.Rational(11, 3)),
    "511404": (
        sp.Rational(1, 2),
        sp.Rational(5, 6),
        sp.Rational(7, 6),
        sp.Rational(3, 2),
    ),
    "500386": (sp.Rational(1, 6), sp.Rational(5, 6)),
    "519634": (sp.Rational(1, 3), sp.Rational(5, 3)),
    "517262": (sp.Rational(1, 2), 1, sp.Rational(3, 2)),
    "656573": (0, sp.Rational(1, 2), 1),
    "656574": (sp.Rational(1, 2), 1, sp.Rational(3, 2)),
    "505428": (
        sp.Rational(2, 3),
        sp.Rational(3, 4),
        sp.Rational(5, 3),
        sp.Rational(7, 4),
    ),
    "511407": (sp.Rational(1, 4), B, sp.Rational(5, 4), 1 + B),
    "507583": tuple(
        sp.Rational(n, 8) for n in (1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15)
    ),
}
ORIGINAL = {
    "519514": sp.sin(7 * sp.pi / 2 + X) + 2 * sp.cos(2 * X) - 1,
    "519540": sp.cos(5 * sp.pi / 2 - X) - 2 * sp.cos(2 * X) - 1,
    "500212": 6 * sp.sin(X) ** 2 + 5 * sp.sin(sp.pi / 2 - X) - 2,
    "510829": sp.cos(X) + sp.sqrt(3) * sp.sin(3 * sp.pi / 2 - X / 2) + 1,
    "511404": sp.sin(sp.pi / 2 + 2 * X) + sp.sqrt(3) * sp.cos(X) + 1,
    "500386": 4 * sp.cos(X) ** 2 + 4 * sp.cos(sp.pi / 2 + X) - 1,
    "519634": 4 / sp.sin(7 * sp.pi / 2 - X) ** 2 - 11 / sp.cos(X) + 6,
    "517262": sp.cos(sp.pi - X) ** 2 - sp.sin(X + 3 * sp.pi / 2),
    "656573": sp.sin(X + sp.pi) ** 2 - sp.cos(-3 * sp.pi / 2 - X),
    "656574": sp.cos(sp.pi - X) ** 2 - sp.sin(3 * sp.pi / 2 + X),
    "505428": sp.tan(X) ** 2 + (1 + sp.sqrt(3)) * sp.tan(X) + sp.sqrt(3),
    "511407": sp.tan(X) ** 2 - 3 * sp.tan(X) + 2,
    "507583": 4 * sp.sin(2 * X) ** 4 + 3 * sp.cos(4 * X) - 1,
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for s in case(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c, context=None):
    _, f, interval, bounds = read(context or c["context"])
    return analyze(f, interval, bounds, parent(c))


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_catalog_registration_reuses_the_existing_rule(g):
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
def test_exact_full_period_and_selected_roots_satisfy_independent_original_equations(c):
    a = analysis(c)
    period = sp.Integer(4 if c["task"] == "510829" else 2)
    actual = select(a.series, (sp.Integer(0), period, True, False))[0]
    assert actual == FULL_PERIOD[c["task"]] and a.selected == SELECTED[c["task"]]
    for q in (*actual, *a.selected):
        assert sp.simplify(ORIGINAL[c["task"]].subs(X, sp.expand(q * sp.pi))) == 0
    if c["task"] not in ("519514", "519540", "511407"):
        denominator = 24 if c["task"] == "507583" else 12
        grid = []
        for i in range(int(period) * denominator):
            x = sp.pi * i / denominator
            if c["task"] == "519634" and sp.cos(x) == 0:
                continue
            if c["task"] == "505428" and sp.cos(x) == 0:
                continue
            if sp.simplify(ORIGINAL[c["task"]].subs(X, x)) == 0:
                grid.append(sp.Rational(i, denominator))
        assert tuple(grid) == actual


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_sources_and_conditions(c):
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
    assert plan(c, ctx).transformations == ()
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )
    images = BeautifulSoup(p.solution_html, "html.parser").find_all("img")
    assert (
        len(images) == 1
        and images[0]["data-asset-id"]
        == ctx["normalized_content"]["assets"][0]["asset_id"]
    )


def test_non_tabular_cosine_answer_groups_the_whole_signed_angle():
    p = plan(case("519514"))
    assert r"\pm\left(\pi - \arccos" in p.answer
    assert r"\right)+2 \pi k" in p.answer
    assert "operatorname{acos}" not in p.answer


def test_half_angle_circle_is_checked_in_its_own_coordinate_and_replay_uses_x():
    c = case("510829")
    a = analysis(c)
    assert a.scale == sp.Rational(1, 2) and a.selected == (-sp.Rational(11, 3), -3)
    entry = deepcopy(
        CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    )
    assert entry["circle_scale"] == "1/2" and entry["bounds"][:2] == ["-2", "-5/4"]
    validate(entry, a)
    entry["circle_scale"] = "1"
    with pytest.raises(UnsupportedCondition):
        validate(entry, a)
    html = plan(c).solution_html
    assert r"\cos \frac{x}{2}" in html
    assert r"- 2 \pi\le\frac{x}{2}\le- \frac{5 \pi}{4}" in html
    assert r"\frac{x}{2}=- \frac{11 \pi}{6}" in html
    assert r"\Longleftrightarrow\quad x=- \frac{11 \pi}{3}" in html


def test_reciprocal_substitution_keeps_the_original_nonzero_domain():
    c = case("519634")
    a = analysis(c)
    t = sp.Symbol("t", real=True)
    assert a.reciprocal == 4 * t * t - 11 * t + 6
    assert set(a.poles) == {C, C * C}
    assert a.branches[0].values == (sp.Rational(1, 2),)
    html = plan(c).solution_html
    assert r"(\cos x)\ne0" in html and r"t=\frac{1}{(\cos x)}" in html
    assert r"t=\frac{3}{4}" in html and "не входит в отрезок" in html


def test_parent_tangent_substitution_and_child_inverse_angle_are_preserved():
    for task in ("505428", "511407"):
        a = analysis(case(task))
        html = plan(case(task)).solution_html
        assert a.substitution == "t"
        assert r"t=(\tg x)" in html and "Вернёмся к исходной переменной" in html
        assert "-1\\le t" not in html


def test_both_parent_methods_are_independent_complete_and_keep_order_and_legend():
    c = case("507583")
    a = analysis(c)
    assert a.scale == 4 and a.doubled and a.raw == C * C + C
    assert a.alternative is not None and a.alternative.scale == 2
    assert a.alternative.preferred == S
    assert (
        canonical(a.series) == canonical(a.alternative.series) == FULL_PERIOD[c["task"]]
    )
    html = plan(c).solution_html
    assert (
        html.index("понижения степени")
        < html.index("<img")
        < html.index("Границы дуги")
        < html.index("Приведём другое решение")
        < html.index("u=")
    )
    assert r"\cos 4 x" in html and r"\sin 2 x" in html
    assert "(*)" in html and "(**)" in html
    assert html.count("<img") == 1


@pytest.mark.parametrize(
    "formula",
    [
        r"\sin(\frac{x}{5})=0",
        r"\sin(\sqrt{2}x)=0",
        r"\frac{1}{\sin x+1}=2",
        r"\frac{1}{\sin x\cos x}=2",
        r"\frac{1}{\cos^3 x}=2",
        r"\sin x=\sin x",
    ],
)
def test_unreviewed_scaled_and_reciprocal_grammars_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, C, sp.Integer(1))


def test_unreviewed_extra_method_and_changed_series_legend_fail_closed():
    with pytest.raises(UnsupportedCondition):
        methods("<p>Другое решение пункта а</p><p>Другое решение пункта а</p>")
    c = case("507583")
    ctx = deepcopy(c["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    section["html"] = section["html"].replace("+3\\cos", "+4\\cos")
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)

    _, f, interval, bounds = read(c["context"])
    with pytest.raises(UnsupportedCondition):
        analyze(f, interval, bounds, parent(c) + "<p>Ещё одно решение.</p>")
