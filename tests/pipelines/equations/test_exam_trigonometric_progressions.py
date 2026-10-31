"""Step-based selection, exact constant angles and complete marked exam subparts."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import C, analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import CIRCLES, read
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_progressions.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "630119": "1 7/6 11/6 2",
    "630155": "3/2 11/6",
    "630184": "5/2 17/6",
    "635862": "5/3 7/3 8/3",
    "635964": "-11/6 -7/6 -5/6",
    "638591": "-9/4 -25/12 -23/12 -7/4",
    "641605": "-1/2 0 1/2 1 3/2",
    "641907": "-14/3 -4",
    "641925": "3 11/3",
}
RESIDUES = {
    "630119": "0 1 7/6 11/6",
    "630155": "7/6 3/2 11/6",
    "630184": "1/6 1/2 5/6",
    "635862": "1/3 2/3 4/3 5/3",
    "635964": "1/6 5/6 7/6 11/6",
    "638591": "1/12 1/4 3/4 11/12 13/12 5/4 7/4 23/12",
    "641605": "0 1/2 1 3/2",
    "641907": "0 2/3 4/3",
    "641925": "1/3 1 5/3",
}
ORIGINAL = {
    "630119": sp.cos(2 * X) + sp.sin(-X) - 1,
    "630155": sp.cos(2 * X) + 3 * sp.sin(-X) - 2,
    "630184": 2 * sp.cos(X) ** 2 - 3 * sp.sin(-X) - 3,
    "635862": sp.cos(X) ** 2 - sp.cos(2 * X) - sp.Rational(3, 4),
    "635964": sp.cos(X) ** 2 - sp.cos(2 * X) - sp.Rational(1, 4),
    "638591": 2 * sp.cos(13 * sp.pi / 6) * sp.cos(2 * X) - 1 - sp.cos(4 * X),
    "641605": sp.sin(sp.pi / 2 - 5 * X / 2) * sp.cos(3 * X / 2)
    - sp.sin(sp.pi - 5 * X / 2) * sp.sin(3 * X / 2)
    - sp.cos(2 * X) ** 2,
    "641907": 1 / sp.cos(X) ** 2 - 1 / sp.sin(3 * sp.pi / 2 + X) - 2,
    "641925": 1 / sp.cos(X) ** 2 + 1 / sp.sin(7 * sp.pi / 2 - X) - 2,
}
FACTORED = {
    "630119": -sp.sin(X) * (2 * sp.sin(X) + 1),
    "630155": -(sp.sin(X) + 1) * (2 * sp.sin(X) + 1),
    "630184": -(sp.sin(X) - 1) * (2 * sp.sin(X) - 1),
    "635862": sp.sin(X) ** 2 - sp.Rational(3, 4),
    "635964": sp.sin(X) ** 2 - sp.Rational(1, 4),
    "638591": -sp.cos(2 * X) * (2 * sp.cos(2 * X) - sp.sqrt(3)),
    "641605": -(sp.sin(2 * X) ** 2),
    "641907": (1 - sp.cos(X)) * (2 * sp.cos(X) + 1) / sp.cos(X) ** 2,
    "641925": (1 + sp.cos(X)) * (1 - 2 * sp.cos(X)) / sp.cos(X) ** 2,
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
def test_reused_circles_match_their_declared_scope_without_invented_images(c):
    assets = c["context"]["normalized_content"]["assets"]
    if not assets:
        assert "<img" not in plan(c).solution_html
        return
    a = analysis(c)
    entry = CIRCLES[assets[0]["asset_id"]]
    visible = {sp.Rational(m["angle"]) for m in entry["green_markers"]}
    expected = (
        {q % 2 for q in a.selected}
        if entry.get("point_scope") == "selected"
        else set(select(a.series, (0, 2, True, False))[0])
    )
    assert visible == expected == set(map(sp.Rational, entry["residues"]))
    assert tuple(map(sp.Rational, entry["labels"])) == a.selected
    assert assets[0]["asset_id"] in plan(c).solution_html


@pytest.mark.parametrize("task", ["630119", "630155"])
def test_step_and_interval_length_are_recomputed_for_every_child_series(task):
    c = case(task)
    a = analysis(c)
    assert a.selection_method == "progressions"
    html = plan(c).solution_html
    assert "Разность между соседними членами" in html
    assert "Решим неравенства" not in html and "окружности" not in html
    for _, period, start, end, values in a.selections:
        maximum = int(sp.floor((a.bounds[1] - a.bounds[0]) / period)) + 1
        assert len(values) <= maximum
        assert str(maximum) in html
        assert end - start + 1 == len(values)
    if task == "630119":
        assert {p for _, p, _, _, _ in a.selections} == {1, 2}
    else:
        assert {p for _, p, _, _, _ in a.selections} == {2}
        assert a.selected[0] == a.bounds[0]


def test_constant_cosine_is_evaluated_before_the_quadratic_in_double_angle():
    c = case("638591")
    a = analysis(c)
    assert a.scale == 2 and a.preferred == C and a.factorization
    assert a.identities[0] == (r"\cos(\frac{13\pi}{6})", sp.sqrt(3) / 2)
    html = plan(c).solution_html
    assert html.index(r"\cos(\frac{13\pi}{6})") < html.index("Вынесем общий множитель")
    assert r"(\cos 2 x)" in html


def test_sum_of_products_preserves_merged_series_and_inequality_selection():
    c = case("641605")
    a = analysis(c)
    assert a.selection_method == "inequalities" and a.scale == 2 and a.merged
    assert a.series == ((0, sp.Rational(1, 2)),)
    assert a.selections[0][2:4] == (-1, 3)
    html = plan(c).solution_html
    assert "Свернём произведения" in html and "Решим неравенства" in html


def test_two_paragraph_condition_with_source_six_marker_is_preserved_verbatim():
    c = case("635964")
    html = plan(c).condition_html
    assert "6)" in html and "<ol" not in html
    assert plan(c).answer.endswith(
        r"- \frac{11 \pi}{6};\ - \frac{7 \pi}{6};\ - \frac{5 \pi}{6}"
    )


@pytest.mark.parametrize(
    "old,new", [("6)", "в)"), ("6)", "б) Дополнительное условие"), ("а)", "1)")]
)
def test_unknown_paragraph_markers_or_instructions_fail_closed(old, new):
    c = case("635964")
    ctx = deepcopy(c["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    section["html"] = section["html"].replace(old, new)
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


@pytest.mark.parametrize("extra", ["<p>Дополнительное условие</p>", "<hr/>"])
def test_content_outside_the_two_paragraphs_is_not_discarded(extra):
    c = case("635964")
    ctx = deepcopy(c["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += extra
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


@pytest.mark.parametrize(
    "formula",
    [
        r"\cos(\frac{\pi}{7})\cos 2x=0",
        r"\cos(30^{\circ})\cos 2x=0",
        r"\tg(\frac{\pi}{4})\cos 2x=0",
        r"\cos y\cos 2x=0",
    ],
)
def test_unreviewed_constant_angle_coefficients_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, C, 2)


@pytest.mark.parametrize(
    "formula", [r"\frac{\cos x}{\sin 0}=0", r"\frac{\cos x}{\cos(\frac{\pi}{2})}=0"]
)
def test_undefined_constant_denominators_fail_before_any_cancellation(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, C, 1)


@pytest.mark.parametrize("task", ["641907", "641925"])
def test_reciprocal_substitution_keeps_the_parent_letter_and_original_pole(task):
    c = case(task)
    a = analysis(c)
    assert a.substitution == "y" and a.reciprocal is not None
    html = plan(c).solution_html
    assert html.index(r"(\cos x)\ne0") < html.index(r"y=\frac{1}{(\cos x)}")
    assert r"y\ne0" in html and 'data-inline-latex="t=' not in html
    assert "y^{2}" in html
