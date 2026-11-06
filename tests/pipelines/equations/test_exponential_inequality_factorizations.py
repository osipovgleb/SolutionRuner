"""Positive-factor signs, preserved linear poles and both native grouping methods."""

import json
import re
from copy import deepcopy
from itertools import pairwise
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
from solution_runner.pipelines.equations.exam_scalar import compare
from solution_runner.pipelines.equations.exponential_inequality_common_base import (
    read_terms,
)
from solution_runner.pipelines.equations.exponential_inequality_factorizations import (
    ANALYSES,
)
from solution_runner.pipelines.equations.exponential_inequality_parser import (
    ExponentialParser,
)
from solution_runner.pipelines.equations.rational_inequality import set_latex
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X, polynomial
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_inequality_factorization_sources.json")
    .read_text()
)
METHODS = {"513348": "linear_denominator", "548802": "grouped_quadratic"}


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


def zero(value):
    assert sp.simplify(sp.expand(value.rewrite(sp.exp))) == 0


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_exact_factorization_source_answer_and_independent_cas(row):
    a = analysis(row)
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    if row["group"] == "513348":
        n = a.numerator
        t = n.base**n.exponent
        leading = sp.Poly(n.stage.original, X).LC()
        zero(n.original * t - n.stage.original.subs(X, t))
        zero(n.original - leading * (t - a.negative_root) * (t - a.positive_root) / t)
        assert (leading * (t - a.negative_root) / t).is_positive is True
        zero(n.base**a.level - a.positive_root)
        reduced = (n.exponent - a.level) / a.denominator
        independent = sp.solve_univariate_inequality(
            relation(reduced, 0), X, relational=False
        )
        original_poles = sp.FiniteSet(*sp.solveset(a.denominator, X, domain=sp.S.Reals))
        assert a.solution == independent - original_poles
        assert sp.FiniteSet(
            *a.stage.poles
        ) == original_poles and not a.solution.intersect(original_poles)
    else:
        factored = (a.other**X - a.base**X) * a.quadratic.original.subs(X, a.base**X)
        zero(a.original - factored)
        assert a.other / a.base > 1 and a.base > 1 and a.coefficients[0] > 0
        for t, value, roots in a.back:
            zero(a.base**value - t)
            assert roots == (value,)
        independent = sp.solve_univariate_inequality(
            relation(X * sp.prod(X - r for r in a.roots), 0), X, relational=False
        )
        assert independent == a.solution
    same_set(a.solution, answer_set(row["expected_answer"]))
    same_set(answer_set(plan(row).answer), a.solution)


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] == "548802"], ids=lambda r: r["task"]
)
def test_interval_signs_match_actual_exponential_function_samples(row):
    a = analysis(row)
    boundaries = (-sp.oo, *a.stage.points, sp.oo)
    signs = []
    for lo, hi in pairwise(boundaries):
        sample = hi - 1 if lo == -sp.oo else lo + 1 if hi == sp.oo else (lo + hi) / 2
        signs.append(compare(sp.simplify(a.original.subs(X, sample)), 0))
    assert tuple(signs) == a.stage.signs
    for r in a.stage.zeros:
        zero(a.original.subs(X, r))


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] == "513348"], ids=lambda r: r["task"]
)
def test_every_unconditional_printed_identity_is_exact(row):
    checked = 0
    for span in BeautifulSoup(plan(row).solution_html, "html.parser").find_all(
        "span", attrs={"data-inline-latex": True}
    ):
        text = span["data-inline-latex"]
        if "=" not in text or r"\iff" in text or r"\quad" in text:
            continue
        left, right = text.split("=")
        if right.strip() == "0" or text.startswith("t="):
            continue
        zero(
            ExponentialParser(left).parse().value
            - ExponentialParser(right).parse().value
        )
        checked += 1
    assert checked >= 4


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] == "548802"], ids=lambda r: r["task"]
)
def test_every_displayed_exponential_grouping_preserves_the_inequality(row):
    a = analysis(row)
    checked = 0
    for span in BeautifulSoup(plan(row).solution_html, "html.parser").find_all(
        "span", attrs={"data-inline-latex": True}
    ):
        text = span["data-inline-latex"]
        if (
            not text.endswith("0")
            or "=" in text
            or len(re.findall(r"\\(?:le|ge|gt|lt)(?![a-zA-Z])|<|>", text)) != 1
            or "x" not in text
            or r"\iff" in text
        ):
            continue
        left, right, _, operator = read_terms(text)
        value = left.value - right.value
        if not any(p.exp.has(X) for p in value.atoms(sp.Pow)):
            continue
        ratio = sp.simplify(
            sp.cancel(
                sp.expand(value.rewrite(sp.exp)) / sp.expand(a.original.rewrite(sp.exp))
            )
        )
        assert ratio.is_Rational is True and ratio > 0 and operator == a.operator, text
        checked += 1
    assert checked >= 8


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_readonly_gateway_replay_and_condition_asset_immutability(row):
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
def test_parent_method_count_order_and_positive_factor_explanation(row):
    p = plan(row)
    a = analysis(row)
    if row["group"] == "548802":
        assert p.solution_html.count("<strong>") == 2
        first, second = p.solution_html.split("<p><strong>Второй способ.</strong></p>")
        assert (
            "Первый способ." in first
            and "метод интервалов" in first
            and "рационализации" not in first
        )
        assert "рационализации" in second and "знаком" in second
        assert (
            first.count("x\\in " + a.answer) == 1
            and second.count("x\\in " + a.answer) == 1
        )
    else:
        assert (
            "положителен при любом" in p.solution_html
            and "тот же знак" in p.solution_html
        )
        assert r"x\ne " + sp.latex(a.stage.poles[0]) in p.solution_html
        assert "t=" not in p.solution_html and "y=" not in p.solution_html
        if row["task"] == "513348":
            assert polynomial(a.numerator.stage.original).LC() == 2
        if row["task"] == "516333":
            assert "−" in row["source_answer"] and "0,5" in row["source_answer"]


