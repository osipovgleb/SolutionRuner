"""Exact large-power structure, all log domains, centered markup and source holes."""

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
from solution_runner.pipelines.equations.logarithm_factored_power import analyze
from solution_runner.pipelines.equations.logarithm_factored_power_input import (
    read_context,
)
from solution_runner.pipelines.equations.rational_inequality_parser import X, polynomial
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_factored_power_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "484579": (7, 2, 16, 7, 3, 2),
    "511294": (6, 2, 16, 7, 3, 2),
    "484580": (5, 7, 16, 13, 5, 4),
}
EXPECTED = sp.Union(sp.Interval.open(-sp.oo, -4), sp.Interval.open(4, sp.oo))


def handler():
    return get_handler(get_group_profile("484579").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


def formula(A=7, B=2, N=16, M=7, c=3, d=2):
    p = f"({A}^{{-x^2}}-{c})"
    q = f"({A}^{{-x^2+{N}}}-1)"
    r = f"({A}^{{{M}-x^2}}-{d})"
    return rf"\log_{B}({p}{q})+\log_{B}\frac{{{p}}}{{{q}}}>\log_{B}{r}^2"


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_three_manual_answers_and_original_logarithms_in_exact_source_domains(row):
    a = analyze(read_context(row["context"])[1])
    A, B, N, M, c, d = MANUAL[row["task"]]
    assert (
        a.base,
        a.log_base,
        a.high_shift,
        a.middle_shift,
        a.left_constant,
        a.right_constant,
    ) == (A, B, N, M, c, d)
    same_set(a.solution, EXPECTED)
    same_set(answer_set(plan(row).answer), EXPECTED)
    for point in range(-7, 8):
        t = sp.Rational(A) ** (-point * point)
        P = t - c
        Q = A**N * t - 1
        R = A**M * t - d
        if Q == 0 or P * Q <= 0 or P / Q <= 0 or R == 0:
            assert not a.solution.contains(point)
            continue
        original = math.log(float(P * Q), B) + math.log(float(P / Q), B) > math.log(
            float(R * R), B
        )
        assert bool(a.solution.contains(point)) == original
    assert not a.solution.contains(-4) and not a.solution.contains(4)
    assert a.solution.contains(-5) and a.solution.contains(5)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_method_correct_back_exponent_original_markup_readonly_and_replay(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert (
        ctx == before
        and p.condition_html == condition["html"]
        and "<img" not in p.solution_html
    )
    assert not handler().diagram_specs(ctx)
    assert (
        p.solution_html.index("Сделаем замену")
        < p.solution_html.index("области всех трёх")
        < p.solution_html.index("третья разность также отрицательна")
        < p.solution_html.index("Складываем логарифмы")
        < p.solution_html.index("раскрываем модули")
        < p.solution_html.index("Возвращаемся")
    )
    assert "^{-x^2}" in p.solution_html and "^{(-x)^2}" not in p.solution_html
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


def test_large_power_stays_factored_and_the_old_coefficient_guard_is_unchanged():
    assert 7**16 > 10**12
    with pytest.raises(UnsupportedCondition):
        polynomial(sp.Integer(7) ** 16 * X + 1)
    a = analyze(formula())
    assert a.high_shift == 16 and "33232930569601" not in plan(ROWS[0]).solution_html


@pytest.mark.parametrize("N,M,c,d", [(9, 3, 2, 2), (17, 5, 4, 3), (32, 31, 3, 2)])
def test_bounded_family_reuses_the_same_domain_proof_without_hardcoded_endpoints(
    N, M, c, d
):
    a = analyze(formula(A=10, N=N, M=M, c=c, d=d))
    expected = sp.Union(
        sp.Interval.open(-sp.oo, -sp.sqrt(N)), sp.Interval.open(sp.sqrt(N), sp.oo)
    )
    same_set(a.solution, expected)


@pytest.mark.parametrize("where", ["exponent", "product", "right"])
def test_original_plain_x_holes_survive_symbolic_power_deduplication_and_cancellation(
    where,
):
    text = formula()
    if where == "exponent":
        text = text.replace("-x^2}", r"-x^2+\frac{x-5}{x-5}-1}", 1)
        point = 5
    elif where == "product":
        p = r"(7^{-x^2}-3)(7^{-x^2+16}-1)"
        assert p in text
        text = text.replace(p, p + r"+\frac{x-5}{x-5}-1", 1)
        point = 5
    else:
        text = text.replace(
            r"(7^{7-x^2}-2)^2", r"((7^{7-x^2}-2)^2+\frac{x+5}{x+5}-1)", 1
        )
        point = -5
    a = analyze(text)
    assert point in a.poles and not a.solution.contains(point)
    same_set(a.solution, EXPECTED - sp.FiniteSet(point))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"N": 7, "M": 7},
        {"N": 7, "M": 16},
        {"N": 33},
        {"M": 0},
        {"c": 1},
        {"d": 0},
        {"c": 2, "d": 3},
    ],
)
def test_domain_order_constant_sign_and_resource_bounds_are_required(kwargs):
    with pytest.raises(UnsupportedCondition):
        analyze(formula(**kwargs))


@pytest.mark.parametrize(
    "before,after",
    [
        ("7^{7-x^2}", "6^{7-x^2}"),
        ("-x^2", "x^2"),
        ("7^{7-x^2}-2", "7^{7-x^2}-2+x"),
        ("-1)", "-2)"),
        (">", "\\ge"),
        ("\\log_2", "\\log_1"),
        ("+\\log_2", "-\\log_2"),
    ],
)
def test_whole_power_and_logarithm_identity_is_verified(before, after):
    text = formula()
    assert before in text
    with pytest.raises(UnsupportedCondition):
        analyze(text.replace(before, after))


def test_unknown_typed_source_denominator_is_rejected_even_after_cancellation():
    text = formula().replace(
        r"(7^{7-x^2}-2)^2", r"((7^{7-x^2}-2)^2+\frac{7^{-x^2}-3}{7^{-x^2}-3}-1)"
    )
    with pytest.raises(UnsupportedCondition):
        analyze(text)


@pytest.mark.parametrize(
    "change", ["center_attribute", "visible_formula_text", "extra_instruction"]
)
def test_center_layout_normalization_does_not_drop_meaningful_markup_or_text(change):
    ctx = deepcopy(ROWS[0]["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if change == "center_attribute":
        condition["html"] = condition["html"].replace(
            "<center>", '<center data-extra="1">'
        )
    elif change == "visible_formula_text":
        condition["html"] = condition["html"].replace(
            "></span>", ">Дополнительное условие</span>", 1
        )
    else:
        condition["html"] += "<p>Дополнительное условие x&gt;100.</p>"
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_parent_and_asset_guards(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), EXPECTED)
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель</p>")
    ctx["normalized_content"]["assets"] = [
        {"asset_key": "unknown", "asset_id": "unreviewed"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
