"""Two exact quadratic branches, union charts and read-only preparation."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
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
from solution_runner.pipelines.equations.absolute_inequality import analyze
from solution_runner.pipelines.equations.absolute_quadratic_figures import (
    SOURCES,
    compatible,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("absolute_quadratic_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "508433": (
        2 * X**2 + sp.Rational(19, 8) * X - sp.Rational(1, 8),
        3 * X**2 + X / 8 - sp.Rational(19, 8),
        (sp.Interval(-sp.Rational(3, 4), 3), sp.Interval(-1, sp.Rational(1, 2))),
        sp.Interval(-1, 3),
    ),
    "508435": (
        X**2 - sp.Rational(29, 12) * X - sp.Rational(35, 12),
        2 * X**2 - sp.Rational(61, 12) * X - sp.Rational(19, 12),
        (sp.Interval(sp.Rational(2, 3), 2), sp.Interval(-sp.Rational(1, 2), 3)),
        sp.Interval(-sp.Rational(1, 2), 3),
    ),
    "511529": (
        X**2 + sp.Rational(4, 3) * X - sp.Rational(13, 6),
        2 * X**2 + sp.Rational(8, 3) * X - sp.Rational(11, 6),
        (sp.Interval(-1, -sp.Rational(1, 3)), sp.Interval(-2, sp.Rational(2, 3))),
        sp.Interval(-2, sp.Rational(2, 3)),
    ),
}


def handler():
    return get_handler(get_group_profile("508433").content_rule_key)


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
def test_manual_answers_independent_polynomial_oracles_and_original_values(row):
    a = analyze(read_formula(row["context"])[1], "quadratic_comparison")
    P, Q, branches, expected = MANUAL[row["task"]]
    assert a.argument == P and a.bound == Q and not a.poles
    assert tuple(s.solution for s in a.branches) == branches
    oracle = sp.solve_univariate_inequality(P >= Q, X, relational=False).union(
        sp.solve_univariate_inequality(-P >= Q, X, relational=False)
    )
    same_set(a.solution, oracle)
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    for point in [sp.Rational(i, 8) for i in range(-40, 41)] + [
        p for b in branches for p in (b.start, b.end)
    ]:
        assert bool(a.solution.contains(point)) == bool(
            abs(P.subs(X, point)) >= Q.subs(X, point)
        )
    assert a.solution.contains(0) and Q.subs(X, 0) < 0


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_order_readonly_exact_native_reuse_and_idempotence(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == before
    assert (
        p.solution_html.index("совокупности")
        < p.solution_html.index("старший коэффициент")
        < p.solution_html.index("<img ")
        < p.solution_html.index("множители")
        < p.solution_html.index("Объединяя")
    )
    assert p.solution_html.count("<img ") == 1
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
    assert record["status"] == "prepared" and record["transformations"] == list(
        p.transformations
    )
    assert gateway.reads == [ctx["problem_id"]]
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    for asset in before["normalized_content"]["assets"]:
        assert (
            asset in ctx["normalized_content"]["assets"]
            and asset["asset_id"] in p.solution_html
        )
    assert len(handler().diagram_specs(before)) == (1 if row["task"] == "508435" else 0)


@pytest.mark.parametrize("row", [ROWS[0], ROWS[2]], ids=lambda r: r["task"])
def test_exact_certified_native_is_restored_and_all_branch_signs_are_checked(row):
    a = analyze(read_formula(row["context"])[1], "quadratic_comparison")
    uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = SOURCES["figures"][uid]
    assert compatible(entry, a)
    import solution_runner.pipelines.equations.absolute_quadratic_figures as figures

    svg = Path(figures.__file__).parent / "assets/absolute-inequalities" / f"{uid}.svg"
    assert hashlib.sha256(svg.read_bytes()).hexdigest() == entry["sha256"]
    for field in ("branches", "union"):
        changed = deepcopy(entry)
        if field == "branches":
            changed[field][1]["signs"] = [-1, 1, -1]
        else:
            changed[field] = "Interval(0,1)"
        assert not compatible(changed, a)
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    restored = _with_required_assets(ctx, handler().key)
    assert restored["normalized_content"]["assets"][0]["asset_id"] == uid
    assert not handler().diagram_specs(restored)


def test_generated_chart_shows_union_containing_smaller_branch_and_fraction_margins():
    (spec,) = handler().diagram_specs(ROWS[1]["context"])
    assert spec["sha256"] == hashlib.sha256(spec["svg_text"].encode()).hexdigest()
    root = ET.fromstring(spec["svg_text"])
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.get("viewBox") == "0 0 194.431 104.525"
    groups = {g.get("data-row"): g for g in root.findall("s:g", ns)}
    assert set(groups) == {"first", "second"}
    assert [r.get("data-union") for r in root.findall("s:rect", ns)] == [
        "Interval(-1/2, 3)"
    ]
    for name, points in [("first", ["2/3", "2"]), ("second", ["-1/2", "3"])]:
        g = groups[name]
        assert [c.get("data-boundary") for c in g.findall("s:circle", ns)] == points
        assert all(c.get("fill") == "#000000" for c in g.findall("s:circle", ns))
        assert [
            int(t.get("data-sign"))
            for t in g.findall("s:text", ns)
            if t.get("data-sign")
        ] == [1, -1, 1]
        fraction = g.findall("s:circle", ns)[0]
        labels = [
            t
            for t in g.findall("s:text", ns)
            if t.get("x") == fraction.get("cx") and not t.get("data-sign")
        ]
        y = [float(t.get("y")) for t in labels]
        assert min(y) > 10 and max(y) < 104
        assert (
            (max(y) < float(fraction.get("cy")) - 5)
            if name == "first"
            else (min(y) > float(fraction.get("cy")) + 5)
        )
    rect = root.find("s:rect", ns)
    outer = groups["second"].findall("s:circle", ns)
    assert float(rect.get("x")) == float(outer[0].get("cx"))
    assert float(rect.get("x")) + float(rect.get("width")) == float(outer[1].get("cx"))


@pytest.mark.parametrize(
    "formula",
    [
        r"|x^2-1|>x^2-2",
        r"|x^2-1|\le2*x^2-2",
        r"|x-1|\ge2*x^2-2",
        r"|x^2-1|+1\ge2*x^2-2",
        r"|x^2-1|\ge|2*x^2-2|",
        r"|x^2-1|\ge-x^2-2",
        r"|x^2-1|\ge2*x^2+2",
        r"|x^2-1+\frac{x}{x}-1|\ge2*x^2-2",
    ],
)
def test_wrong_whole_shape_strictness_branches_and_hidden_poles_are_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula, "quadratic_comparison")


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_ignored_parent_and_asset_mismatch_rejected(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), MANUAL[row["task"]][-1])
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель</p>")
    if ctx["normalized_content"]["assets"]:
        ctx["normalized_content"]["assets"][0]["asset_id"] = "unreviewed"
        with pytest.raises(UnsupportedCondition):
            plan(row, ctx)


def test_generated_chart_hash_must_match_current_mathematics():
    ctx = ROWS[1]["context"]
    (spec,) = handler().diagram_specs(ctx)
    generated = (
        {**spec, "sha256": "0" * 64, "source_asset_id": "bad", "url": "/assets/bad"},
    )
    with pytest.raises(UnsupportedCondition):
        handler().plan(
            PlanInput(
                ctx, parent_solution_html=PARENT, generated_solution_assets=generated
            )
        )
