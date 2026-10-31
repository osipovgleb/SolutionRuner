"""Complete the quadratic theme with periodic shifts and sine/cosine combinations."""

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
    T,
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import CIRCLES, read
from solution_runner.pipelines.equations.exam_trigonometric_combination import (
    branches,
    impossible_branch,
)
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_combinations.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "681574": "-3 -2 -7/4",
    "687516": "25/4 31/4",
    "688734": "-11/6",
    "688780": "11/6",
    "692901": "11/6 2 3 19/6 23/6 4",
    "701451": "31/6 35/6",
    "701452": "37/4 39/4",
    "701491": "22/3 23/3",
    "702493": "-21/4 -17/4",
    "702512": "-19/4 -15/4",
}
RESIDUES = {
    "681574": "0 1/4 3/4 1",
    "687516": "1/4 7/4",
    "688734": "1/6 5/6",
    "688780": "7/6 11/6",
    "692901": "0 1 7/6 11/6",
    "701451": "7/6 11/6",
    "701452": "5/4 7/4",
    "701491": "4/3 5/3",
    "702493": "3/4 7/4",
    "702512": "1/4 5/4",
}
ORIGINAL = {
    "681574": 2 * sp.sqrt(2) * sp.sin(X + sp.pi / 3)
    + 2 * sp.cos(X) ** 2
    - 2
    - sp.sqrt(6) * sp.cos(X),
    "687516": 1 / sp.cos(3 * sp.pi + X) ** 2
    - sp.sqrt(2) / sp.cos(X)
    + 1 / (14 * sp.cos(X))
    - 1 / (7 * sp.sqrt(2)),
    "688734": 2 * sp.cos(2 * X) - 12 * sp.cos(X + sp.pi / 2) - 7,
    "688780": 2 * sp.cos(2 * X) - 16 * sp.cos(X + 3 * sp.pi / 2) - 9,
    "692901": sp.sin(2025 * sp.pi / 2 + X) ** 2
    + sp.sin(X + 2026 * sp.pi / 2)
    - 2 * sp.cos(X) ** 2
    + sp.Rational(3, 2) * sp.sin(X)
    + 1,
    "701451": 4 * sp.cos(X + sp.pi / 6) + 2 * sp.sqrt(3) * sp.cos(sp.pi + X) - 1,
    "701452": 4 * sp.cos(X + sp.pi / 4) + 2 * sp.sqrt(2) * sp.cos(sp.pi - X) - 2,
    "701491": 4 * sp.cos(X + sp.pi / 3) + 2 * sp.cos(sp.pi - X) - 3,
    "702493": sp.sin(2 * X) + 2 * sp.sqrt(2) * sp.sin(X + sp.pi / 4) + 1,
    "702512": sp.sin(2 * X) + 2 * sp.sqrt(2) * sp.sin(X - sp.pi / 4) - 1,
}
FACTORED = {
    "681574": -sp.sin(X) * (2 * sp.sin(X) - sp.sqrt(2)),
    "687516": -(sp.sqrt(2) * sp.cos(X) - 1) * (sp.cos(X) + 14) / (14 * sp.cos(X) ** 2),
    "688734": -(2 * sp.sin(X) - 1) * (2 * sp.sin(X) - 5),
    "688780": -(2 * sp.sin(X) + 1) * (2 * sp.sin(X) + 7),
    "692901": sp.sin(X) * (sp.sin(X) + sp.Rational(1, 2)),
    "701451": -2 * sp.sin(X) - 1,
    "701452": -2 * (sp.sqrt(2) * sp.sin(X) + 1),
    "701491": -2 * sp.sqrt(3) * sp.sin(X) - 3,
    "702493": (sp.sin(X) + sp.cos(X)) * (sp.sin(X) + sp.cos(X) + 2),
    "702512": (sp.sin(X) - sp.cos(X)) * (2 - sp.sin(X) + sp.cos(X)),
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
def test_circle_scope_and_multiple_turn_labels_use_actual_computed_roots(c):
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


@pytest.mark.parametrize(
    "task,sine,cosine,tangent", [("702493", -1, -1, -1), ("702512", 1, -1, 1)]
)
def test_combination_excludes_only_the_impossible_extreme_before_ratio_division(
    task, sine, cosine, tangent
):
    c = case(task)
    a = analysis(c)
    assert len(a.branches) == 2
    valid, excluded = a.branches
    assert not valid.impossible and valid.variable == T and valid.values == (tangent,)
    assert excluded.impossible and excluded.values == () and excluded.residues == ()
    assert sp.simplify(excluded.original.subs({S: sine, C: cosine})) == 0
    assert sine * sine + cosine * cosine == 2
    assert sp.expand(a.reduced - a.raw) == a.raw.subs({S: 0, C: 0}) * (
        S * S + C * C - 1
    )
    html = plan(c).solution_html
    assert (
        html.index("ветвь корней не имеет")
        < html.index("оставшееся однородное")
        < html.index("только в этой ветви можно разделить")
    )
    assert r"\cos(x)\ne0" in html
    assert "Коши" not in html and "D=" not in html
    if task == "702512":
        assert sp.expand(valid.original) == S - C
        assert "1 -" in html or "-1" in html


def test_large_half_pi_shifts_keep_periodicity_and_every_turn_of_the_selected_interval():
    c = case("692901")
    a = analysis(c)
    assert sp.expand(a.reduced - S * S - S / 2) == 0
    assert len(a.selected) == 6 and a.selected[-1] == a.bounds[1]
    html = plan(c).solution_html
    assert "2025" in html and "2026" in html
    assert a.selected.count(2) == 1 and a.selected.count(4) == 1


def test_reciprocal_cosine_discards_the_out_of_range_inverse_and_keeps_its_pole():
    c = case("687516")
    a = analysis(c)
    assert a.reciprocal is not None and a.preferred == C
    assert -14 in a.branches[0].candidates and -14 not in a.branches[0].values
    html = plan(c).solution_html
    assert html.index(r"(\cos x)\ne0") < html.index(r"t=\frac{1}{(\cos x)}")
    assert "от −1 до 1" in html


@pytest.mark.parametrize(
    "task,rejected", [("688734", sp.Rational(5, 2)), ("688780", -sp.Rational(7, 2))]
)
def test_out_of_range_sine_levels_are_discarded(task, rejected):
    c = case(task)
    a = analysis(c)
    assert rejected in a.branches[0].candidates and rejected not in a.branches[0].values
    assert "от −1 до 1" in plan(c).solution_html


def test_child_selection_uses_its_equation_instead_of_copied_solution_numbers():
    c = case("701491")
    saved = next(
        s["html"]
        for s in c["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    assert r"\frac{37\pi}{4}" in saved and r"\frac{39\pi}{4}" in saved
    p = plan(c)
    assert r"\frac{22 \pi}{3}" in p.answer and r"\frac{23 \pi}{3}" in p.answer
    assert (
        r"\frac{37\pi}{4}" not in p.solution_html
        and r"\frac{39\pi}{4}" not in p.solution_html
    )


@pytest.mark.parametrize("expression", [S + C + 1, S + 2 * C + 3, S + C + 3, S * C + S])
def test_other_affine_factors_are_not_assumed_impossible(expression):
    assert impossible_branch(expression) is None


@pytest.mark.parametrize(
    "raw", [2 * S * C + S + C + 1, S + C, (S + C) ** 2, 2 * S * C + S - C + 1]
)
def test_unreviewed_combination_factorizations_fail_closed(raw):
    with pytest.raises(UnsupportedCondition):
        branches(raw)


@pytest.mark.parametrize("formula", [r"\sin(x+10001\pi)=0", r"\sin(101x)=0"])
def test_angle_complexity_remains_bounded(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, S, 1)


def test_unknown_interval_instruction_is_not_discarded():
    c = case("701452")
    ctx = deepcopy(c["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    section["html"] += "Не исключайте лишние корни."
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


def test_combination_proof_and_root_series_keep_a_scaled_base_angle():
    from solution_runner.pipelines.equations.exam_trigonometric_proof import render

    c = case("702493")
    formula = r"\sin 4x+2\sqrt{2}\sin(2x+\frac{\pi}{4})+1=0"
    bounds = (sp.S.Zero, 2 * sp.pi, True, False)
    a = analyze(formula, r"[0;2\pi)", bounds, parent(c))
    assert a.scale == 2
    assert a.selected == tuple(map(sp.Rational, ["3/8", "7/8", "11/8", "15/8"]))
    for q in a.selected:
        assert (
            sp.simplify(
                (sp.sin(4 * X) + 2 * sp.sqrt(2) * sp.sin(2 * X + sp.pi / 4) + 1).subs(
                    X, q * sp.pi
                )
            )
            == 0
        )
    _, _, html = render(a, "")
    assert r"(\sin 2 x)" in html and r"\cos(2 x)\ne0" in html
    assert r"(\tg 2 x)=-1" in html
