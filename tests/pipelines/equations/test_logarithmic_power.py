"""Proven positive-variable identities, strict endpoints and both parent methods."""

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
from solution_runner.pipelines.equations.logarithmic_power import analyze
from solution_runner.pipelines.equations.logarithmic_power_input import T
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithmic_power_sources.json")
    .read_text()
)
PARENTS = {
    r["method"]: next(
        s["html"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for r in ROWS
    if r["task"] == r["group"]
}
MANUAL = {
    "508458": (9, 10, sp.Rational(1, 2), ">=", sp.Interval(sp.sqrt(10), sp.oo)),
    "508460": (9, 10, -sp.Rational(1, 2), "<=", sp.Interval.Lopen(0, 1 / sp.sqrt(10))),
    "511540": (4, 10, sp.Rational(1, 2), ">=", sp.Interval(sp.sqrt(10), sp.oo)),
    "508471": (
        5,
        5,
        sp.Rational(1, 4),
        ">=",
        sp.Union(sp.Interval.Lopen(0, 1 / sp.sqrt(5)), sp.Interval(sp.sqrt(5), sp.oo)),
    ),
    "508473": (
        3,
        3,
        sp.Rational(1, 4),
        ">",
        sp.Union(
            sp.Interval.open(0, 1 / sp.sqrt(3)), sp.Interval.open(sp.sqrt(3), sp.oo)
        ),
    ),
    "511547": (
        4,
        4,
        sp.Rational(1, 4),
        ">=",
        sp.Union(sp.Interval.Lopen(0, sp.Rational(1, 2)), sp.Interval(2, sp.oo)),
    ),
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def plan(row, context=None, parent=None):
    return handler(row).plan(
        PlanInput(
            row["context"] if context is None else context,
            parent_solution_html=PARENTS[row["method"]] if parent is None else parent,
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_six_originals_manual_answers_and_independent_coordinate_oracle(row):
    a = analyze(read_formula(row["context"])[1], row["method"])
    base, reference, level, operator, expected = MANUAL[row["task"]]
    assert (a.base, a.reference, a.level, a.operator) == (
        base,
        reference,
        level,
        operator,
    )
    p = X if row["method"] == "linear_reciprocity" else X**2
    compare = {">=": p >= level, ">": p > level, "<=": p <= level, "<": p < level}[
        operator
    ]
    oracle = sp.solve_univariate_inequality(compare, X, relational=False)
    same_set(a.inverse.stage.solution, oracle)
    same_set(a.inverse.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    assert not a.inverse.solution.contains(0)
    assert a.exponent == (T if row["method"] == "linear_reciprocity" else T**2)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_power_values_at_positive_samples_including_one(row):
    a = analyze(read_formula(row["context"])[1], row["method"])
    for x in (
        sp.Rational(1, 10),
        sp.Rational(1, 2),
        sp.Integer(1),
        sp.Integer(2),
        sp.Integer(10),
    ):
        if row["method"] == "linear_reciprocity":
            p = 3 if a.base == 9 else 2
            original = sp.Integer(a.base) ** (sp.log(x) / sp.log(10)) + x ** (
                2 * sp.log(p) / sp.log(10)
            )
        else:
            t = sp.log(x) / sp.log(a.reference)
            original = sp.Integer(a.base) ** t**2 + x**t
        simplified = 2 * sp.Integer(a.base) ** a.exponent.subs(
            T, sp.log(x) / sp.log(a.reference)
        )
        assert abs((original - simplified).evalf(50)) < sp.Rational(1, 10) ** 40
        difference = (original - a.right).evalf(50)
        if abs(difference) > sp.Rational(1, 10) ** 40:
            op = a.operator
            expected = {
                ">=": difference > 0,
                ">": difference > 0,
                "<=": difference < 0,
                "<": difference < 0,
            }[op]
            assert bool(a.inverse.solution.contains(x)) == bool(expected)
    # x=1 belongs to the original domain even though it need not satisfy the inequality.
    assert a.inverse.domain.contains(1)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_method_order_clean_tex_readonly_and_idempotence(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == before
        and "<img" not in p.solution_html
        and not handler(row).diagram_specs(ctx)
    )
    assert (
        p.solution_html.index("условии")
        < p.solution_html.index("Неравенство принимает вид")
        < p.solution_html.index("сравниваем показатели")
        < p.solution_html.index("Возвращаясь")
    )
    assert ("Приведём второе" in p.solution_html) == (
        row["method"] == "square_coordinate"
    )
    soup = BeautifulSoup(p.solution_html, "html.parser")
    formulas = [e["data-inline-latex"] for e in soup.select("[data-inline-latex]")]
    assert all(r"\mathtt" not in f and r"\textbackslash" not in f for f in formulas)
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=PARENTS[row["method"]],
    )
    assert (
        record["status"] == "prepared"
        and record["transformations"] == list(p.transformations)
        and gateway.reads == [ctx["problem_id"]]
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


def test_strict_quadratic_comparison_excludes_both_boundary_points():
    row = next(r for r in ROWS if r["task"] == "508473")
    a = analyze(read_formula(row["context"])[1], row["method"])
    assert not a.inverse.solution.contains(
        sp.sqrt(3)
    ) and not a.inverse.solution.contains(1 / sp.sqrt(3))


def test_square_method_also_handles_the_opposite_comparison_direction():
    a = analyze(r"5^{\log_{5}^{2}x}+x^{\log_{5}x}\le2\sqrt[4]{5}", "square_coordinate")
    same_set(a.inverse.solution, sp.Interval(1 / sp.sqrt(5), sp.sqrt(5)))


def test_linear_method_handles_a_strict_upper_bound():
    a = analyze(r"9^{\lg x}+x^{2\lg 3}\lt\frac{2}{3}", "linear_reciprocity")
    same_set(a.inverse.solution, sp.Interval.open(0, 1 / sp.sqrt(10)))


@pytest.mark.parametrize(
    "formula,method",
    [
        (r"9^{\lg x}+x^{2\lg 2}\ge6", "linear_reciprocity"),
        (r"9^{\lg x}+x^{2\lg 3}+1\ge6", "linear_reciprocity"),
        (r"9^{\lg x}+x^{2\lg 3}\ge x", "linear_reciprocity"),
        (r"9^{\lg x}+x^{2\lg 3}\ge0", "linear_reciprocity"),
        (r"9^{\lg x}+x^{2\lg 3}\ge6\ge0", "linear_reciprocity"),
        (r"9^{\lg x}+x^{2\lg 3}\ge2\sqrt{2}", "linear_reciprocity"),
        (r"9^{\lg(x^2)}+x^{2\lg 3}\ge6", "linear_reciprocity"),
        (r"9^{\lg(\frac{x(x-1)}{x-1})}+x^{2\lg 3}\ge6", "linear_reciprocity"),
        (r"9^{\lg x}+\frac{x-1}{x-1}x^{2\lg 3}\ge6", "linear_reciprocity"),
        (r"5^{\log_{5}^{2}x}+x^{\log_{3}x}\ge2\sqrt[4]{5}", "square_coordinate"),
        (r"5^{\log_{5}^{2}x}+x^{\log_{5}x+1}\ge2\sqrt[4]{5}", "square_coordinate"),
        (r"5^{\log_{5}x}+x^{\log_{5}x}\ge2\sqrt[4]{5}", "square_coordinate"),
        (r"5^{\log_x^{2}x}+x^{\log_x x}\ge2\sqrt[4]{5}", "square_coordinate"),
        (r"(2^{40})^{40}+x^{2\lg 3}\ge6", "linear_reciprocity"),
    ],
)
def test_whole_identity_reference_domain_and_bound_guards(formula, method):
    with pytest.raises(UnsupportedCondition):
        analyze(formula, method)


@pytest.mark.parametrize("row", [ROWS[0], ROWS[3]], ids=lambda r: r["task"])
def test_parent_asset_extra_instruction_and_saved_answer_guards(row):
    other = (
        "square_coordinate"
        if row["method"] == "linear_reciprocity"
        else "linear_reciprocity"
    )
    with pytest.raises(UnsupportedCondition):
        plan(row, parent=PARENTS[other])
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(row, ctx).answer == plan(row).answer
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Дополнительно x&gt;1</p>"
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
