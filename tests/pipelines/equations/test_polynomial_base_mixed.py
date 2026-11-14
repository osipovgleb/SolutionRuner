"""Both polynomial base cases and the exact sign/domain chart of the heterogeneous quotient."""

import hashlib
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

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.polynomial_base_mixed_figures import (
    SOURCES,
    compatible,
)
from solution_runner.pipelines.equations.polynomial_logarithm_cases import (
    PolynomialLogCases,
    analyze,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("polynomial_base_mixed_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
R = sp.sqrt(13)
MANUAL = {
    "520497": sp.Union(
        sp.Interval.open(-5, -4),
        sp.Interval.open(-4, -3),
        sp.Interval.Ropen(-sp.Rational(2, 3), (1 - R) / 6),
        sp.Interval.Lopen((1 + R) / 6, 1),
    ),
    "520517": sp.Union(
        sp.Interval(-sp.oo, -sp.Rational(7, 3)),
        sp.Interval.Ropen(0, 2),
        sp.Interval.open(4, sp.oo),
    ),
    "520701": sp.Union(sp.Interval.Lopen(-5, -1), sp.Interval(1, sp.oo)),
}


def handler():
    return get_handler(get_group_profile("520497").content_rule_key)


def plan(row, context=None, parent=PARENT):
    ctx = _with_required_assets(
        row["context"] if context is None else context, handler().key
    )
    return handler().plan(PlanInput(ctx, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_three_manual_answers_and_original_values(row):
    a = analyze(read_formula(row["context"])[1])
    expected = MANUAL[row["task"]]
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    points = [sp.Rational(i, 8) for i in range(-48, 49)] + [
        sp.Rational(-2, 3),
        sp.Rational(-7, 3),
    ]
    for point in points:
        if isinstance(a, PolynomialLogCases):
            B = sp.simplify(a.base.subs(X, point))
            Q = sp.simplify(a.argument.subs(X, point))
            if B <= 0 or B == 1 or Q <= 0:
                assert not a.domain.contains(point)
                continue
            value = math.log(float(Q), float(B))
            direct = value <= 1e-12 if a.operator == "<=" else value >= -1e-12
        else:
            Q = a.radicand.subs(X, point)
            if Q <= 0:
                assert not a.domain.contains(point)
                continue
            value = float(sp.N(a.numerator.subs(X, point), 50))
            direct = value >= -1e-12
        assert bool(a.solution.contains(point)) == direct
    if isinstance(a, PolynomialLogCases):
        domain = sp.solve_univariate_inequality(
            a.base > 0, X, relational=False
        ).intersect(
            sp.solve_univariate_inequality(a.argument > 0, X, relational=False)
        ) - sp.FiniteSet(*sp.solve(a.base - 1, X))
        same_set(a.domain, domain)
        assert tuple(c[0] for c in a.cases) == (-1, 1)
    else:
        assert (
            a.points == (-1, 1)
            and a.thresholds == (sp.Rational(1, 2), 7)
            and a.bases == (2, 7)
        )
        assert (
            not a.domain.contains(-5)
            and a.solution.contains(-1)
            and a.solution.contains(1)
        )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_order_required_extension_native_reuse_readonly_and_replay(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == before and not handler().diagram_specs(ctx)
    if row["task"] == "520701":
        uid = ctx["normalized_content"]["assets"][0]["asset_id"]
        assert uid in p.solution_html and p.solution_html.count("<img ") == 1
        assert (
            p.solution_html.index("разложим числитель")
            < p.solution_html.index("<img ")
            < p.solution_html.index("Нули числителя")
            < p.solution_html.index("строго положительным")
            < p.solution_html.index("множителя возрастают")
        )
    else:
        assert "<img" not in p.solution_html
        assert (
            p.solution_html.index("Первый случай")
            < p.solution_html.index("Второй случай")
            < p.solution_html.index("Объединяя")
        )
        if row["task"] == "520517":
            assert "решений нет" in p.solution_html
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
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
    assert all(
        asset in ctx["normalized_content"]["assets"]
        for asset in before["normalized_content"]["assets"]
    )


def test_every_native_marker_sign_domain_and_selection_is_certified_and_sha_exact():
    row = ROWS[2]
    a = analyze(read_formula(row["context"])[1])
    uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = SOURCES["figures"][uid]
    assert compatible(entry, a)
    import solution_runner.pipelines.equations.polynomial_base_mixed_figures as figures

    svg = (
        Path(figures.__file__).parent / "assets/logarithmic-inequalities" / f"{uid}.svg"
    )
    assert hashlib.sha256(svg.read_bytes()).hexdigest() == entry["sha256"]
    assert (
        entry["points"] == ["-5", "-1", "1"]
        and entry["closed"] == [False, True, True]
        and entry["signs"] == [None, 1, -1, 1]
    )
    for key, value in [
        ("points", ["-4", "-1", "1"]),
        ("closed", [True, True, True]),
        ("signs", [None, -1, 1, -1]),
        ("domain", "Interval(-5,oo)"),
        ("solution", "Interval(-5,oo)"),
        ("operator", ">"),
        ("role", "numerator_only"),
    ]:
        changed = {**entry, key: value}
        assert not compatible(changed, a)


def test_missing_exact_source_chart_is_restored_without_a_generated_duplicate():
    row = ROWS[2]
    ctx = deepcopy(row["context"])
    uid = ctx["normalized_content"]["assets"][0]["asset_id"]
    ctx["normalized_content"]["assets"] = []
    restored = _with_required_assets(ctx, handler().key)
    assert restored["normalized_content"]["assets"][0][
        "asset_id"
    ] == uid and not handler().diagram_specs(restored)
    assert uid in plan(row, restored).solution_html


@pytest.mark.parametrize("part", ["base", "argument"])
def test_logarithm_cases_preserve_hidden_original_poles(part):
    formula = read_formula(ROWS[0]["context"])[1]
    before = "(x+4)^{2}" if part == "base" else "3x^{2}-x-1"
    replacement = before + r"+\frac{x-1}{x-1}-1"
    assert before in formula
    a = analyze(formula.replace(before, replacement, 1))
    assert 1 in a.poles and not a.solution.contains(1)
    same_set(a.solution, MANUAL["520497"] - sp.FiniteSet(1))


def test_hidden_root_hole_is_retained_and_an_incompatible_unmarked_source_chart_rejected():
    formula = read_formula(ROWS[2]["context"])[1].replace(
        "x+5", r"x+5+\frac{x-2}{x-2}-1"
    )
    a = analyze(formula)
    assert 2 in a.poles and not a.domain.contains(2)
    same_set(a.solution, MANUAL["520701"] - sp.FiniteSet(2))
    assert not any(compatible(e, a) for e in SOURCES["figures"].values())


def test_root_quotient_requires_the_whole_positive_root_and_closed_zero_boundaries():
    formula = read_formula(ROWS[2]["context"])[1]
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace(r"\ge", r"\gt"))
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace("x+5", "5-x"))
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace("14^{x}", "15^{x}"))
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace("14\\cdot 2", "13\\cdot 2"))


@pytest.mark.parametrize(
    "before,after",
    [
        ("(x+4)^{2}", "(x+4)^2+1"),
        ("3x^{2}-x-1", "-3x^2-x-1"),
        ("3x^{2}-x-1", "3x^2-x-1+2^x"),
        (r"\le 0", r"\le 1"),
    ],
)
def test_polynomial_log_whole_shape_and_method_guards(before, after):
    formula = read_formula(ROWS[0]["context"])[1]
    assert before in formula
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace(before, after, 1))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_parent_asset_and_instruction_guards(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), MANUAL[row["task"]])
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
