"""All four heterogeneous originals, exact radical-base signs and forbidden base one."""

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
from solution_runner.pipelines.equations.logarithm_monotonic import (
    RadicalRange,
    analyze,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_monotonic_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "513429": sp.Interval.Ropen(0, sp.log(5) / sp.log(2)),
    "513448": sp.Interval.Ropen(1, sp.log(7) / sp.log(2)),
    "514188": sp.Interval.Ropen(1, sp.log(7) / sp.log(2)),
    "513626": sp.Union(
        sp.Interval.Lopen(sp.Rational(5, 2), sp.Rational(13, 5)),
        sp.Interval.open(3, sp.oo),
    ),
}


def handler():
    return get_handler(get_group_profile("513429").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_four_original_answers_domains_and_direct_logarithms(row):
    a = analyze(read_formula(row["context"])[1])
    expected = MANUAL[row["task"]]
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    for point in [sp.Rational(i, 4) for i in range(-8, 21)] + [sp.Rational(13, 5)]:
        if isinstance(a, RadicalRange):
            q = a.offset - a.exponential_base**point
            if q <= 0:
                assert not a.domain.contains(point)
                continue
            left = math.log(float(a.constant), float(a.base))
            right = math.log(float(q), float(a.base))
            assert bool(a.solution.contains(point)) == (left >= right - 1e-10)
        else:
            B = a.base.subs(X, point)
            Q = a.argument.subs(X, point)
            if B <= 0 or B == 1:
                assert not a.domain.contains(point)
                continue
            value = float(a.coefficient.subs(X, point)) * math.log(float(Q), float(B))
            assert bool(a.solution.contains(point)) == (value >= -1e-12)
    if isinstance(a, RadicalRange):
        p, q = a.radicals
        r = a.denominator
        H = r * r + p - q
        assert r * r > p and H > 0 and H * H < 4 * r * r * p
        assert not a.domain.contains(a.upper) and a.solution.contains(a.lower)
        assert r"\log_{2}" in a.answer
    else:
        assert a.stage.solution.contains(3) and not a.solution.contains(3)
        assert not a.domain.contains(sp.Rational(5, 2))
        same_set(a.solution, a.stage.solution.intersect(a.domain))
        assert a.argument.subs(X, 3) == 1 and a.base.subs(X, 3) == 1


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_monotonic_strategy_extension_readonly_unchanged_input_and_replay(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == before
        and "<img" not in p.solution_html
        and not handler().diagram_specs(ctx)
    )
    if row["task"] == "513626":
        assert (
            p.solution_html.index("основание логарифма зависит")
            < p.solution_html.index("область определения")
            < p.solution_html.index("Выделим квадрат")
            < p.solution_html.index("При основании больше")
            < p.solution_html.index("При основании между")
            < p.solution_html.index("Объединяя")
        )
        assert "Эта точка запрещена" in p.solution_html
    else:
        assert (
            p.solution_html.index("возведениях в квадрат")
            < p.solution_html.index("функция возрастает")
            < p.solution_html.index("Показательная функция")
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


@pytest.mark.parametrize(
    "before,after",
    [
        (r"\frac{\sqrt{2}+\sqrt{13}}{5}", r"\frac{(\sqrt{2}+\sqrt{13})(x-1)}{5(x-1)}"),
        (r"} 4", r"} (4+\frac{x-1}{x-1}-1)"),
        ("5-2^{x}", r"5-2^x+\frac{x-1}{x-1}-1"),
    ],
)
def test_cancelled_original_holes_in_radical_base_and_both_arguments_remain(
    before, after
):
    formula = read_formula(ROWS[0]["context"])[1]
    assert before in formula
    a = analyze(formula.replace(before, after, 1))
    assert 1 in a.poles and not a.domain.contains(1)
    same_set(a.solution, MANUAL["513429"] - sp.FiniteSet(1))


def test_variable_base_argument_hole_removes_an_otherwise_valid_zero_coefficient():
    row = next(r for r in ROWS if r["task"] == "513626")
    formula = read_formula(row["context"])[1]
    a = analyze(
        formula.replace(
            "x^{2}-6x+10", r"x^2-6x+10+\frac{x-\frac{13}{5}}{x-\frac{13}{5}}-1"
        )
    )
    assert sp.Rational(13, 5) in a.poles and not a.solution.contains(sp.Rational(13, 5))
    same_set(a.solution, MANUAL["513626"] - sp.FiniteSet(sp.Rational(13, 5)))


def test_variable_base_hole_is_not_rescued_by_the_logarithm_sign_reduction():
    row = next(r for r in ROWS if r["task"] == "513626")
    formula = read_formula(row["context"])[1]
    a = analyze(formula.replace("2x-5", r"2x-5+\frac{x-4}{x-4}-1"))
    assert 4 in a.poles and not a.domain.contains(4)
    same_set(a.solution, MANUAL["513626"] - sp.FiniteSet(4))


@pytest.mark.parametrize(
    "before,after",
    [
        (r"\sqrt{13}", r"\sqrt{12}"),
        (r"\sqrt{2}+\sqrt{13}", r"\sqrt{2}+\sqrt{3}+\sqrt{13}"),
        ("} 4", "} 10"),
        ("5-2^{x}", "5-2^{2x}"),
        ("5-2^{x}", "5-2*2^x"),
        (r"\ge", r"\gt"),
        (r"\ge", r"\le"),
    ],
)
def test_exact_base_proof_whole_argument_shape_and_operator_guards(before, after):
    formula = read_formula(ROWS[0]["context"])[1]
    assert before in formula
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace(before, after))


@pytest.mark.parametrize(
    "before,after",
    [
        ("x^{2}-6x+10", "x^2-6x+11"),
        ("2x-5", "2x-4"),
        ("5x-13", "-5x+13"),
        ("5x-13", "5x-20"),
        (r"\ge 0", r"\ge 1"),
        (r"\ge", r"\le"),
    ],
)
def test_variable_product_domain_square_and_case_sign_guards(before, after):
    row = next(r for r in ROWS if r["task"] == "513626")
    formula = read_formula(row["context"])[1]
    assert before in formula
    with pytest.raises(UnsupportedCondition):
        analyze(formula.replace(before, after))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_parent_assets_and_instruction_guards(row):
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
