"""Verify exact surd samples, original argument poles and scoped three-row charts."""

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
from solution_runner.pipelines.equations.exam_logarithmic_input import read_equation
from solution_runner.pipelines.equations.exam_scalar import compare, enclose
from solution_runner.pipelines.equations.logarithm_inequality_planner import (
    build_context_repair_plan,
)
from solution_runner.pipelines.equations.logarithm_product_inequality import analyze
from solution_runner.pipelines.equations.logarithm_quotient_inequality_figures import (
    SOURCES,
    chart,
    row_signature,
)
from solution_runner.pipelines.equations.logarithm_quotient_inequality_proof import (
    render,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.equations.rational_substitution_preimages import (
    comparison,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_quotient_inequality_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)


def handler():
    return get_handler(get_group_profile("521006").content_rule_key)


def plan(ctx, parent=PARENT):
    return handler().plan(
        PlanInput(
            _with_required_assets(ctx, handler().key), parent_solution_html=parent
        )
    )


def model(row):
    return analyze(read_formula(row["context"])[1], method="quotient")


def test_algebraic_compare_uses_its_exact_simplified_difference():
    value = (-2 + (-sp.sqrt(2) - 1) ** 2) / (-sp.sqrt(2) - 1) ** 2
    with pytest.raises(UnsupportedCondition):
        enclose(value)
    assert (
        compare(value, 0) == 1
        and compare(-value, 0) == -1
        and compare(value, value) == 0
    )
    assert compare(value, 0) == compare(-5 + 4 * sp.sqrt(2), 0)
    with pytest.raises(UnsupportedCondition):
        compare(sp.sin(1), 0)
    with pytest.raises(UnsupportedCondition):
        compare(2 ** sp.sqrt(401), 0)


@pytest.mark.parametrize(
    "op,expected",
    [
        (
            "<=",
            sp.Union(
                sp.Interval.Ropen(-sp.sqrt(2), 0), sp.Interval.Lopen(0, sp.sqrt(2))
            ),
        ),
        (
            "<",
            sp.Union(sp.Interval.open(-sp.sqrt(2), 0), sp.Interval.open(0, sp.sqrt(2))),
        ),
        (
            ">=",
            sp.Union(sp.Interval(-sp.oo, -sp.sqrt(2)), sp.Interval(sp.sqrt(2), sp.oo)),
        ),
    ],
)
def test_rational_intervals_with_surd_samples_and_a_squared_pole(op, expected):
    a = comparison((X**2 - 2) / X**2, op)
    same_set(a.solution, expected)
    assert a.poles == (sp.Integer(0),) and a.solution.contains(0) is sp.false


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_source_answers_independent_cas_domains_and_positive_factor_identity(row):
    a = model(row)
    A, B, C = a.arguments
    independent_domain = sp.Intersection(
        *(
            sp.solve_univariate_inequality(arg > 0, X, relational=False)
            for arg in a.arguments
        )
    )
    full = sp.solve_univariate_inequality(A / B - C <= 0, X, relational=False)
    same_set(full.intersect(independent_domain), a.solution)
    same_set(a.solution, answer_set(row["expected_answer"]))
    assert sp.cancel(a.full_stage.original * B - a.stage.original) == 0
    assert a.full_stage.solution.intersect(a.domain) == a.stage.solution.intersect(
        a.domain
    )
    assert a.displayed_indices == (0, 1) and a.argument_holes == ()
    assert plan(row["context"]).answer == a.answer


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_each_source_chart_is_reused_at_its_certified_intermediate_scope(row):
    a = model(row)
    image, keys, changes, scope = chart(row["context"], a)
    html = render(a, image, scope)
    assert len(keys) == 1 and not changes and html.count("<img ") == 1
    own = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    assert own in html
    entry = SOURCES["figures"][own]
    assert all(entry[k] == v for k, v in row_signature(a, scope).items())
    assert a.full_stage.poles != a.stage.poles
    if row["task"] == "521006":
        assert scope == "positive_factor_removed" and html.index("<img ") > html.index(
            "Средний аргумент положителен"
        )
        assert entry["bottom_signature"]["poles"] == ["0"]
    else:
        assert scope == "full_denominator" and html.index("<img ") < html.index(
            "Средний аргумент положителен"
        )
        assert len(entry["bottom_signature"]["poles"]) == 2


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_original_conditions_and_replay(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(ctx)
    assert ctx == original and not handler().diagram_specs(ctx)
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


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_missing_chart_reuses_an_existing_exact_asset_without_a_new_svg(row):
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    p = plan(ctx)
    assert (
        row["context"]["normalized_content"]["assets"][0]["asset_id"] in p.solution_html
    )
    assert not handler().diagram_specs(ctx)


@pytest.mark.parametrize("task", ["521006", "681152", "701915"])
def test_wrong_denominator_scope_rejected_even_when_final_intersection_matches(
    task, monkeypatch
):
    row = next(r for r in ROWS if r["task"] == task)
    key = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = SOURCES["figures"][key]
    monkeypatch.setitem(
        entry,
        "bottom_scope",
        "full_denominator"
        if entry["bottom_scope"] == "positive_factor_removed"
        else "positive_factor_removed",
    )
    with pytest.raises(UnsupportedCondition):
        plan(row["context"])


@pytest.mark.parametrize("index", [0, 2])
def test_cancelled_original_argument_poles_remain_in_domain_and_proof(index):
    arguments = [r"2+\frac{2}{x}", r"x+3", r"\frac{x+6}{x^2}"]
    arguments[index] = r"\frac{(" + arguments[index] + r")(x-1)}{x-1}"
    formula = (
        r"\log_7("
        + arguments[0]
        + r")-\log_7("
        + arguments[1]
        + r")\le\log_7("
        + arguments[2]
        + ")"
    )
    a = analyze(formula, method="quotient")
    original = model(ROWS[0])
    same_set(a.solution, original.solution - sp.FiniteSet(1))
    assert a.argument_holes == (sp.Integer(1),) and a.domain.contains(1) is sp.false
    assert r"x\ne 1" in render(a, "", "positive_factor_removed")
    if index == 2:
        assert a.displayed_indices == (0, 1, 2)


def test_old_equation_reader_keeps_its_default_polynomial_argument_guard():
    formula = read_formula(ROWS[0]["context"])[1].replace(r"\le", "=")
    with pytest.raises(UnsupportedCondition):
        read_equation(formula, extended=True)
    assert model(ROWS[0]).solution


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_unknown_relabelled_and_duplicate_source_images_fail_closed(row):
    for field, value in [
        ("asset_id", "unknown"),
        ("asset_key", "wrong"),
        ("kind", "wrong"),
        ("url", "/assets/foreign"),
    ]:
        ctx = deepcopy(row["context"])
        ctx["normalized_content"]["assets"][0][field] = value
        with pytest.raises(UnsupportedCondition):
            plan(ctx)
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] *= 2
    with pytest.raises(UnsupportedCondition):
        plan(ctx)


def test_parent_method_mismatch_and_unknown_answers_do_not_change_calculation():
    ctx = deepcopy(ROWS[0]["context"])
    with pytest.raises(UnsupportedCondition):
        plan(ctx, PARENT + "wrong")
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(ctx, parent_solution_html=PARENT, method="product")
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>wrong</p>"
    assert plan(ctx).answer == plan(ROWS[0]["context"]).answer
