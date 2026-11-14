"""Verify decreasing logarithms, implied domains and strict repeated-root holes."""

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

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exponential_inequality_common_base import (
    read_terms,
)
from solution_runner.pipelines.equations.logarithm_product_inequality import analyze
from solution_runner.pipelines.equations.logarithm_product_inequality_proof import (
    grouping,
    render,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_product_inequality_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)


def handler():
    return get_handler(get_group_profile("526217").content_rule_key)


def plan(context, parent=PARENT):
    return handler().plan(PlanInput(context, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_source_answers_independent_domains_and_logarithmic_samples(row):
    a = analyze(read_formula(row["context"])[1])
    A, B, C = a.arguments
    independent_domain = sp.Intersection(
        *(
            sp.solve_univariate_inequality(v > 0, X, relational=False)
            for v in a.arguments
        )
    )
    independent = sp.solve_univariate_inequality(
        B * C - A < 0, X, relational=False
    ).intersect(independent_domain)
    same_set(independent, a.solution)
    same_set(a.solution, answer_set(row["expected_answer"]))
    assert a.displayed_indices == (1, 2)
    assert a.display_domain.intersect(a.stage.solution) == a.domain.intersect(
        a.stage.solution
    )
    for point in (-8, -7, -6, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6):
        if a.domain.contains(point) is not sp.true:
            continue
        args = [v.subs(X, point) for v in a.arguments]
        actual = sp.simplify(
            sp.expand_log(
                (sp.log(args[0]) - sp.log(args[1]) - sp.log(args[2])) / sp.log(a.base)
            )
        )
        assert bool(actual.evalf(50) < 0) == bool(a.solution.contains(point))
    assert plan(row["context"]).answer == a.answer


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_system_cubic_grouping_and_domain_intersection_are_exact(row):
    a = analyze(read_formula(row["context"])[1])
    html = render(a)
    equations = [
        n["data-inline-latex"]
        for n in BeautifulSoup(grouping(a), "html.parser").find_all(
            attrs={"data-inline-latex": True}
        )
    ]
    assert len(equations) == 3
    for text in equations:
        left, right, _, _ = read_terms(text)
        assert sp.expand(left.value - a.stage.original) == 0 and right.value == 0
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").find_all(
            attrs={"data-inline-latex": True}
        )
    ]
    assert formulas[0].startswith(r"\begin{cases}") and formulas[0].count(">0") == 2
    assert "знак сравнения аргументов меняется" in html
    assert "Пересечём" in html and "Оставшийся аргумент положителен" in html
    assert "<img " not in html
    if row["task"] == "526217":
        assert "множитель положителен" in html
    else:
        hole = -2 if row["task"] == "654863" else -1
        assert (
            a.domain.contains(hole) is sp.true and a.solution.contains(hole) is sp.false
        )
        assert "при строгом сравнении он исключён" in html


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_condition_immutability_and_replay(row):
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


@pytest.mark.parametrize(
    "base,operator,expected,indices",
    [
        ("7", r"\lt", sp.EmptySet, (0, 1, 2)),
        ("7", r"\gt", sp.Interval.open(-2, 1), (1, 2)),
        (r"\frac{1}{3}", r"\ge", sp.EmptySet, (0, 1, 2)),
    ],
)
def test_increasing_base_and_other_comparisons_keep_all_required_domains(
    base, operator, expected, indices
):
    a = analyze(
        r"\log_{"
        + base
        + r"}(18-9x)"
        + operator
        + r"\log_{"
        + base
        + r"}(x^2-6x+5)+\log_{"
        + base
        + r"}(x+2)"
    )
    same_set(a.solution, expected)
    assert a.displayed_indices == indices
    assert "Основание" in render(a)


def test_nonstrict_relation_retains_the_repeated_root():
    row = next(r for r in ROWS if r["task"] == "654863")
    a = analyze(read_formula(row["context"])[1].replace(r"\lt", r"\le"))
    assert a.solution == sp.Interval.open(-7, 1) and a.solution.contains(-2) is sp.true


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_x(18-9x)<\log_x(x^2-6x+5)+\log_x(x+2)",
        r"\log_3(18-9x)<\log_5(x^2-6x+5)+\log_3(x+2)",
        r"\log_3(18-9x)+x<\log_3(x^2-6x+5)+\log_3(x+2)",
        r"2\log_3(18-9x)<\log_3(x^2-6x+5)+\log_3(x+2)",
        r"\log_3(18-9x)<\log_3(x+2)",
        r"\log_3\sqrt{18-9x}<\log_3(x^2-6x+5)+\log_3(x+2)",
        r"\log_3(18-9x)<\log_3(x^3-6x+5)+\log_3(x+2)",
    ],
)
def test_unreviewed_atoms_bases_and_outer_expressions_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_foreign_parent_assets_and_unknown_source_answers_are_safe():
    ctx = deepcopy(ROWS[0]["context"])
    with pytest.raises(UnsupportedCondition):
        plan(ctx, PARENT + "wrong")
    ctx["normalized_content"]["assets"] = [{"asset_id": "unknown"}]
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
    ctx = deepcopy(ROWS[0]["context"])
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>wrong</p>"
    assert plan(ctx).answer == plan(ROWS[0]["context"]).answer
