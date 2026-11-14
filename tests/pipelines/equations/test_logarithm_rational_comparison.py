"""Check complete rational comparison groups and the implied cubic domain."""

import json
from copy import deepcopy
from pathlib import Path

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
from solution_runner.pipelines.equations.logarithm_power_quotient import (
    analyze as power,
)
from solution_runner.pipelines.equations.logarithm_product_inequality import (
    analyze as quotient,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_rational_comparison_sources.json")
    .read_text()
)
PARENTS = {
    r["group"]: next(
        s["html"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for r in ROWS
    if r["group"] == r["task"]
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def model(row):
    formula = read_formula(row["context"])[1]
    return (
        power(formula)
        if row["method"] == "power_quotient"
        else quotient(formula, method="quotient")
    )


def plan(row, ctx=None, parent=None):
    return handler(row).plan(
        PlanInput(
            _with_required_assets(
                row["context"] if ctx is None else ctx, handler(row).key
            ),
            parent_solution_html=PARENTS[row["group"]] if parent is None else parent,
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_complete_sources_match_manual_answers_and_original_log_values(row):
    a = model(row)
    same_set(a.solution, answer_set(row["expected_answer"]))
    A, B, C = a.arguments
    for point in (
        -24,
        -12,
        -6,
        -4,
        -3,
        -1,
        sp.Rational(1, 8),
        sp.Rational(1, 5),
        sp.Rational(1, 4),
        sp.Rational(1, 2),
        1,
        2,
        3,
        4,
        10,
        24,
    ):
        values = [v.subs(X, point) for v in (A, B, C)]
        if any(
            v.is_real is not True or v.is_finite is not True or v <= 0 for v in values
        ):
            assert a.solution.contains(point) is sp.false
            continue
        coefficient = 2 if row["method"] == "power_quotient" else 1
        original = (
            coefficient * sp.log(values[0]) / sp.log(a.base)
            - sp.log(values[1]) / sp.log(a.base)
            - sp.log(values[2]) / sp.log(a.base)
        )
        original = sp.simplify(sp.expand_log(original))
        v = sp.N(original, 50)
        expected = {"<": v < 0, "<=": v <= 0, ">": v > 0, ">=": v >= 0}[a.operator]
        assert bool(a.solution.contains(point)) == bool(expected)
    same_set(a.full_stage.solution.intersect(a.domain), a.solution)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_runtime_is_readonly_idempotent_and_retains_every_original_asset(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == before
    same_set(answer_set(p.answer), answer_set(row["expected_answer"]))
    assert not handler(row).diagram_specs(ctx)
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=PARENTS[row["group"]],
    )
    assert record["status"] == "prepared" and record["transformations"] == list(
        p.transformations
    )
    assert gateway.reads == [ctx["problem_id"]]
    replay(ctx, p.transformations)
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize(
    "row", [r for r in ROWS if r["method"] == "power_quotient"], ids=lambda r: r["task"]
)
def test_original_denominators_and_constructive_right_argument_positivity(row):
    a = model(row)
    A, B, C = a.arguments
    left = sp.cancel(A**2 / B)
    assert a.domain.is_subset(
        sp.solve_univariate_inequality(left > 0, X, relational=False)
    )
    n, d = sp.fraction(sp.cancel(C - left))
    assert sp.degree(n, X) == 3
    assert a.domain.is_subset(
        sp.solve_univariate_inequality(d > 0, X, relational=False)
    )
    assert 0 in a.argument_holes and a.domain.contains(0) is sp.false
    html = plan(row).solution_html
    assert "положительность правого аргумента" in html


@pytest.mark.parametrize(
    "row",
    [r for r in ROWS if r["context"]["normalized_content"]["assets"]],
    ids=lambda r: r["task"],
)
def test_exact_reviewed_two_row_charts_are_reused_without_duplicates(row):
    p = plan(row)
    uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    assert p.solution_html.count('data-asset-id="' + uid + '"') == 1
    if row["method"] == "power_quotient":
        ctx = deepcopy(row["context"])
        ctx["normalized_content"]["assets"] = []
        for section in ctx["normalized_content"]["sections"]:
            if section["key"] == "solution":
                section["asset_keys"] = []
                section["html"] = "<p>Прежнее решение.</p>"
        prepared = plan(row, ctx)
        assert uid in prepared.solution_html


def test_same_answer_does_not_make_a_different_stage_chart_compatible():
    row = next(r for r in ROWS if r["task"] == "520908")
    ctx = deepcopy(row["context"])
    other = next(r for r in ROWS if r["task"] == "701888")
    ctx["normalized_content"]["assets"] = deepcopy(
        other["context"]["normalized_content"]["assets"]
    )
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_cancelled_original_right_argument_hole_is_not_lost():
    formula = r"2\log_7(x\sqrt{2})-\log_7(\frac{x}{1-x})\le\log_7(8x^2+\frac{1}{x}-5+\frac{x-2}{x-2}-1)"
    a = power(formula)
    assert 2 in a.argument_holes
    formula = r"2\log_7(x\sqrt{2})-\log_7(\frac{x}{1-x})\le\log_7(8x^2+\frac{1}{x}-5+\frac{5x-1}{5x-1}-1)"
    a = power(formula)
    assert a.solution.contains(sp.Rational(1, 5)) is sp.false


@pytest.mark.parametrize(
    "formula",
    [
        r"2\log_7(x\sqrt{2})-\log_7(\frac{x}{1-x})\ge\log_7(8x^2+\frac{1}{x}-5)",
        r"2\log_{(0.5)}(x\sqrt{2})-\log_{(0.5)}(\frac{x}{1-x})\le\log_{(0.5)}(8x^2+\frac{1}{x}-5)",
        r"3\log_7(x\sqrt{2})-\log_7(\frac{x}{1-x})\le\log_7(8x^2+\frac{1}{x}-5)",
        r"2\log_7(x\sqrt{2})-\log_3(\frac{x}{1-x})\le\log_7(8x^2+\frac{1}{x}-5)",
        r"2\log_7(x\sqrt{2})-\log_7(\frac{x}{1-x})\le\log_7(8x^2+\frac{1}{x}-5)+x",
    ],
)
def test_unreviewed_monotonicity_coefficient_base_and_external_variable_are_rejected(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        power(formula)


@pytest.mark.parametrize("group", ["520804", "520908"])
def test_parent_identity_and_saved_answer_are_not_used_to_compute_the_solution(group):
    row = next(r for r in ROWS if r["group"] == group and r["task"] != group)
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), model(row).solution)
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")


def test_quadratic_middle_argument_extension_requires_positivity_everywhere():
    row = next(r for r in ROWS if r["task"] == "520804")
    formula = read_formula(row["context"])[1].replace("x^{2}-x+12", "x^{2}-1")
    with pytest.raises(UnsupportedCondition, match="everywhere positive quadratic"):
        quotient(formula, method="quotient")