@pytest.mark.parametrize(
    "method,formula,expected",
    [
        (
            "linear_denominator",
            r"\frac{4^x-4/4^x}{x}>0",
            sp.Interval.open(-sp.oo, 0) | sp.Interval.open(sp.Rational(1, 2), sp.oo),
        ),
        ("linear_denominator", r"\frac{4^x-4/4^x}{x-\frac{1}{2}}\le0", sp.EmptySet),
        (
            "linear_denominator",
            r"\frac{4^x-4/4^x}{x-\frac{1}{2}}\ge0",
            sp.S.Reals - sp.FiniteSet(sp.Rational(1, 2)),
        ),
        (
            "linear_denominator",
            r"\frac{4^x-4/4^x}{-x}\le0",
            sp.Interval.open(-sp.oo, 0) | sp.Interval(sp.Rational(1, 2), sp.oo),
        ),
        (
            "grouped_quadratic",
            r"20^x-8^x-9\cdot10^x+9\cdot4^x+8\cdot5^x-8\cdot2^x\le0",
            sp.Interval(-sp.oo, 3),
        ),
        (
            "grouped_quadratic",
            r"20^x-8^x-9\cdot10^x+9\cdot4^x+8\cdot5^x-8\cdot2^x<0",
            sp.Interval.open(-sp.oo, 0) | sp.Interval.open(0, 3),
        ),
    ],
)
def test_strictness_negative_denominator_cancellation_and_repeated_zero(
    method, formula, expected
):
    same_set(ANALYSES[method](formula).solution, expected)


@pytest.mark.parametrize(
    "formula,expected",
    [
        (r"\frac{4^x-4/4^x}{x-\frac{1}{2}}\le0", sp.EmptySet),
        (
            r"\frac{4^x-4/4^x}{-x}\le0",
            sp.Interval.open(-sp.oo, 0) | sp.Interval(sp.Rational(1, 2), sp.oo),
        ),
    ],
)
def test_prepared_proof_preserves_cancelled_pole_and_negative_normalization(
    formula, expected
):
    row = SOURCES[0]
    ctx = deepcopy(row["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    soup.find("span", attrs={"data-inline-latex": True})["data-inline-latex"] = formula
    condition["html"] = str(soup)
    p = plan(row, ctx)
    assert p.answer == set_latex(expected)
    if expected == sp.EmptySet:
        assert (
            r"x\ne \frac{1}{2}" in p.solution_html
            and "Сокращение общего множителя сохраняет" in p.solution_html
        )
    else:
        assert (
            "отрицательный множитель" in p.solution_html
            and r"x\ne 0" in p.solution_html
        )


@pytest.mark.parametrize(
    "method,formula",
    [
        ("linear_denominator", r"\frac{4^x-4/4^x}{x^2-1}\le0"),
        ("linear_denominator", r"\frac{4^x-4/4^x}{x}\le1"),
        ("linear_denominator", r"\frac{4^{\frac{x}{x-1}}-2^x}{x}\le0"),
        ("linear_denominator", r"\frac{2^x+3^x-1}{x}\le0"),
        ("linear_denominator", r"\frac{4^x-3\cdot2^x+2}{x}\le0"),
        ("linear_denominator", r"\frac{2^x-2^{-x}+2}{x}\le0"),
        (
            "grouped_quadratic",
            r"3\cdot45^x-3\cdot27^x-28\cdot15^x+28\cdot9^x+9\cdot5^x-8\cdot3^x\le0",
        ),
        (
            "grouped_quadratic",
            r"3\cdot45^x-3\cdot27^x-28\cdot15^x+28\cdot9^x+9\cdot5^x-3^{x+2}+1\le0",
        ),
        (
            "grouped_quadratic",
            r"3\cdot45^{x^2}-3\cdot27^x-28\cdot15^x+28\cdot9^x+9\cdot5^x-3^{x+2}\le0",
        ),
        (
            "grouped_quadratic",
            r"3\cdot45^{x+1000000000000}-3\cdot27^x-28\cdot15^x+28\cdot9^x+9\cdot5^x-3^{x+2}\le0",
        ),
    ],
)
def test_unknown_degrees_domains_coefficients_and_offsets_fail_closed(method, formula):
    with pytest.raises(UnsupportedCondition):
        ANALYSES[method](formula)


@pytest.mark.parametrize("group", METHODS)
@pytest.mark.parametrize(
    "change",
    ("answer", "solution", "asset", "instruction", "parent", "other_method_parent"),
)
def test_only_condition_computes_answer_and_parent_methods_remain_isolated(
    group, change
):
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
