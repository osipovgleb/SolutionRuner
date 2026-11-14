"""Certify exact squares, retained pole multiplicities and source chart reuse."""

import json
from copy import deepcopy
from pathlib import Path

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
from solution_runner.pipelines.equations.exponential_inequality_common_base import (
    read_terms,
)
from solution_runner.pipelines.equations.exponential_squared_denominator import analyze
from solution_runner.pipelines.equations.exponential_squared_denominator_figures import (
    SOURCES,
    row_signature,
)
from solution_runner.pipelines.equations.exponential_squared_denominator_proof import (
    render,
)
from solution_runner.pipelines.equations.rational_exponential_figures import (
    multiplicity,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_squared_denominator_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)


def handler():
    return get_handler(get_group_profile("681197").content_rule_key)


def plan(context, parent=PARENT):
    context = _with_required_assets(context, handler().key)
    return handler().plan(PlanInput(context, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_actual_answers_exact_denominator_identity_and_independent_rational_cas(row):
    a = analyze(read_formula(row["context"])[1])
    difference = a.denominator - a.scalar * (a.base**a.exponent - a.root) ** 2
    assert sp.simplify(sp.expand(difference)) == 0
    assert a.base**a.level == a.root
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.stage.original, 0), X, relational=False
    ) - sp.FiniteSet(*a.stage.poles)
    same_set(independent, a.solution)
    same_set(a.solution, answer_set(row["source_answer"]))
    n, d = sp.fraction(a.stage.expression)
    assert sorted(multiplicity(n, z) for z in a.stage.zeros) == [1, 2]
    assert len(a.stage.poles) == 2 and all(
        multiplicity(d, p) == 2 for p in a.stage.poles
    )
    assert all(a.solution.contains(p) is sp.false for p in a.stage.poles)
    for point in (-3, -2, -1, 0, 1, 2, 3):
        if point in a.stage.poles:
            continue
        actual = a.numerator.subs(X, point) / a.denominator.subs(X, point)
        assert sp.simplify(relation(actual, 0)) == a.solution.contains(point)
    assert plan(row["context"]).answer == a.answer


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_displayed_grouping_and_square_identities_are_exact(row):
    a = analyze(read_formula(row["context"])[1])
    html = render(a)
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").find_all(
            attrs={"data-inline-latex": True}
        )
    ]
    for formula in formulas[:3]:
        left, right, _, _ = read_terms(formula.replace("=", r"\le ", 1))
        assert sp.expand(left.value - right.value) == 0, (row["task"], formula)
    assert formulas[7].count("^{2}") == 3
    assert "те же нули" in html and "исключены" in html
    assert "2(x^{2}-2)" not in html


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_and_original_chart_reuse_are_idempotent(row):
    context = deepcopy(row["context"])
    original = deepcopy(context)
    p = plan(context)
    assert context == original and not handler().diagram_specs(context)
    asset = context["normalized_content"]["assets"][0]
    assert p.solution_html.count("<img ") == 1 and asset["asset_id"] in p.solution_html
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in p.transformations
    )
    entry = SOURCES["figures"][asset["asset_id"]]
    assert all(
        entry[k] == v
        for k, v in row_signature(analyze(read_formula(context)[1])).items()
    )
    gateway = ReadOnlyGateway(context)
    result = _prepared_record(
        gateway,
        {"problem_id": context["problem_id"], "source_problem_id": row["task"]},
        None,
        handler().key,
        parent_solution_html=PARENT,
    )
    assert result["status"] == "prepared" and result["transformations"] == list(
        p.transformations
    )
    assert gateway.reads == [context["problem_id"]]
    replay(context, p.transformations)
    assert not plan(context).transformations


def test_equal_charts_keep_the_actual_source_and_missing_asset_reuses_existing():
    first = next(r for r in ROWS if r["task"] == "681246")
    second = next(r for r in ROWS if r["task"] == "681273")
    assert row_signature(analyze(read_formula(first["context"])[1])) == row_signature(
        analyze(read_formula(second["context"])[1])
    )
    for row in (first, second):
        own = row["context"]["normalized_content"]["assets"][0]["asset_id"]
        assert own in plan(row["context"]).solution_html
    ctx = deepcopy(second["context"])
    ctx["normalized_content"]["assets"] = []
    p = plan(ctx)
    assert (
        first["context"]["normalized_content"]["assets"][0]["asset_id"]
        in p.solution_html
    )
    assert not handler().diagram_specs(ctx)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_foreign_relabelled_and_duplicate_figures_fail_closed(row):
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


def test_full_signature_rejects_changed_multiplicities(monkeypatch):
    row = ROWS[0]
    key = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = SOURCES["figures"][key]
    monkeypatch.setitem(entry, "multiplicities", {"zeros": {}, "poles": {}})
    with pytest.raises(UnsupportedCondition):
        plan(row["context"])


def test_shifted_numerator_roots_scalar_and_strict_comparison_are_calculated():
    a = analyze(r"\frac{2x^3+6x^2-8}{2\cdot4^{x^2}-32\cdot2^{x^2}+128}\ge0")
    same_set(
        a.solution,
        sp.Union(
            sp.FiniteSet(-2),
            sp.Interval.Ropen(1, sp.sqrt(3)),
            sp.Interval.open(sp.sqrt(3), sp.oo),
        ),
    )
    assert a.scalar == 2
    assert "Положительный числовой множитель" in render(a)
    negative = analyze(r"\frac{-x^3-x^2+x+1}{4^{x^2}-8\cdot2^{x^2}+16}\le0")
    same_set(negative.solution, analyze(read_formula(ROWS[0]["context"])[1]).solution)
    assert "отрицательный множитель" in render(negative)
    strict = analyze(r"\frac{x^3+x^2-x-1}{4^{x^2}-8\cdot2^{x^2}+16}>0")
    same_set(
        strict.solution,
        sp.Union(sp.Interval.open(1, sp.sqrt(2)), sp.Interval.open(sp.sqrt(2), sp.oo)),
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{x^3+x^2-x-1}{4^{x^2}-7\cdot2^{x^2}+16}\ge0",
        r"\frac{x^3+x^2-x-1}{4^x-8\cdot2^x+16}\ge0",
        r"\frac{x^3+x^2-x-1}{4^{x^2}+8\cdot2^{x^2}+16}\ge0",
        r"\frac{x^3+x^2-x-1}{4^{x^2}-2\cdot2^{x^2}+1}\ge0",
        r"\frac{x^3-1}{4^{x^2}-8\cdot2^{x^2}+16}\ge0",
        r"\frac{x^3+x^2-x-1}{4^{x^2}-8\cdot2^{x^2}+16}\ge1",
    ],
)
def test_non_square_or_other_root_and_pole_structure_fails_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_foreign_parent_and_source_answers_do_not_change_calculation():
    ctx = deepcopy(ROWS[0]["context"])
    with pytest.raises(UnsupportedCondition):
        plan(ctx, PARENT + "wrong")
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>wrong</p>"
    assert plan(ctx).answer == plan(ROWS[0]["context"]).answer
