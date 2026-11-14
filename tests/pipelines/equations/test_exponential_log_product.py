"""Original product values, a shared double zero and exact optional source charts."""

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
from solution_runner.pipelines.equations.exponential_log_product import analyze
from solution_runner.pipelines.equations.exponential_log_product_figures import (
    SOURCES,
    compatible,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_log_product_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "562040": (
        2,
        sp.Integer(2),
        sp.Integer(2),
        sp.Rational(1, 2),
        sp.Union(sp.FiniteSet(-1), sp.Interval(2 ** sp.Rational(1, 4) - 2, sp.oo)),
    ),
    "562043": (
        5,
        sp.Rational(1, 2),
        sp.Integer(1),
        sp.Integer(2),
        sp.Union(
            sp.Interval.open(-sp.Rational(1, 2), sp.Rational(1, 2)),
            sp.Interval.open(sp.Rational(1, 2), sp.Rational(49, 2)),
        ),
    ),
    "563337": (
        5,
        sp.Rational(1, 2),
        sp.Rational(1, 2),
        sp.Integer(2),
        sp.Union(
            sp.Interval.open(-sp.Rational(1, 2), sp.Rational(1, 2)),
            sp.Interval.open(sp.Rational(1, 2), sp.Rational(1249, 2)),
        ),
    ),
}


def handler():
    return get_handler(get_group_profile("562040").content_rule_key)


