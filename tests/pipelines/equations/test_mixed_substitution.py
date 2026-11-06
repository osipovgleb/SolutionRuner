"""Native mixed substitution, original domains and certified union-image reuse."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_exponential_inequality_quadratic import answer_set, same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exponential_inequality_rational_exponents import (
    analyze as exponential,
)
from solution_runner.pipelines.equations.logarithmic_inequality_substitution import (
    analyze as logarithmic,
)
from solution_runner.pipelines.equations.mixed_substitution_figures import (
    SOURCES,
    chart,
    required_assets,
    row_signature,
)
from solution_runner.pipelines.equations.mixed_substitution_proof import model
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.equations.rational_substitution_preimages import (
    branches,
    comparison,
    excluded_points,
)
from solution_runner.pipelines.equations.variable_logarithm_parser import (
    VariableLogarithmParser,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES_ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("mixed_substitution_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in SOURCES_ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
RULE = "exam-exponential-inequality-mixed_substitution"


def plan(row, context=None, parent=PARENT):
    return get_handler(RULE).plan(
        PlanInput(context or row["context"], parent_solution_html=parent)
    )


@pytest.mark.parametrize("row", SOURCES_ROWS, ids=lambda r: r["task"])
def test_native_answers_exact_identities_and_independent_inverse_cas(row):
    a = model(read_formula(row["context"])[1])
    same_set(a.solution, answer_set(row["expected_answer"]))
    same_set(answer_set(plan(row).answer), a.solution)
    if row["task"] == "514046":
        first, second = a.atoms
        assert sp.cancel(second.argument - first.argument / first.base**a.shift) == 0
        assert a.stage.original == X**2 - 3 * X + 2
        assert a.domain == sp.S.Reals - sp.FiniteSet(0, 3)
        assert a.decreasing_domain == sp.EmptySet
    else:
        t = a.base**a.exponent
        difference = (
            a.original * t**a.multiply_degree - a.stage.original.subs(X, t)
        ).rewrite(sp.exp)
        difference = difference.replace(
            lambda e: e.func == sp.exp, lambda e: sp.exp(sp.apart(e.args[0], X))
        )
        assert sp.simplify(sp.expand(difference)) == 0
    results = []
    relations = {"<": sp.Lt, ">": sp.Gt, "<=": sp.Le, ">=": sp.Ge}
    for branch in a.branches:
        constraints = []
        for c in branch.conditions:
            stage = c.stage
            independent = sp.solve_univariate_inequality(
                relations[stage.operator](stage.original, 0), X, relational=False
            )
            same_set(independent, stage.solution)
            constraints.append(independent)
        results.append(sp.Intersection(branch.domain, *constraints))
    assert a.solution == sp.Union(*results)


@pytest.mark.parametrize("row", SOURCES_ROWS, ids=lambda r: r["task"])
def test_replay_and_read_only_runtime_preserve_source_images(row):
    result = plan(row)
    assert get_group_profile("514027").content_rule_key == RULE
    assert all(
        t["transformation_target_id"].startswith("section:")
        for t in result.transformations
    )
    updated = deepcopy(row["context"])
    replay(updated, result.transformations)
    assert not plan(row, updated).transformations
    assert (
        updated["normalized_content"]["assets"]
        == row["context"]["normalized_content"]["assets"]
    )
    if row["context"]["normalized_content"]["assets"]:
        image = row["context"]["normalized_content"]["assets"][0]
        assert result.solution_html.count("<img ") == 1
        assert image["asset_id"] in result.solution_html
        assert SOURCES["figures"][image["asset_id"]]["operation"] == "union"
        assert all(
            SOURCES["figures"][image["asset_id"]][k] == v
            for k, v in row_signature(model(read_formula(row["context"])[1])).items()
        )
    else:
        assert "<img " not in result.solution_html
    gateway = ReadOnlyGateway(row["context"])
    record = _prepared_record(
        gateway,
        {"problem_id": row["context"]["problem_id"], "source_problem_id": row["task"]},
        None,
        RULE,
        parent_solution_html=PARENT,
    )
    assert record["status"] == "prepared", record
    assert record["transformations"] == list(result.transformations)
    assert gateway.reads == [row["context"]["problem_id"]]
    assert gateway.ctx == row["context"]


def test_cancellation_never_restores_a_source_exponent_pole():
    original = read_formula(SOURCES_ROWS[0]["context"])[1]
    changed = original.replace(r"\frac{x}{x+1}", r"\frac{x(x-2)}{(x+1)(x-2)}", 1)
    a = exponential(changed)
    assert a.poles == (-1, 2)
    assert a.solution == model(original).solution - sp.FiniteSet(2)
    assert excluded_points((X / (X - 2),)) == (0, 2)


def test_cancellation_inside_log_argument_keeps_its_original_hole():
    original = read_formula(SOURCES_ROWS[1]["context"])[1]
    changed = original.replace("(x-3)^{2}", r"\frac{(x-3)^{2}(x-1)}{x-1}", 1)
    a = logarithmic(changed)
    assert 1 not in a.domain
    assert a.solution == model(original).solution - sp.FiniteSet(1)


def test_negative_log_values_are_not_cut_off_as_exponentials():
    a = logarithmic(r"\log_{x+2}(x+1)\cdot\log_{x+2}\frac{x+1}{x+2}\ge 0")
    assert a.solution == sp.Interval.Lopen(-1, 0)
    assert a.stage.solution.contains(-1) is sp.true


def test_log_base_below_one_reverses_each_inverse_comparison():
    a = logarithmic(r"\log_{x+1}(x+2)\cdot\log_{x+1}\frac{x+2}{x+1}\ge 0")
    assert a.decreasing_domain == sp.Interval.open(-1, 0)
    assert a.increasing_domain == sp.Interval.open(0, sp.oo)
    assert a.solution == sp.Interval.open(-1, sp.oo) - sp.FiniteSet(0)


def test_finite_points_intersect_inside_branch_and_union_across_branches():
    result = branches(
        sp.FiniteSet(-1, 2), sp.S.Reals, lambda t, op: comparison(X - t, op)
    )
    assert sp.Union(*(b.solution for b in result)) == sp.FiniteSet(-1, 2)
    interval = branches(
        sp.Interval(0, 1), sp.S.Reals, lambda t, op: comparison(X - t, op)
    )
    assert interval[0].solution == sp.Interval(0, 1)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{x+1}",
        r"\log_{x+1}()",
        r"\log_x(x+1)",
        r"\log_{x+1}(x+1)^",
        r"\log_{x+1}(x+1)^{100}",
        r"(\log_{x+1}(x+2))^{-1}",
        r"\sqrt{\log_{x+1}(x+2)}",
        r"1/(\log_{x+1}(x+2))",
        r"unknown(x)",
    ],
)
def test_closed_log_parser_rejects_unsupported_or_undefined_syntax(formula):
    with pytest.raises(UnsupportedCondition):
        VariableLogarithmParser(formula).parse()


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{x+1}(x+2)\cdot\log_{x+2}\frac{x+2}{x+1}\ge 0",
        r"\log_{x+1}(x+2)\cdot\log_{x+1}(x+3)\ge 0",
        r"\log_{x+1}(x+2)\ge 0",
        r"2^{x/(x+1)}+2^{x/(x-1)}\ge 0",
        r"2^{x}+2^{2x}\ge 0",
    ],
)
def test_model_rejects_unreviewed_substitution_patterns(formula):
    with pytest.raises(UnsupportedCondition):
        model(formula)


@pytest.mark.parametrize(
    "row",
    [r for r in SOURCES_ROWS if r["context"]["normalized_content"]["assets"]],
    ids=lambda r: r["task"],
)
def test_unknown_duplicate_swapped_or_relabelled_images_fail_closed(row):
    for field, value in [
        ("asset_id", "unknown"),
        ("asset_key", "wrong"),
        ("kind", "other"),
        ("url", "/assets/other"),
    ]:
        ctx = deepcopy(row["context"])
        ctx["normalized_content"]["assets"][0][field] = value
        with pytest.raises(UnsupportedCondition):
            plan(row, ctx)
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] *= 2
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    other = next(
        r for r in SOURCES_ROWS if r["task"] in ("672802", "672940") and r != row
    )
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = other["context"]["normalized_content"][
        "assets"
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


@pytest.mark.parametrize(
    "row",
    [r for r in SOURCES_ROWS if r["context"]["normalized_content"]["assets"]],
    ids=lambda r: r["task"],
)
def test_missing_chart_requires_exact_source_reuse_not_generation(row):
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    for s in ctx["normalized_content"]["sections"]:
        s["asset_keys"] = []
    needed = required_assets(ctx)
    assert len(needed) == 1
    assert (
        needed[0]["source_asset_id"]
        == row["context"]["normalized_content"]["assets"][0]["asset_id"]
    )
    with pytest.raises(UnsupportedCondition):
        chart(ctx, model(read_formula(ctx)[1]))
    from solution_runner.pipelines.core.content_runtime import _with_required_assets

    prepared = _with_required_assets(ctx, RULE)
    assert len(prepared["normalized_content"]["assets"]) == 1
    result = plan(row, prepared)
    assert result.solution_html.count("<img ") == 1
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )


@pytest.mark.parametrize("row", SOURCES_ROWS, ids=lambda r: r["task"])
def test_only_condition_drives_math_and_latex_commands_are_complete(row):
    from bs4 import BeautifulSoup

    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>wrong answer</p>"
    assert plan(row, ctx).answer == plan(row).answer
    html = plan(row).solution_html
    for span in BeautifulSoup(html, "html.parser").find_all(
        attrs={"data-inline-latex": True}
    ):
        assert r"\gex" not in span["data-inline-latex"]
        assert r"\lex" not in span["data-inline-latex"]


def test_union_chart_role_and_original_sign_orientation_cannot_change(monkeypatch):
    row = next(r for r in SOURCES_ROWS if r["task"] == "672802")
    a = model(read_formula(row["context"])[1])
    assert a.branches[1].conditions[0].stage.signs == (1, -1)
    key = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    monkeypatch.setitem(SOURCES["figures"][key], "operation", "intersection")
    with pytest.raises(UnsupportedCondition):
        plan(row)


def test_unreviewed_parent_rejected():
    with pytest.raises(UnsupportedCondition):
        plan(SOURCES_ROWS[0], parent=PARENT + "changed")
