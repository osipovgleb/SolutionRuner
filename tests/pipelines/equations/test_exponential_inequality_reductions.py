"""Exact factor reductions, parent-faithful proofs and read-only source preparation."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_quadratic import answer_set, same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exponential_inequality_common_base import (
    read_terms,
)
from solution_runner.pipelines.equations.exponential_inequality_parser import (
    ExponentialParser,
)
from solution_runner.pipelines.equations.exponential_inequality_reductions import (
    ANALYSES,
)
from solution_runner.pipelines.equations.rational_inequality import FLIPPED, analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_inequality_reduction_sources.json")
    .read_text()
)
METHODS = {
    "508457": "homogeneous",
    "508484": "grouped_product",
    "508491": "collected_power",
}


def parent(row):
    p = next(r for r in SOURCES if r["task"] == row["group"])
    return next(
        s["html"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def rule(row):
    return get_group_profile(row["group"]).content_rule_key


def plan(row, ctx=None):
    return get_handler(rule(row)).plan(
        PlanInput(ctx or row["context"], parent_solution_html=parent(row))
    )


def analysis(row):
    return ANALYSES[METHODS[row["group"]]](read_formula(row["context"])[1])


def exact_zero(value):
    assert sp.simplify(sp.expand(value.rewrite(sp.exp))) == 0


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_answers_exact_reduction_and_independent_interval_oracle(row):
    a = analysis(row)
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    if row["group"] == "508484":
        left, right = (b**a.exponent - v for b, v in zip(a.bases, a.bounds))
        exact_zero(a.original - left * right)
        assert all(
            b > 1 and sp.simplify(b**r - v) == 0
            for b, r, v in zip(a.bases, a.roots, a.bounds)
        )
        exact_zero(
            a.stage.original - (a.exponent - a.roots[0]) * (a.exponent - a.roots[1])
        )
        independent = sp.solve_univariate_inequality(
            relation(a.stage.original, 0), X, relational=False
        )
        assert independent == a.solution
    else:
        actual = a.base**a.exponent
        assert actual.is_positive is True
        divisor = a.divisor[0] ** a.divisor[1] if a.divisor else sp.Integer(1)
        assert divisor.is_positive is True
        exact_zero(
            a.original * actual**a.multiply_degree
            - a.stage.original.subs(X, actual) * divisor
        )
        independent = sp.solve_univariate_inequality(
            relation(a.stage.original, 0), X, relational=False
        )
        assert a.positive_solution == independent.intersect(sp.Interval.open(0, sp.oo))
        for t, v, branch in a.back:
            assert t > 0
            exact_zero(a.base**v - t)
            exact_zero(a.exponent.subs(X, branch[0]) - v)
    same_set(a.solution, answer_set(row["expected_answer"]))
    same_set(answer_set(plan(row).answer), a.solution)


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_gateway_replay_does_not_write_or_change_condition_or_assets(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    handler = get_handler(rule(row))
    assert (
        ctx == row["context"]
        and not handler.diagram_specs(ctx)
        and not handler.asset_requirements(ctx)
    )
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        rule(row),
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == p.answer and record["transformations"] == list(
        p.transformations
    )
    assert len(gateway.reads) == 1 and not record.get("generated_diagrams")
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_parent_presentation_and_every_displayed_grouping_identity(row):
    a = analysis(row)
    p = plan(row)
    lines = [
        s["data-inline-latex"]
        for s in BeautifulSoup(p.solution_html, "html.parser").find_all(
            "span", attrs={"data-inline-latex": True}
        )
    ]
    if row["group"] == "508457":
        assert p.solution_html.index("Разделим") < p.solution_html.index(
            "Сделаем замену"
        )
        assert any(f.startswith("z=") and f.endswith(">0") for f in lines)
        assert any("-1" in f and "z" in f and r"\le" in f for f in lines)
        assert "Учитывая положительность z" in p.solution_html and all(
            t > 0 for t, _, _ in a.back
        )
    elif row["group"] == "508491":
        assert not any(re.match("[tyz]=", f) for f in lines)
        assert "Вынесем общую степень" in p.solution_html
        coefficient = dict(a.coefficients)[1]
        assert (
            "отрицательное" if coefficient < 0 else "положительное"
        ) in p.solution_html
        assert ("меняется" if coefficient < 0 else "сохраняется") in p.solution_html
        if row["task"] == "508491":
            assert r"\log_{5}(3)+1" in p.answer and r"\log_{5}(15)" not in p.answer
    else:
        checked = 0
        for formula in lines:
            if "=" in formula:
                left, right = formula.split("=")
                exact_zero(
                    ExponentialParser(left).parse().value
                    - ExponentialParser(right).parse().value
                )
                checked += 1
        assert checked == 2
        assert (
            "тот же знак" in p.solution_html
            and "равносильное неравенство" in p.solution_html
        )
        assert not any("4 x" in f and "3" in f for f in lines)


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] != "508484"], ids=lambda r: r["task"]
)
def test_displayed_power_and_polynomial_inequalities_preserve_the_solution(row):
    a = analysis(row)
    checked = 0
    for span in BeautifulSoup(plan(row).solution_html, "html.parser").find_all(
        "span", attrs={"data-inline-latex": True}
    ):
        text = span["data-inline-latex"]
        if (
            "=" in text
            or r"\log" in text
            or len(re.findall(r"\\(?:le|ge|gt|lt)(?![a-zA-Z])|<|>", text)) != 1
            or not re.search(r"[xz]", text)
        ):
            continue
        left, right, _, operator = read_terms(text.replace("z", "x"))
        value = left.value - right.value
        if value.is_positive is True:
            assert operator == ">"
            continue
        if "z" not in text and not any(p.exp.has(X) for p in value.atoms(sp.Pow)):
            same_set(analyze(text).solution, a.solution)
            checked += 1
            continue
        reference = a.stage.original if "z" in text else a.original
        ratio = sp.simplify(
            sp.cancel(
                sp.expand(value.rewrite(sp.exp)) / sp.expand(reference.rewrite(sp.exp))
            )
        )
        assert ratio.is_positive is True or ratio.is_negative is True, text
        assert operator == (a.operator if ratio.is_positive else FLIPPED[a.operator]), (
            text
        )
        checked += 1
    assert checked >= 3


@pytest.mark.parametrize(
    "method,formula,expected",
    [
        (
            "homogeneous",
            r"25^{-x}-20^{-x}-2\cdot16^{-x}\le0",
            sp.Interval(-sp.log(2) / sp.log(sp.Rational(5, 4)), sp.oo),
        ),
        (
            "collected_power",
            r"5^{3x-1}-5^{3x+1}<-72",
            sp.Interval.open((sp.log(3) / sp.log(5) + 1) / 3, sp.oo),
        ),
        ("collected_power", r"2^{-x}+2^{1-x}>6", sp.Interval.open(-sp.oo, -1)),
        ("grouped_product", r"6^x-3^x-2^x+1\le0", sp.FiniteSet(0)),
        ("grouped_product", r"6^x-3^x-2^x+1<0", sp.EmptySet),
        (
            "grouped_product",
            r"6^{1-x}-4\cdot3^{1-x}-2^{1-x}+4<0",
            sp.Interval.open(-1, 1),
        ),
    ],
)
def test_strict_bounds_decreasing_substitutions_and_repeated_factors(
    method, formula, expected
):
    same_set(ANALYSES[method](formula).solution, expected)


@pytest.mark.parametrize(
    "method,formula",
    [
        ("homogeneous", r"25^x-20^x-2\cdot15^x\le0"),
        ("homogeneous", r"25^x-20^x-2\cdot16^x+1\le0"),
        ("homogeneous", r"25^{x^2}-20^x-2\cdot16^x\le0"),
        ("homogeneous", r"\frac{25^x}{x-1}-20^x-2\cdot16^x\le0"),
        ("collected_power", r"5^x+5^{2x}\le3"),
        ("collected_power", r"5^x-5^x\le3"),
        ("collected_power", r"5^x+3^x\le3"),
        ("collected_power", r"5^x+5^{x+1000000000000}\le3"),
        ("grouped_product", r"6^x-4\cdot3^x-2^x+5\le0"),
        ("grouped_product", r"7^x-4\cdot3^x-2^x+4\le0"),
        ("grouped_product", r"6^x-4\cdot3^x+2^x-4\le0"),
        ("grouped_product", r"6^{2x}-4\cdot3^x-2^x+4\le0"),
        ("grouped_product", r"(-6)^x-4\cdot3^x-2^x+4\le0"),
    ],
)
def test_unreviewed_factorization_degree_domains_and_unbounded_offsets_fail_closed(
    method, formula
):
    with pytest.raises(UnsupportedCondition):
        ANALYSES[method](formula)


@pytest.mark.parametrize("group", METHODS)
@pytest.mark.parametrize(
    "change",
    ("answer", "solution", "asset", "instruction", "parent", "other_method_parent"),
)
def test_only_condition_computes_answers_and_parent_methods_are_isolated(group, change):
    row = next(r for r in SOURCES if r["task"] == group)
    ctx = deepcopy(row["context"])
    if change in ("answer", "solution"):
        next(s for s in ctx["normalized_content"]["sections"] if s["key"] == change)[
            "html"
        ] = "<p>Неверно</p>"
        assert plan(row, ctx).answer == plan(row).answer
        return
    if change == "asset":
        ctx["normalized_content"]["assets"] = [
            {"asset_id": "unknown", "asset_key": "image_1"}
        ]
    elif change == "instruction":
        next(
            s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
        )["html"] += "<p>Укажите только целые решения.</p>"
    with pytest.raises(UnsupportedCondition):
        if change in ("parent", "other_method_parent"):
            html = (
                parent(row) + " "
                if change == "parent"
                else parent(next(r for r in SOURCES if r["group"] != group))
            )
            get_handler(rule(row)).plan(PlanInput(ctx, parent_solution_html=html))
        else:
            plan(row, ctx)
