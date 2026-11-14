"""Check complete nested sources, exact root labels and strict variable scope."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_scalar import enclose
from solution_runner.pipelines.equations.logarithm_inequality_planner import (
    build_context_repair_plan,
)
from solution_runner.pipelines.equations.logarithm_nested_inequality import analyze
from solution_runner.pipelines.equations.logarithm_quadratic_inequality import (
    analyze as old_quadratic,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_nested_inequality_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for row in ROWS
    if row["group"] == row["task"]
    for s in row["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
BASE = r"\log_2^2(-\log_2 x)+\log_2\log_2^2 x\le3"
EXPECTED = {
    "508469": sp.Interval(sp.Rational(1, 4), 2 ** (-sp.Rational(1, 8))),
    "508470": sp.Interval(sp.Rational(1, 9), 3 ** (-sp.Rational(1, 8))),
    "511546": sp.Interval(sp.Rational(1, 4), 2 ** (-sp.Rational(1, 32))),
}


def handler():
    return get_handler(get_group_profile("508469").content_rule_key)


def plan(ctx, parent=PARENT):
    return handler().plan(PlanInput(ctx, parent_solution_html=parent))


def model(row):
    return analyze(read_formula(row["context"])[1])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_sources_manual_sets_exact_root_answers_and_quadratic_cas(row):
    a = model(row)
    q = a.quadratic
    same_set(a.solution, EXPECTED[row["task"]])
    assert re.sub(r"\s+", "", a.answer) == re.sub(
        r"\s+", "", row["expected_answer"].strip().removesuffix(".")
    )
    p = (
        X**2
        + (4 if row["task"] == "511546" else 2) * X
        - (5 if row["task"] == "511546" else 3)
    )
    same_set(
        q.stage.solution, sp.solve_univariate_inequality(p <= 0, X, relational=False)
    )
    assert q.domain == sp.Interval.open(-sp.oo, 0) and a.solution.is_subset(
        sp.Interval.open(0, 1)
    )
    assert a.inner_base == (3 if row["task"] == "508470" else 2)
    assert a.original_outer_base == (
        sp.Rational(1, 2) if row["task"] == "508470" else 2
    )
    assert q.base == 2 and q.solution == sp.Interval(
        -2, -sp.Rational(1, 32 if row["task"] == "511546" else 8)
    )
    assert plan(row["context"]).answer == a.answer


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_nested_logarithms_numerically_include_domains_and_exact_endpoints(
    row,
):
    a = model(row)
    inner_base, outer_base, coefficient, right = {
        "508469": (2, sp.Integer(2), 1, 3),
        "508470": (3, sp.Rational(1, 2), -1, 3),
        "511546": (2, sp.Integer(2), 2, 5),
    }[row["task"]]
    points = (
        -1,
        0,
        1,
        2,
        sp.Rational(1, 16),
        sp.Rational(1, 9),
        sp.Rational(1, 4),
        sp.Rational(1, 2),
        sp.Rational(3, 4),
        sp.Rational(9, 10),
        sp.Rational(99, 100),
        EXPECTED[row["task"]].start,
        EXPECTED[row["task"]].end,
    )
    for point in points:
        if not 0 < point < 1:
            assert a.solution.contains(point) is sp.false
            continue
        inner = sp.simplify(sp.expand_log(sp.log(point)) / sp.log(inner_base))
        first = sp.log(-inner) / sp.log(outer_base)
        second = sp.log(inner**2) / sp.log(outer_base)
        direct = sp.N(
            sp.simplify(sp.expand_log(first**2 + coefficient * second - right)), 50
        )
        assert bool(a.solution.contains(point)) == bool(direct <= 0)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_conditions_no_assets_parent_method_and_idempotence(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(ctx)
    assert (
        ctx == before
        and not handler().diagram_specs(ctx)
        and "<img " not in p.solution_html
    )
    assert "модуль" in p.solution_html and "z=" in p.solution_html
    assert "порядок границ" in p.solution_html
    if row["task"] == "508470":
        assert "квадрат остаётся прежним" in p.solution_html
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
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
    assert not plan(ctx).transformations


def test_exact_root32_presentation_does_not_widen_the_scalar_grammar():
    a = model(next(row for row in ROWS if row["task"] == "511546"))
    assert a.endpoint(a.solution.end) == r"\frac{1}{\sqrt[32]{2}}"
    assert sp.simplify(a.solution.end**32 - sp.Rational(1, 2)) == 0
    with pytest.raises(UnsupportedCondition):
        enclose(a.solution.end)
    with pytest.raises(UnsupportedCondition):
        a.endpoint(sp.Integer(2))
    with pytest.raises(UnsupportedCondition):
        old_quadratic(BASE)


def test_strict_boundaries_and_reviewed_inverse_root_limit():
    a = analyze(BASE.replace(r"\le", r"\lt"))
    same_set(a.solution, sp.Interval.open(sp.Rational(1, 4), 2 ** (-sp.Rational(1, 8))))
    at_limit = analyze(r"\log_2^2(-\log_2 x)+\frac{7}{2}\log_2\log_2^2 x\le8")
    assert at_limit.quadratic.solution.end == -sp.Rational(1, 256)
    assert at_limit.endpoint(at_limit.solution.end) == r"\frac{1}{\sqrt[256]{2}}"
    with pytest.raises(UnsupportedCondition):
        analyze(r"\log_7^2(-\log_2 x)+\log_7\log_2^2 x\le3")


@pytest.mark.parametrize(
    "formula",
    [
        BASE.replace(r"\le3", r"+x\le3"),
        BASE.replace(r"\log_2 x", r"\log_2(x+1)", 1),
        BASE.replace(r"\log_2^2 x", r"\log_3^2 x"),
        BASE.replace(r"+\log_2\log_2", r"+\log_3\log_2"),
        BASE.replace("^2(-", "^2("),
        BASE.replace(r"\log_2", r"\log_{(0{,}5)}"),
        BASE.replace(r"\log_2^2(-", r"\log_x^2(-"),
        BASE.replace(r"\log_2^2 x", r"\log_2^3 x"),
        BASE.replace(r"\le3", r"\ge3"),
        r"\log_2^2(-\log_2 x)+4\log_2\log_2^2 x\le9",
        BASE.replace(r"\log_2^2(-", r"\log_2^3(-"),
    ],
)
def test_incomplete_or_unreviewed_nested_grammar_fails_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_cancelled_original_variable_poles_cannot_hide_behind_the_inner_placeholder():
    formula = BASE.replace(
        r"-\log_2 x)", r"-\log_2 x+\frac{x-\frac{1}{2}}{x-\frac{1}{2}}-1)"
    )
    assert formula != BASE
    with pytest.raises(UnsupportedCondition, match="original variable"):
        analyze(formula)


def test_pinned_parent_presentation_unknown_assets_and_answer_independence():
    ctx = deepcopy(ROWS[0]["context"])
    with pytest.raises(UnsupportedCondition):
        plan(ctx, PARENT + "changed")
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(ctx, parent_solution_html=PARENT, method="quadratic")
    expected = plan(ctx).answer
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>wrong</p>"
    assert plan(ctx).answer == expected
    ctx["normalized_content"]["assets"] = [{"asset_id": "foreign"}]
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
