"""Native common-denominator identities, cancelled poles and isolated double zeros."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_rational_inequality import answer_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.rational_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read
from solution_runner.pipelines.equations.rational_inequality_methods import prepare
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("rational_inequality_polynomial_sources.json")
    .read_text()
)
METHODS = {
    "508360": "quadratic_right",
    "508381": "cubic_cancel",
    "530674": "quadratic_denominators",
    "621777": "square_zero",
}


def handler(row):
    return get_handler(
        "exam-rational-inequality-" + METHODS[row["group"]].replace("_", "-")
    )


def parent(row):
    return next(
        s["html"]
        for r in SOURCES
        if r["task"] == row["group"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(row, ctx):
    h = handler(row)
    ctx = _with_required_assets(ctx, h.key)
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
            ctx, parent_solution_html=parent(row), generated_solution_assets=generated
        )
    )


def expected(row):
    text = (
        row["expected_answer"]
        .replace(r"\left", "")
        .replace(r"\right", "")
        .replace(r"\cdot", "")
        .replace(",", ";")
    )
    return answer_set(text)


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_answers_independent_cas_and_every_displayed_identity(row):
    a = read(row["context"])[1]
    relation = {"<=": sp.Le, ">=": sp.Ge}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.original, 0), X, relational=False
    ) - sp.FiniteSet(*a.poles)
    assert a.solution == independent == expected(row)
    identities, steps = prepare(a, METHODS[row["group"]])
    assert not identities
    for step in steps:
        assert sp.cancel(RationalParser(step.text).parse().value - a.original) == 0
    assert answer_set(plan(row, row["context"]).answer) == independent


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_replay_and_preparation_never_write_or_mutate_the_condition(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    assert ctx == row["context"]
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    for asset in ctx["normalized_content"].get("assets", []):
        assert asset["asset_id"] in p.solution_html
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == p.answer and record["transformations"] == list(
        p.transformations
    )
    assert len(gateway.reads) == 1 and gateway.ctx == ctx
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("task,pole", [("530674", -8), ("515745", 7), ("530694", 18)])
def test_common_factor_cancellation_never_fills_the_original_hole(task, pole):
    row = next(r for r in SOURCES if r["task"] == task)
    a = read(row["context"])[1]
    assert a.holes == (pole,) and pole not in a.solution
    left = sp.simplify(a.expression.subs(X, pole - sp.Rational(1, 100)))
    right = sp.simplify(a.expression.subs(X, pole + sp.Rational(1, 100)))
    assert sp.sign(left) == sp.sign(right)
    assert (
        "Сокращение общего множителя сохраняет"
        in plan(row, row["context"]).solution_html
    )


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] == "621777"], ids=lambda r: r["task"]
)
def test_double_zero_is_retained_as_an_isolated_solution(row):
    a = read(row["context"])[1]
    assert sp.FiniteSet(0) in a.solution.args
    assert (
        sp.Rational(1, 100) not in a.solution and -sp.Rational(1, 100) not in a.solution
    )
    assert r"\{0\}" in plan(row, row["context"]).answer
    assert "Дублирует" not in plan(row, row["context"]).solution_html
    assert not handler(row).diagram_specs(row["context"])


def test_compatible_quadratic_chart_is_restored_exactly_without_a_duplicate():
    row = next(r for r in SOURCES if r["task"] == "508361")
    h = handler(row)
    assert not h.diagram_specs(row["context"])
    assert (
        h.asset_requirements(row["context"])[0]["source_asset_id"]
        == "15f28735-0d45-436e-a0c0-4ea321a558cb"
    )
    assert (
        "15f28735-0d45-436e-a0c0-4ea321a558cb"
        in plan(row, row["context"]).solution_html
    )


@pytest.mark.parametrize(
    "task,points,closed,signs",
    [
        ("508362", ["0", "2", "3"], {"0", "2"}, [-1, 1, -1, 1]),
        ("511523", ["0", "4/3", "3"], {"4/3", "3"}, [-1, 1, -1, 1]),
    ],
)
def test_changed_required_chart_uses_current_roots_and_open_denominator(
    task, points, closed, signs
):
    row = next(r for r in SOURCES if r["task"] == task)
    (spec,) = handler(row).diagram_specs(row["context"])
    root = ET.fromstring(spec["svg_text"])
    marks = [n for n in root.iter() if n.get("data-boundary")]
    assert [m.get("data-boundary") for m in marks] == points
    assert {
        m.get("data-boundary") for m in marks if m.get("fill") == "#000000"
    } == closed
    assert [int(n.get("data-sign")) for n in root.iter() if n.get("data-sign")] == signs


@pytest.mark.parametrize(
    "formula,method",
    [
        (r"\frac{x^3}{x-1}\le x", "quadratic_right"),
        (r"x^2-\frac{x^2+1}{x-1}\le0", "cubic_cancel"),
        (r"x^3+\frac{x^2+x+1}{x-1}\le0", "square_zero"),
        (r"\frac{1}{x^2-1}+\frac{1}{x^2-4}\ge0", "quadratic_denominators"),
    ],
)
def test_unproved_polynomial_shapes_fail_closed(formula, method):
    with pytest.raises(UnsupportedCondition):
        prepare(analyze(formula), method)


def test_changed_optional_source_layout_is_rejected_until_its_adaptation_is_reviewed():
    row = next(r for r in SOURCES if r["task"] == "508423")
    ctx = deepcopy(row["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    section["html"] = section["html"].replace("28x", "29x")
    with pytest.raises(UnsupportedCondition, match="exact reuse only"):
        plan(row, ctx)
