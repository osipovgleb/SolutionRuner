"""Grouping, repeated factors, and exact unions with isolated real roots."""

import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_scalar import compare
from solution_runner.pipelines.equations.exam_trigonometric import (
    C,
    S,
    T,
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_affine import compile_affine
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    LINES,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import (
    compile_equation,
)
from solution_runner.pipelines.equations.exam_trigonometric_inverse import decode
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_mixed_factors.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "520495": "3 10/3 4",
    "515667": "-5 -4",
    "520515": "-1 -5/6 0",
    "509888": "7/3",
    "513912": "5/3 9/4 7/3 8/3",
    "513919": "7/3 8/3 11/4 10/3",
    "514239": "-7/6 -5/6",
    "485977": "4/3 7/3",
    "485986": "1/6",
    "501486": "-5/2 -7/4 -3/2 -5/4",
    "511361": "3 10/3 4",
    "500427": "3 15/4 4",
    "520973": "-3 -13/6 -2",
    "500407": "5/3 2 7/3 3",
    "520980": "-4 -10/3 -3",
    "661142": "7/2 17/4 9/2",
    "517829": "2/3",
}
RESIDUES = {
    "520495": "0 2/3 1 4/3",
    "515667": "0 1/6 5/6 1",
    "520515": "0 5/6 1 7/6",
    "509888": "1/3 5/3",
    "513912": "1/4 1/3 2/3 5/4 4/3 5/3",
    "513919": "1/3 2/3 3/4 4/3 5/3 7/4",
    "514239": "5/6 7/6",
    "485977": "1/3 4/3",
    "485986": "1/6 7/6",
    "501486": "1/4 1/2 3/4 3/2",
    "511361": "0 2/3 1 4/3",
    "500427": "0 1/4 1 7/4",
    "520973": "0 1/6 1 11/6",
    "500407": "0 1/3 1 5/3",
    "520980": "0 2/3 1 4/3",
    "661142": "1/4 1/2 3/4 3/2",
    "517829": "2/3 4/3",
    "518143": "0",
}
ORIGINAL = {
    "520495": 2 * sp.sin(sp.pi + X) * sp.sin(sp.pi / 2 + X) - sp.sin(X),
    "515667": 2 * sp.sin(sp.pi + X) * sp.cos(sp.pi / 2 + X) - sp.sin(X),
    "520515": 2 * sp.cos(X - 3 * sp.pi / 2) * sp.cos(2 * sp.pi - X)
    - sp.sqrt(3) * sp.sin(X),
    "509888": 2 * sp.cos(X) ** 3 - sp.cos(X) ** 2 + 2 * sp.cos(X) - 1,
    "513912": sp.tan(X) ** 3 - sp.tan(X) ** 2 - 3 * sp.tan(X) + 3,
    "513919": sp.tan(X) ** 3 + sp.tan(X) ** 2 - 3 * sp.tan(X) - 3,
    "514239": 2 * sp.cos(X) ** 3
    + sp.sqrt(3) * sp.cos(X) ** 2
    + 2 * sp.cos(X)
    + sp.sqrt(3),
    "485977": sp.sin(2 * X)
    - 2 * sp.sqrt(3) * sp.cos(X) ** 2
    - 4 * sp.sin(X)
    + 4 * sp.sqrt(3) * sp.cos(X),
    "485986": sp.sin(2 * X)
    - 2 * sp.sqrt(3) * sp.sin(X) ** 2
    + 4 * sp.cos(X)
    - 4 * sp.sqrt(3) * sp.sin(X),
    "501486": sp.sqrt(2) * sp.sin(X) ** 3 - sp.sqrt(2) * sp.sin(X) + sp.cos(X) ** 2,
    "511361": 2 * sp.cos(X) ** 3 - 2 * sp.cos(X) - sp.sin(X) ** 2,
    "500427": sp.sqrt(2) * sp.cos(X) ** 3 - sp.sqrt(2) * sp.cos(X) + sp.sin(X) ** 2,
    "520973": 2 * sp.cos(X) - sp.sqrt(3) * sp.sin(X) ** 2 - 2 * sp.cos(X) ** 3,
    "500407": 2 * sp.cos(X) ** 3 - 2 * sp.cos(X) + sp.sin(X) ** 2,
    "520980": 2 * sp.cos(X) + sp.sin(X) ** 2 - 2 * sp.cos(X) ** 3,
    "661142": 2 * sp.sin(X) - sp.sqrt(2) * sp.cos(X) ** 2 - 2 * sp.sin(X) ** 3,
    "517829": 2 * X * sp.cos(X) - 8 * sp.cos(X) + X - 4,
    "518143": X * sp.cos(X) + 4 * sp.cos(X) - X - 4,
}
FACTORED = {
    "520495": -sp.sin(X) * (1 + 2 * sp.cos(X)),
    "515667": sp.sin(X) * (2 * sp.sin(X) - 1),
    "520515": -sp.sin(X) * (2 * sp.cos(X) + sp.sqrt(3)),
    "509888": (2 * sp.cos(X) - 1) * (sp.cos(X) ** 2 + 1),
    "513912": (sp.tan(X) - 1) * (sp.tan(X) ** 2 - 3),
    "513919": (sp.tan(X) + 1) * (sp.tan(X) ** 2 - 3),
    "514239": (2 * sp.cos(X) + sp.sqrt(3)) * (sp.cos(X) ** 2 + 1),
    "485977": 2 * (sp.cos(X) - 2) * (sp.sin(X) - sp.sqrt(3) * sp.cos(X)),
    "485986": 2 * (sp.sin(X) + 2) * (sp.cos(X) - sp.sqrt(3) * sp.sin(X)),
    "501486": sp.cos(X) ** 2 * (1 - sp.sqrt(2) * sp.sin(X)),
    "511361": -(sp.sin(X) ** 2) * (2 * sp.cos(X) + 1),
    "500427": sp.sin(X) ** 2 * (1 - sp.sqrt(2) * sp.cos(X)),
    "520973": sp.sin(X) ** 2 * (2 * sp.cos(X) - sp.sqrt(3)),
    "500407": sp.sin(X) ** 2 * (1 - 2 * sp.cos(X)),
    "520980": sp.sin(X) ** 2 * (2 * sp.cos(X) + 1),
    "661142": sp.cos(X) ** 2 * (2 * sp.sin(X) - sp.sqrt(2)),
    "517829": (X - 4) * (2 * sp.cos(X) + 1),
    "518143": (X + 4) * (sp.cos(X) - 1),
}
ZERO_SQUARE = {
    "501486": C,
    "511361": S,
    "500427": S,
    "520973": S,
    "500407": S,
    "520980": S,
    "661142": C,
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for cc in CASES
        if cc["task"] == c["group"]
        for s in cc["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def handler(c):
    return get_handler(get_group_profile(c["group"]).content_rule_key)


def plan(c, context=None):
    ctx = context or c["context"]
    h = handler(c)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(ctx)
    )
    return h.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
        )
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
    ) == (g["uuid"], g["theme_uuid"], 6, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_independent_equations_full_periodic_sets_and_isolated_roots(c):
    task = c["task"]
    a = analysis(c)
    assert sp.trigsimp(sp.expand(sp.expand_trig(ORIGINAL[task] - FACTORED[task]))) == 0
    assert a.residues == tuple(map(sp.Rational, RESIDUES[task].split()))
    assert select(a.series, (0, 2, True, False))[0] == a.residues
    expected = (
        (-sp.Integer(2), -4 / sp.pi)
        if task == "518143"
        else tuple(map(sp.Rational, SELECTED[task].split()))
    )
    assert a.selected == expected
    for q in (*a.residues, *a.selected):
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
        if task in ("513912", "513919"):
            assert sp.cos(q * sp.pi) != 0
    if a.affine:
        assert a.affine.roots == (
            (sp.Integer(4),) if task == "517829" else (-sp.Integer(4),)
        )
        assert all(sp.simplify(ORIGINAL[task].subs(X, r)) == 0 for r in a.affine.roots)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    ctx = deepcopy(c["context"])
    before = deepcopy(ctx)
    p = plan(c, ctx)
    assert ctx == before and p.condition_html == next(
        s["html"]
        for s in ctx["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>UNUSED9999</p>"
    assert plan(c, ctx) == p
    for t in p.transformations:
        key = t["transformation_target_id"]
        kind = "assets" if key.startswith("asset:") else "sections"
        items = ctx["normalized_content"][kind]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert all(
        a in ctx["normalized_content"]["assets"]
        for a in before["normalized_content"]["assets"]
    )
    assert len(ctx["normalized_content"]["assets"]) - len(
        before["normalized_content"]["assets"]
    ) == (1 if c["task"] == "518143" else 0)


@pytest.mark.parametrize("task", ZERO_SQUARE)
def test_squared_zero_factor_and_its_pi_period_remain_separate(task):
    a = analysis(case(task))
    zero = ZERO_SQUARE[task]
    assert (
        a.factored_source is not None
        and a.branches[0].variable == zero
        and a.branches[0].values == (0,)
    )
    assert any(p == 1 for q, p in a.series)
    assert sp.rem(a.raw, zero**2, zero) == 0
    assert (
        not a.division
        and "На тригонометрический множитель не делим" in plan(case(task)).solution_html
    )


@pytest.mark.parametrize("task", ("509888", "513912", "513919", "514239"))
def test_cubic_grouping_and_impossible_quadratic_are_explained(task):
    a = analysis(case(task))
    html = plan(case(task)).solution_html
    assert a.branches[0].grouping and "Сгруппируем слагаемые" in html
    if task in ("509888", "514239"):
        assert "отрицательный дискриминант" in html and "не обращается в нуль" in html
    else:
        assert "Решим кубическое" in html and r"\cos x\ne0" in html


@pytest.mark.parametrize("task", ("485977", "485986"))
def test_affine_range_exclusion_precedes_local_homogeneous_division(task):
    a = analysis(case(task))
    html = plan(case(task)).solution_html
    assert (
        len(a.branches) == 2
        and a.branches[0].values == ()
        and a.branches[1].variable == T
    )
    assert html.index("не входит в отрезок") < html.index(
        "только в этой ветви можно разделить"
    )
    assert not a.division


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_source_figure_scope_matches_periodic_and_isolated_components(c):
    a = analysis(c)
    asset = c["context"]["normalized_content"]["assets"][0]
    e = (CIRCLES | LINES)[asset["asset_id"]]
    assert bool(handler(c).diagram_specs(c["context"])) == (c["task"] == "518143")
    assert tuple(decode(q) for q in e["residues"]) == a.residues
    labels = (
        select(a.series, a.bounds)[0]
        if e.get("label_scope") == "periodic"
        else a.selected
    )
    assert tuple(decode(q) for q in e["labels"]) == labels
    if e.get("figure_kind") != "number_line":
        assert sorted({sp.Rational(p["angle"]) for p in e["green_markers"]}) == list(
            a.residues
        )


@pytest.mark.parametrize("task", ("517829", "518143"))
def test_isolated_roots_are_finite_union_terms_and_use_number_line_selection(task):
    c = case(task)
    a = analysis(c)
    p = plan(c)
    assert (
        a.selection_method == "number_line"
        and a.affine is not None
        and r"\cup" in p.answer
    )
    assert ("\\{4\\}" if task == "517829" else "\\{-4\\}") in p.answer
    assert "На числовой прямой" in p.solution_html
    if task == "517829":
        assert a.selected == (sp.Rational(2, 3),) and "4&gt;\\pi" in p.solution_html
    else:
        assert a.selected == (-2, -4 / sp.pi) and p.answer.endswith(r"-4")
        assert "Числовая прямая" in p.solution_html


def test_original_schematic_line_preserves_tick_order_and_all_visible_root_labels():
    e = LINES["74d39d5b-4413-42bd-80d3-c6af4a9fe9e4"]
    data = gzip.decompress(
        (DIRECTORY / "74d39d5b-4413-42bd-80d3-c6af4a9fe9e4.svgz").read_bytes()
    )
    assert hashlib.sha256(data).hexdigest() == e["sha256"]
    root = ET.fromstring(data)
    xs = {
        float(n.get("x1"))
        for n in root.iter()
        if n.tag.endswith("line") and n.get("x1") == n.get("x2")
    }
    ticks = e["ticks"]
    assert all(t["x"] in xs for t in ticks)
    values = [decode(t["value"]) * sp.pi for t in ticks]
    assert all(
        compare(a, b) < 0 and x["x"] < y["x"]
        for a, b, x, y in zip(values, values[1:], ticks, ticks[1:])
    )
    visible = [decode(t["value"]) * sp.pi for t in ticks if t["role"].endswith("root")]
    assert visible == [-2 * sp.pi / 3, 2 * sp.pi / 3, 4]
    assert e["interval_arc"] == [ticks[1]["x"], ticks[4]["x"]]


def test_prepared_line_places_both_types_of_root_in_physical_radians():
    a = analysis(case("518143"))
    root = ET.parse(DIRECTORY / "affine-negative-four-number-line.svg").getroot()
    groups = next(g for g in root if g.tag.endswith("g"))
    points = [g for g in groups if g.get("data-role")]
    values = []
    for g in points:
        q = (
            sp.Rational(g.get("data-q"))
            if g.get("data-q") is not None
            else sp.Rational(g.get("data-scalar")) / sp.pi
        )
        circle = next(n for n in g if n.tag.endswith("circle"))
        actual = float(circle.get("cx"))
        expected = float(40 + (q - a.bounds[0]) / (a.bounds[1] - a.bounds[0]) * 350)
        assert abs(actual - expected) < 1e-6
        if g.get("data-role").endswith("root"):
            values.append(q)
    assert tuple(values) == a.selected


@pytest.mark.parametrize(
    "formula",
    [
        r"x^2\cos x-x=0",
        r"\frac{x}{x-4}\cos x=0",
        r"x\cos(2x)-4\cos(2x)+x-4=0",
        r"x\tg x-4\tg x+x-4=0",
    ],
)
def test_unreviewed_mixed_affine_forms_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_affine(formula)


def test_cubic_review_flag_does_not_widen_the_default_tangent_grammar():
    with pytest.raises(UnsupportedCondition):
        compile_equation(r"\tg^3 x=1")
    with pytest.raises(UnsupportedCondition):
        compile_equation(r"\tg^3 x=1", allow_cubic=True)
    p, _ = compile_equation(r"\tg^3 x-\tg^2 x-3\tg x+3=0", allow_cubic=True)
    assert sp.expand(p - (T - 1) * (T * T - 3)) == 0


def test_isolated_boundary_roots_are_deduplicated_and_open_ends_are_respected():
    p = parent(case("517829"))
    closed = analyze(r"x\cos x-x=0", r"[0;\pi]", (sp.S.Zero, sp.pi, True, True), p)
    assert closed.affine.roots == (0,) and closed.selected == (0,)
    opened = analyze(r"x\cos x-x=0", r"(0;\pi]", (sp.S.Zero, sp.pi, False, True), p)
    assert opened.selected == ()
    only = analyze(
        r"x\cos x-4\cos x-2x+8=0", r"[\pi;2\pi]", (sp.pi, 2 * sp.pi, True, True), p
    )
    assert (
        only.series == ()
        and only.selected == (4 / sp.pi,)
        and render(only, "")[0].startswith(r"а) \{4\};")
    )
