"""Whole root quotients, both-zero monotonicity and every plotted source row."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.radical_inequality_difference import analyze
from solution_runner.pipelines.equations.radical_inequality_difference_figures import (
    SOURCES,
    compatible,
)
from solution_runner.pipelines.equations.rational_inequality_figures import (
    read_formula,
    signature,
)
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = [
    r
    for r in json.loads(
        Path(__file__)
        .with_name("fixtures")
        .joinpath("radical_inequality_sources.json")
        .read_text()
    )
    if r["group"] == "507894"
]
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
R = sp.sqrt(5)
MANUAL = {
    "507894": (
        (X - 1) ** 2,
        X**2 + X,
        X**2 + X - 1,
        sp.Union(
            sp.Interval.Lopen((-1 - R) / 2, -1),
            sp.Interval(0, sp.Rational(1, 3)),
            sp.Interval.open((R - 1) / 2, sp.oo),
        ),
    ),
    "507922": (
        (X + 2) ** 2,
        X**2 - X,
        X**2 - X - 1,
        sp.Union(
            sp.Interval(-sp.oo, -sp.Rational(4, 5)),
            sp.Interval.Lopen((1 - R) / 2, 0),
            sp.Interval.Ropen(1, (1 + R) / 2),
        ),
    ),
    "511504": (
        (X - 2) ** 2,
        X**2 + X,
        X**2 + X - 2,
        sp.Union(
            sp.Interval.Lopen(-2, -1),
            sp.Interval(0, sp.Rational(4, 5)),
            sp.Interval.open(1, sp.oo),
        ),
    ),
}


def handler():
    return get_handler(get_group_profile("507894").content_rule_key)


def plan(row, context=None, parent=PARENT):
    ctx = _with_required_assets(
        row["context"] if context is None else context, handler().key
    )
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler().diagram_specs(ctx)
    )
    return handler().plan(
        PlanInput(ctx, parent_solution_html=parent, generated_solution_assets=generated)
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_manual_original_domains_rational_oracle_and_answers(row):
    a = analyze(read_formula(row["context"])[1])
    P, Q, D, expected = MANUAL[row["task"]]
    assert a.square == sp.expand(P) and a.other == Q and a.denominator == D
    assert sp.cancel(a.stage.original - (P - Q) / D) == 0
    root_domain = sp.Intersection(
        *(sp.solve_univariate_inequality(v >= 0, X, relational=False) for v in (P, Q))
    )
    excluded = sp.FiniteSet(*sp.solve(D, X))
    same_set(a.constraints.values, root_domain - excluded)
    assert sp.FiniteSet(*a.constraints.excluded) == excluded
    oracle = (
        sp.solve_univariate_inequality((P - Q) / D <= 0, X, relational=False).intersect(
            root_domain
        )
        - excluded
    )
    same_set(a.solution, oracle)
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_values_include_square_root_zero_and_both_denominator_signs(row):
    a = analyze(read_formula(row["context"])[1])
    P, Q, D, _expected = MANUAL[row["task"]]
    for point in {sp.Rational(n, 4) for n in range(-16, 17)} | set(a.stage.points):
        if a.constraints.values.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        value = sp.simplify(
            (sp.sqrt(P.subs(X, point)) - sp.sqrt(Q.subs(X, point))) / D.subs(X, point)
        )
        assert bool(a.solution.contains(point)) == bool(value <= 0), (
            row["task"],
            point,
            value,
        )


def test_both_roots_zero_is_valid_even_when_the_conjugate_is_zero():
    a = analyze(r"\frac{\sqrt{x^2}-\sqrt{x^2+x}}{x^2+x-1}\le0")
    assert a.square.subs(X, 0) == a.other.subs(X, 0) == 0
    assert a.denominator.subs(X, 0) == -1
    assert a.solution.contains(0)
    assert a.constraints.values.contains(0)


def test_both_roots_zero_does_not_rescue_an_original_zero_denominator():
    a = analyze(r"\frac{\sqrt{x^2}-\sqrt{x^2+x}}{x^2+x}\le0")
    assert a.stage.holes == (0,)
    assert not a.solution.contains(0)
    assert a.solution == sp.Interval.open(0, sp.oo)


def test_original_hole_inside_a_radicand_remains_after_polynomial_cancellation():
    formula = read_formula(ROWS[-1]["context"])[1].replace(
        "x^{2}-4x+4", r"\frac{x-2}{x-2}+x^2-4*x+3"
    )
    a = analyze(formula)
    assert a.square == (X - 2) ** 2 or sp.expand(a.square - (X - 2) ** 2) == 0
    assert 2 in a.stage.holes
    assert not a.solution.contains(2)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_equivalent_system_order_exact_native_reuse_readonly_and_replay(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and p.solution_html.count("<img ") == 1
    assert "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
    assert (
        p.solution_html.index("Перейдём к равносильной системе")
        < p.solution_html.index("Из первого")
        < p.solution_html.index("Второе неравенство")
        < p.solution_html.index("<img ")
        < p.solution_html.index("Пересекая полученные")
    )
    assert "оба корня равны нулю" in p.solution_html
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler().key,
        parent_solution_html=PARENT,
    )
    assert (
        record["status"] == "prepared"
        and record["transformations"] == list(p.transformations)
        and gateway.reads == [ctx["problem_id"]]
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    assert all(
        a in ctx["normalized_content"]["assets"]
        for a in original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("row", ROWS[:2], ids=lambda r: r["task"])
def test_exact_two_or_three_row_source_is_restored_when_missing(row):
    uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = SOURCES["figures"][uid]
    assert entry["rows"] == (2 if row["task"] == "507894" else 3)
    assert uid in plan(row).solution_html and not handler().diagram_specs(
        row["context"]
    )
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    restored = _with_required_assets(ctx, handler().key)
    assert restored["normalized_content"]["assets"][0]["asset_id"] == uid
    assert not handler().diagram_specs(restored)


def test_three_row_source_checks_the_extra_square_zero_even_if_other_rows_match():
    row = ROWS[1]
    ctx = deepcopy(row["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace(
        "x^{2}+4x+4", r"x^2-\frac{4}{5}x+\frac{4}{25}"
    )
    a = analyze(read_formula(ctx)[1])
    original = analyze(read_formula(row["context"])[1])
    uid = ctx["normalized_content"]["assets"][0]["asset_id"]
    assert signature(a.stage) == signature(original.stage)
    assert signature(a.other_stage) == signature(original.other_stage)
    assert a.square_stage.points == (sp.Rational(2, 5),)
    assert not compatible(SOURCES["figures"][uid], a)
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_two_row_source_does_not_depend_on_the_unplotted_square_zero():
    row = ROWS[0]
    ctx = deepcopy(row["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace(
        "x^{2}-2x+1", r"x^2+\frac{2}{3}x+\frac{1}{9}"
    )
    a = analyze(read_formula(ctx)[1])
    original = analyze(read_formula(row["context"])[1])
    uid = ctx["normalized_content"]["assets"][0]["asset_id"]
    assert (
        signature(a.stage) == signature(original.stage)
        and a.square_stage.points != original.square_stage.points
    )
    assert (
        compatible(SOURCES["figures"][uid], a) and uid in plan(row, ctx).solution_html
    )


def test_generated_parent_size_chart_has_fraction_label_two_sign_rows_and_full_intersection():
    row = ROWS[-1]
    specs = handler().diagram_specs(row["context"])
    assert len(specs) == 1
    root = ET.fromstring(specs[0]["svg_text"])
    ns = {"s": "http://www.w3.org/2000/svg"}
    groups = {g.get("data-row"): g for g in root.findall("s:g", ns)}
    assert root.get("viewBox") == "0 0 253.1598 93.5393"
    assert [
        (c.get("data-boundary"), c.get("fill"))
        for c in groups["stage"].findall("s:circle", ns)
    ] == [("-2", "#FFFFFF"), ("4/5", "#000000"), ("1", "#FFFFFF")]
    assert [
        (c.get("data-boundary"), c.get("fill"))
        for c in groups["domain"].findall("s:circle", ns)
    ] == [("-1", "#000000"), ("0", "#000000")]
    assert [
        int(t.get("data-sign"))
        for t in groups["stage"].findall("s:text", ns)
        if t.get("data-sign")
    ] == [-1, 1, -1, 1]
    assert [
        int(t.get("data-sign"))
        for t in groups["domain"].findall("s:text", ns)
        if t.get("data-sign")
    ] == [1, -1, 1]
    assert [r.get("data-intersection") for r in root.findall("s:rect", ns)] == [
        "Interval.Lopen(-2, -1)",
        "Interval(0, 4/5)",
        "Interval.open(1, oo)",
    ]
    fraction_circle = next(
        c
        for c in groups["stage"].findall("s:circle", ns)
        if c.get("data-boundary") == "4/5"
    )
    labels = [
        t
        for t in groups["stage"].findall("s:text", ns)
        if t.get("x") == fraction_circle.get("cx") and not t.get("data-sign")
    ]
    assert max(float(t.get("y")) for t in labels) < float(fraction_circle.get("cy")) - 5
    guides = [float(line.get("x1")) for line in root.findall("s:line", ns)]
    assert all(
        abs(float(t.get("x")) - x) >= 12
        for g in groups.values()
        for t in g.findall("s:text", ns)
        if t.get("data-sign")
        for x in guides
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_is_ignored_and_parent_identity_is_required(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), MANUAL[row["task"]][-1])
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_key", "wrong"),
        ("kind", None),
        ("url", "/wrong"),
        ("asset_id", "unknown"),
    ],
)
def test_native_chart_requires_complete_verified_metadata(field, value):
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{x^2}-\sqrt{x^2+x}\le0",
        r"\frac{\sqrt{x^2}+\sqrt{x^2+x}}{x^2+x-1}\le0",
        r"\frac{\sqrt{x^2}-\sqrt{x^2+x}+1}{x^2+x-1}\le0",
        r"\frac{\sqrt{x^2}-\sqrt{x^2+x}}{x^2+x-1}\ge0",
        r"\frac{\sqrt{x^2}-\sqrt{x^2+x}}{x^2+x-1}\le1",
        r"\frac{\sqrt{x^2+1}-\sqrt{x^2+x}}{x^2+x-1}\le0",
        r"\frac{\sqrt{x^2}-\sqrt{2*x^2+x}}{x^2+x-1}\le0",
        r"\frac{\sqrt{x^2}-\sqrt{x^2+x}}{x-1}\le0",
    ],
)
def test_complete_difference_shape_original_radicands_and_comparison_are_required(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)
