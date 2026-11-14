"""Original root and logarithm domains, justified squaring and exact inverse images."""

import json
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
from solution_runner.pipelines.equations.logarithm_radical import analyze
from solution_runner.pipelines.equations.logarithm_rational_substitution import (
    solution_images,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_radical_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "507779": (
        8,
        4,
        1,
        2,
        sp.Union(sp.Interval.Ropen(1 / sp.sqrt(8), 1), sp.Interval.open(1, sp.sqrt(8))),
    ),
    "507786": (
        2,
        8,
        2,
        1,
        sp.Union(
            sp.Interval.Ropen(2 ** (-sp.sqrt(2) / 4), 1),
            sp.Interval.open(1, 2 ** sp.Rational(1, 3)),
        ),
    ),
    "511489": (
        4,
        4,
        1,
        2,
        sp.Union(sp.Interval.Ropen(sp.Rational(1, 2), 1), sp.Interval.open(1, 2)),
    ),
}


def handler():
    return get_handler(get_group_profile("507779").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_originals_against_manual_answer_and_independent_two_case_oracle(row):
    a = analyze(read_formula(row["context"])[1])
    base, alpha, c, r, expected = MANUAL[row["task"]]
    assert (a.base, a.scale, a.coefficient, a.bound) == (
        base,
        c,
        sp.Rational(alpha, c * c),
        r,
    )
    q = 1 - sp.Rational(alpha, c * c) * X**2
    side = 1 - r * X

    def solve(expr):
        return sp.solve_univariate_inequality(expr, X, relational=False)

    domain = solve(q >= 0) - sp.FiniteSet(0)
    negative = domain.intersect(solve(X < 0)).intersect(solve(q - side**2 < 0))
    positive = domain.intersect(solve(X > 0)).intersect(solve(q - side**2 > 0))
    same_set(a.negative, negative)
    same_set(a.positive, positive)
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    assert not a.solution.contains(1) and not a.domain.contains(0)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_unsquared_root_values_and_real_domain(row):
    a = analyze(read_formula(row["context"])[1])
    _base, alpha, c, r, _expected = MANUAL[row["task"]]
    radius = 1 / sp.sqrt(alpha)
    for L in (-radius, -radius / 2, sp.Integer(0), radius / 2, radius, 2 * radius):
        radicand = sp.simplify(1 - alpha * L**2)
        if L == 0 or radicand < 0:
            if L == 0:
                assert not a.solution.contains(1)
            continue
        original = (1 - sp.sqrt(radicand)) / (c * L)
        expected = bool(sp.simplify(original - r) < 0)
        working = c * L
        assert bool(a.negative.union(a.positive).contains(working)) == expected
    assert (1 - sp.sqrt(1)) == 0


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_branch_order_readonly_unchanged_input_and_idempotence(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == before
        and "<img" not in p.solution_html
        and not handler().diagram_specs(ctx)
    )
    assert (
        p.solution_html.index("После замены")
        < p.solution_html.index("область определения")
        < p.solution_html.index("две системы")
        < p.solution_html.index("Решим первую")
        < p.solution_html.index("первом случае")
        < p.solution_html.index("Решим вторую")
        < p.solution_html.index("втором случае")
        < p.solution_html.index("Объединяя")
    )
    assert "x=1" in p.solution_html
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


def test_logarithm_zero_level_maps_to_one_instead_of_exponential_inverse_infinity():
    assert solution_images(sp.Integer(2), sp.FiniteSet(0)) == [
        (sp.FiniteSet(0), sp.FiniteSet(1))
    ]


def test_exact_algebraic_log_levels_can_have_transcendental_image_endpoints():
    values = sp.Interval.Ropen(-sp.sqrt(2) / 4, 0)
    images = solution_images(sp.Integer(2), values)
    assert images == [(values, sp.Interval.Ropen(2 ** (-sp.sqrt(2) / 4), 1))]


def test_shared_root_domain_endpoint_is_strict_only_on_positive_branch():
    a = analyze(read_formula(ROWS[0]["context"])[1])
    assert a.negative.contains(-sp.Rational(1, 2)) and not a.positive.contains(
        sp.Rational(1, 2)
    )
    assert a.negative_image.contains(1 / sp.sqrt(8)) and not a.positive_image.contains(
        sp.sqrt(8)
    )


def test_positive_squaring_side_is_proved_on_the_entire_parent_domain():
    for row in ROWS:
        a = analyze(read_formula(row["context"])[1])
        assert a.bound**2 <= a.coefficient
        assert sp.simplify(1 - a.bound / sp.sqrt(a.coefficient)) >= 0
    with pytest.raises(UnsupportedCondition):
        analyze(r"\frac{1-\sqrt{1-4\log_8^2 x}}{\log_8 x}\lt3")


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{1-\sqrt{1-4\log_8^2 x}}{\log_8 x}\le2",
        r"\frac{1-\sqrt{1-4\log_8^2 x}}{\log_4 x}\lt2",
        r"\frac{1-\sqrt{1-4\log_8^2 x}}{\log_8 x}+1\lt2",
        r"\frac{2-\sqrt{1-4\log_8^2 x}}{\log_8 x}\lt2",
        r"\frac{1-\sqrt{2-4\log_8^2 x}}{\log_8 x}\lt2",
        r"\frac{1-\sqrt{1-4\log_8^2 x}}{\log_8 x+1}\lt2",
        r"\frac{1-\sqrt{1-4\log_8^2 (x+1)}}{\log_8 x}\lt2",
        r"\frac{1-\sqrt{1-4\log_8^2 (\frac{x(x-2)}{x-2})}}{\log_8 x}\lt2",
        r"\frac{1-\sqrt{1-4\log_8^2 x+\frac{\log_8 x-1/4}{\log_8 x-1/4}-1}}{\log_8 x}\lt2",
        r"\frac{1-\sqrt{1-4\log_8^2 x+x}}{\log_8 x}\lt2",
        r"\frac{1-\sqrt{1-4\log_8^2 x}}{\log_8 x}\lt0",
        r"\frac{1-\sqrt{1-4\log_8^2 x}}{\log_8 x}\lt2\lt3",
    ],
)
def test_whole_log_root_quotient_original_poles_and_parent_method_guards(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_saved_answer_parent_assets_and_instruction_guards():
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], parent=PARENT + " ")
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)
    ctx = deepcopy(ROWS[0]["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(ROWS[0], ctx).answer == plan(ROWS[0]).answer
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Дополнительно x&gt;1</p>"
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)
