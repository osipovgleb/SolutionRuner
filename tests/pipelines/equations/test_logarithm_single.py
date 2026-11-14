"""Original logarithms, canceled exclusions and parent-specific presentations."""

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
from solution_runner.pipelines.equations.logarithm_single_rationalization import analyze
from solution_runner.pipelines.equations.logarithm_single_svg import boundaries, render
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_single_sources.json")
    .read_text()
)
PARENTS = {
    r["group"]: next(
        s["html"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for r in ROWS
    if r["task"] == r["group"]
}
MANUAL = {
    "507258": ((25 - X**2) / 16, (24 + 2 * X - X**2) / 14, 1),
    "508521": (6 * X**2 - X - 1, 2 * X**2 - 5 * X + 3, 0),
    "508523": (6 * X**2 + 5 * X, 2 * X**2 - 3 * X + 1, 0),
    "511562": (6 * X**2 + X - 1, 3 * X**2 - 7 * X + 3, 0),
    "508492": (X / 3, 3 * X**2 - 2 * X + 1, 0),
    "508494": (X / 2, 4 * X**2 - 3 * X + 1, 0),
    "511553": (X / 4, 4 * X**2 - 2 * X + 1, 0),
    "514728": (X / 2, (X - 1) ** 2, 2),
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def plan(row, context=None, parent=None):
    h = handler(row)
    ctx = _with_required_assets(row["context"] if context is None else context, h.key)
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
            ctx,
            parent_solution_html=PARENTS[row["group"]] if parent is None else parent,
            generated_solution_assets=generated,
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_domain_and_both_rationalizations(row):
    a = analyze(read_formula(row["context"])[1])
    G, A, k = MANUAL[row["task"]]
    assert sp.cancel(a.G - G) == sp.cancel(a.A - A) == 0 and a.bound == k
    assert a.operator == (">" if row["task"] == "507258" else ">=")
    domain = sp.Intersection(
        *(
            sp.solve_univariate_inequality(expr > 0, X, relational=False)
            for expr in (G, A)
        )
    ) - sp.solveset(G - 1, X, domain=sp.S.Reals)
    same_set(a.domain, domain)
    same_set(a.solution, answer_set(row["expected_answer"]))
    for stage in (a.product, a.quotient):
        same_set(stage.solution.intersect(domain), a.solution)
    for point in [sp.Rational(n, 12) for n in range(-72, 85)]:
        if domain.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        value = sp.log(A.subs(X, point)) / sp.log(G.subs(X, point)) - k
        value = sp.N(sp.simplify(value), 45)
        expected = value > 0 if a.operator == ">" else value >= 0
        assert bool(a.solution.contains(point)) == bool(expected)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_and_idempotent_replay(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
    assert ctx == original
    same_set(answer_set(p.answer), answer_set(row["expected_answer"]))
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=PARENTS[row["group"]],
    )
    assert record["status"] == "prepared"
    assert record["transformations"] == list(p.transformations)
    assert gateway.reads == [ctx["problem_id"]]
    assert p.solution_html.count("<img ") == (1 if row["group"] == "507258" else 0)
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    assert all(
        asset in ctx["normalized_content"]["assets"]
        for asset in original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize(
    "row", [r for r in ROWS if r["group"] == "507258"], ids=lambda r: r["task"]
)
def test_two_chart_rows_and_original_asset_reuse(row):
    specs = handler(row).diagram_specs(row["context"])
    assert len(specs) == (0 if row["task"] == row["group"] else 1)
    a = analyze(read_formula(row["context"])[1])
    root = ET.fromstring(render(a))
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.get("viewBox") == "0 0 500 155"
    groups = {g.get("data-row"): g for g in root.findall("s:g", ns)}
    for key, points, solution in [
        ("stage", a.product.points, a.product.solution),
        ("domain", boundaries(a.domain), a.domain),
    ]:
        circles = groups[key].findall("s:circle", ns)
        assert {c.get("data-boundary") for c in circles} == {str(p) for p in points}
        for c in circles:
            point = next(p for p in points if str(p) == c.get("data-boundary"))
            assert c.get("fill") == (
                "#000000" if solution.contains(point) is sp.true else "#FFFFFF"
            )
            assert 0 < float(c.get("cx")) < 484
    assert [
        int(t.get("data-sign"))
        for t in groups["stage"].findall("s:text", ns)
        if t.get("data-sign")
    ] == list(a.product.signs)
    assert all(0 <= float(t.get("y")) < 155 for t in root.findall(".//s:text", ns))
    if not specs:
        uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
        assert uid in plan(row).solution_html
        assert not any(
            t["transformation_target_id"].startswith("asset:")
            for t in plan(row).transformations
        )


def test_canceled_unit_base_and_zero_argument_are_still_excluded():
    row = next(r for r in ROWS if r["task"] == "514728")
    a = analyze(read_formula(row["context"])[1])
    assert sp.cancel(a.quotient.original - (3 * X - 2) / 2) == 0
    assert a.solution.contains(sp.Rational(2, 3)) is sp.true
    assert all(a.solution.contains(p) is sp.false for p in (1, 2))
    assert "Положительность аргумента учитываем строго" in plan(row).solution_html


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_unreviewed_parent_and_saved_answer_guard(row):
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой метод.</p>")
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), answer_set(row["expected_answer"]))


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_x(x+1)+x\ge0",
        r"\log_x(x+1)\ge3",
        r"\log_x(x+1)\ge\log_x(x+2)",
        r"\log_x(x^3+1)\ge0",
    ],
)
def test_complete_reviewed_shape_is_required(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)