def plan(row, context=None, parent=PARENT):
    ctx = _with_required_assets(
        row["context"] if context is None else context, handler().key
    )
    return handler().plan(PlanInput(ctx, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_originals_independent_manual_solutions_and_logarithm_factor(row):
    a = analyze(read_formula(row["context"])[1])
    b, s, A, B, expected = MANUAL[row["task"]]
    assert a.base == b and a.shift == s and a.argument == X + s
    assert a.exponents == (1 - X - s, X + s - 1)
    assert a.log_polynomial == A * X**2 - B * X and a.level == B / A
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    assert a.points == (-s, 1 - s, sp.Integer(b) ** (B / A) - s) and a.signs == (
        1,
        1,
        -1,
    )
    assert not a.solution.contains(-s)
    # A separate cubic in t has the same sign as the original product on its domain.
    t = sp.Symbol("t", real=True)
    poly = -(t**2) * (t - B / A)
    oracle = sp.solve_univariate_inequality(
        {"<=": poly <= 0, ">": poly > 0}[a.operator], t, relational=False
    )
    for value in (sp.Integer(-1), sp.Integer(0), B / (2 * A), B / A, B / A + 1):
        x = sp.Integer(b) ** value - s
        assert bool(a.solution.contains(x)) == bool(oracle.contains(value))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_unsimplified_original_product_domain_and_all_three_sign_intervals(row):
    a = analyze(read_formula(row["context"])[1])
    b, s, A, B, _expected = MANUAL[row["task"]]
    for x in (
        -s,
        -s + sp.Rational(1, 4),
        1 - s,
        (a.shared_zero + a.second_zero) / 2,
        a.second_zero,
        a.second_zero + 1,
    ):
        u = x + s
        if u <= 0:
            assert not a.domain.contains(x) and not a.solution.contains(x)
            continue
        e = (
            sp.Integer(b) * sp.Rational(1, b) ** u
            - sp.Rational(1, b) * sp.Integer(b) ** u
        )
        l = sp.simplify(
            A * (sp.log(u) / sp.log(sp.Rational(1, b))) ** 2 - B * sp.log(u) / sp.log(b)
        )
        value = (e * l).evalf(50)
        if abs(value) < sp.Rational(1, 10) ** 35:
            expected = a.operator in ("<=", ">=")
        else:
            expected = value < 0 if a.operator in ("<=", "<") else value > 0
        assert bool(a.solution.contains(x)) == bool(expected)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_order_readonly_idempotence_and_preserved_source_assets(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == before and not handler().diagram_specs(ctx)
    assert (
        p.solution_html.index("Преобразуем")
        < p.solution_html.index("Область определения")
        < p.solution_html.index("Найдём нули первого")
        < p.solution_html.index("Найдём нули второго")
        < p.solution_html.index("Упорядочим")
        < p.solution_html.index("Применим метод интервалов")
    )
    assert p.solution_html.count("<img ") == (0 if row["task"] == "562040" else 1)
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
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]


@pytest.mark.parametrize("row", ROWS[1:], ids=lambda r: r["task"])
def test_exact_native_chart_reuse_restoration_and_mathematical_certification(row):
    ctx = deepcopy(row["context"])
    a = analyze(read_formula(ctx)[1])
    uid = ctx["normalized_content"]["assets"][0]["asset_id"]
    assert compatible(SOURCES["figures"][uid], a) and uid in plan(row).solution_html
    ctx["normalized_content"]["assets"] = []
    restored = _with_required_assets(ctx, handler().key)
    assert restored["normalized_content"]["assets"][0]["asset_id"] == uid
    assert uid in plan(row, ctx).solution_html


def test_child_exponential_identity_uses_correct_half_integer_offsets():
    a = analyze(read_formula(ROWS[1]["context"])[1])
    assert a.exponents == (sp.Rational(1, 2) - X, X - sp.Rational(1, 2))
    for x in (sp.Integer(0), sp.Rational(1, 2), sp.Integer(1)):
        original = 5 * sp.Rational(1, 5) ** (x + sp.Rational(1, 2)) - sp.Rational(
            1, 5
        ) * 5 ** (x + sp.Rational(1, 2))
        normalized = 5 ** a.exponents[0].subs(X, x) - 5 ** a.exponents[1].subs(X, x)
        assert sp.simplify(original - normalized) == 0


@pytest.mark.parametrize("operator", ["<", "<=", ">", ">="])
def test_shared_zero_and_outer_domain_boundary_for_all_comparisons(operator):
    symbols = {"<": r"\lt", "<=": r"\le", ">": r"\gt", ">=": r"\ge"}
    formula = read_formula(ROWS[0]["context"])[1].replace(r"\leq", symbols[operator])
    a = analyze(formula)
    assert a.operator == operator
    assert bool(a.solution.contains(a.shared_zero)) == operator.endswith("=")
    assert bool(a.solution.contains(a.second_zero)) == operator.endswith("=")
    assert not a.solution.contains(-a.shift)


@pytest.mark.parametrize(
    "formula",
    [
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(x+2)-0.5\log_2(x+2))\le1",
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(x+2)-0.5\log_2(x+2))+1\le0",
        r"(2\cdot0.5^{x+3}-0.5\cdot2^{x+3})(2\log_{0.5}^{2}(x+2)-0.5\log_2(x+2))\le0",
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(x+3)-0.5\log_2(x+2))\le0",
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(x+2)-0.5\log_3(x+2))\le0",
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(x+2)+0.5\log_2(x+2))\le0",
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(x+2)-0.5\log_2(x+2)+1)\le0",
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(2x+2)-0.5\log_2(2x+2))\le0",
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(\frac{(x+2)(x-1)}{x-1})-0.5\log_2(x+2))\le0",
        r"(2\cdot0.5^{x+2}-0.5\cdot2^{x+2})(2\log_{0.5}^{2}(x+2)-0.5\log_2(x+2))\le0\le1",
    ],
)
def test_whole_product_shape_original_domain_and_parent_method_guards(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_changing_strictness_invalidates_the_all_open_native_chart():
    ctx = deepcopy(ROWS[1]["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    section["html"] = (
        section["html"].replace("&gt;0", r"\ge0").replace("&gt; 0", r"\ge 0")
    )
    # Change the formula itself rather than relying on source HTML entity formatting.
    soup = BeautifulSoup(section["html"], "html.parser")
    span = soup.select_one("[data-inline-latex]")
    span["data-inline-latex"] = (
        span["data-inline-latex"].replace(">0", r"\ge0").replace("> 0", r"\ge 0")
    )
    section["html"] = str(soup)
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[1], ctx)


def test_parent_metadata_and_saved_answer_guards():
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], parent=PARENT + " ")
    ctx = deepcopy(ROWS[1]["context"])
    ctx["normalized_content"]["assets"][0]["url"] = "/assets/wrong"
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[1], ctx)
    ctx = deepcopy(ROWS[0]["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(ROWS[0], ctx).answer == plan(ROWS[0]).answer
