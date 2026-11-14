"""Whole product identity, signed logarithm bound and original equality-point holes."""

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exponential_log_bound import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_log_bound_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {"484588": (7, 2, 3), "507652": (5, 2, 2), "511461": (6, 3, 3)}


def handler():
    return get_handler(get_group_profile("484588").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_three_manual_answers_original_domain_and_values_on_both_log_signs(row):
    a = analyze(read_formula(row["context"])[1])
    base, log_base, center = MANUAL[row["task"]]
    assert (a.base, a.log_base, a.center) == (base, log_base, center)
    assert sp.expand(a.argument - (log_base - (X - center) ** 2)) == 0
    expected_domain = sp.Interval.open(
        center - sp.sqrt(log_base), center + sp.sqrt(log_base)
    )
    same_set(a.domain, expected_domain)
    same_set(a.solution, sp.FiniteSet(center))
    same_set(answer_set(plan(row).answer), sp.FiniteSet(center))
    saw_negative_log = False
    saw_positive_log = False
    for point in [
        sp.Rational(i, 10) for i in range(10 * (center - 2), 10 * (center + 2) + 1)
    ]:
        argument = a.argument.subs(X, point)
        if argument <= 0:
            assert not a.domain.contains(point) and not a.solution.contains(point)
            continue
        value = math.log(float(argument), log_base)
        product = base ** (-abs(float(point - center))) * value
        saw_negative_log |= value < 0
        saw_positive_log |= value > 0
        assert product <= 1 + 1e-12
        assert bool(a.solution.contains(point)) == (abs(product - 1) < 1e-12)
    assert saw_negative_log and saw_positive_log
    assert all(not a.domain.contains(p) for p in expected_domain.boundary)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_bounds_order_sign_justification_readonly_unchanged_input_and_replay(
    row,
):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == before
        and "<img" not in p.solution_html
        and not handler().diagram_specs(ctx)
    )
    assert (
        p.solution_html.index("области определения")
        < p.solution_html.index("Показатель степени")
        < p.solution_html.index("Выделим квадрат")
        < p.solution_html.index("Если логарифм неположителен")
        < p.solution_html.index("равенстве обоих множителей")
    )
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
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


def test_affine_modulus_scaling_has_the_same_exact_bound_and_equality_method():
    a = analyze(r"3^{-|2x-1|}\cdot\log_4(4-(2x-1)^2)\ge1")
    assert a.solution == sp.FiniteSet(sp.Rational(1, 2))
    same_set(a.domain, sp.Interval.open(-sp.Rational(1, 2), sp.Rational(3, 2)))


def test_hidden_log_argument_pole_at_the_equality_point_removes_the_only_candidate():
    a = analyze(r"7^{-|x-3|}\cdot\log_2(6x-x^2-7+\frac{x-3}{x-3}-1)\ge1")
    assert a.solution == sp.EmptySet and a.poles == (3,) and not a.domain.contains(3)


def test_hidden_absolute_argument_pole_at_the_equality_point_is_also_retained():
    a = analyze(r"7^{-|x-3+\frac{x-3}{x-3}-1|}\cdot\log_2(6x-x^2-7)\ge1")
    assert a.solution == sp.EmptySet and a.poles == (3,)


def test_an_unrelated_hidden_pole_does_not_remove_the_valid_equality_point():
    a = analyze(r"7^{-|x-3|}\cdot\log_2(6x-x^2-7+\frac{x-2}{x-2}-1)\ge1")
    assert (
        a.solution == sp.FiniteSet(3) and a.poles == (2,) and not a.domain.contains(2)
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"1^{-|x-3|}\cdot\log_2(6x-x^2-7)\ge1",
        r"\frac{1}{7}^{-|x-3|}\cdot\log_2(6x-x^2-7)\ge1",
        r"7^{|x-3|}\cdot\log_2(6x-x^2-7)\ge1",
        r"7^{1-|x-3|}\cdot\log_2(6x-x^2-7)\ge1",
        r"7^{-|x-2|}\cdot\log_2(6x-x^2-7)\ge1",
        r"7^{-|x-3|}\cdot\log_2(6x-x^2-6)\ge1",
        r"7^{-|x-3|}\cdot\log_3(6x-x^2-7)\ge1",
        r"7^{-|x-3|}\cdot\log_{\frac12}(6x-x^2-7)\ge1",
        r"7^{-|x-3|}\cdot2\log_2(6x-x^2-7)\ge1",
        r"7^{-|x-3|}\cdot\log_2^2(6x-x^2-7)\ge1",
        r"7^{-|x-3|}\cdot\log_2\sqrt{6x-x^2-7}\ge1",
        r"7^{-|x-3|}\cdot\log_2(6x-x^2-7)+1\ge1",
        r"7^{-|x-3|}+\log_2(6x-x^2-7)\ge1",
        r"7^{-|x-3|}\cdot\log_2(6x-x^2-7)>1",
        r"7^{-|x-3|}\cdot\log_2(6x-x^2-7)\le1",
        r"7^{-|x-3|}\cdot\log_2(6x-x^2-7)\ge2",
        r"7^{-|x-3|}\cdot\log_2(6x-x^2-7)\ge1+x",
        r"7^{-|x^2-3|}\cdot\log_2(2-(x^2-3)^2)\ge1",
    ],
)
def test_entire_product_numeric_bases_identity_and_comparison_are_required(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_parent_assets_and_full_instruction_guards(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), sp.FiniteSet(MANUAL[row["task"]][2]))
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель</p>")
    ctx["normalized_content"]["assets"] = [
        {"asset_key": "unknown", "asset_id": "unreviewed"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Дополнительное условие</p>"
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
