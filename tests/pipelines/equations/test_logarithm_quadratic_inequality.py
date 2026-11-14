"""Check complete source cases, exact inverse branches and the read-only contract."""

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
from solution_runner.pipelines.equations.logarithm_quadratic_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_quadratic_inequality_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for row in ROWS
    if row["task"] == row["group"]
    for s in row["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
EXPECTED = {
    "508459": sp.Union(sp.Interval.open(0, 4), sp.Interval.open(8, sp.oo)),
    "508461": sp.Union(
        sp.Interval.open(0, sp.Rational(1, 8)),
        sp.Interval.open(sp.Rational(1, 4), sp.oo),
    ),
    "508472": sp.Union(sp.Interval.open(0, 3), sp.Interval.open(9, sp.oo)),
    "508474": sp.Union(sp.Interval.Lopen(0, 4), sp.Interval(8, sp.oo)),
    "511541": sp.Union(
        sp.Interval.open(0, sp.Rational(1, 4)), sp.Interval.open(256, sp.oo)
    ),
}


def handler():
    return get_handler(get_group_profile("508459").content_rule_key)


def plan(context, parent=PARENT):
    return handler().plan(PlanInput(context, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_original_answers_and_independent_numeric_logarithms(row):
    a = analyze(read_formula(row["context"])[1])
    same_set(a.solution, EXPECTED[row["task"]])
    same_set(answer_set(row["expected_answer"]), a.solution)
    assert a.domain == sp.Interval.open(0, sp.oo)
    x = next(iter(a.argument.free_symbols))
    for value in (
        sp.Rational(1, 16),
        sp.Rational(1, 4),
        1,
        3,
        4,
        6,
        8,
        9,
        16,
        256,
        512,
    ):
        log = sp.log(value) / sp.log(a.base)
        coefficients = {
            "508459": (1, -5, 6),
            "508461": (1, 5, 6),
            "508472": (1, -3, 2),
            "508474": (1, -5, 6),
            "511541": (1, -6, -16),
        }[row["task"]]
        direct = sp.N(
            sp.simplify(
                sum(c * log**degree for c, degree in zip(coefficients, (2, 1, 0)))
            ),
            40,
        )
        expected = direct >= 0 if row["task"] == "508474" else direct > 0
        assert bool(a.solution.contains(value)) == bool(expected)
    assert a.argument == x


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_preparation_keeps_conditions_uses_no_assets_and_replays(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(ctx)
    assert ctx == before and not handler().diagram_specs(ctx)
    assert "<img " not in p.solution_html and "t=" not in p.solution_html
    assert "как квадратное относительно логарифма" in p.solution_html
    assert all(
        not v["transformation_target_id"].startswith(("asset:", "section:condition"))
        for v in p.transformations
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
    "formula,expected",
    [
        (
            r"\log_{(0{,}5)}^2 x-3\log_{(0{,}5)}x+2\le 0",
            sp.Interval(sp.Rational(1, 4), sp.Rational(1, 2)),
        ),
        (
            r"\log_2^2(4-x^2)+3\log_{(0{,}5)}(4-x^2)+2\ge 0",
            sp.Union(
                sp.Interval.Lopen(-2, -sp.sqrt(2)),
                sp.FiniteSet(0),
                sp.Interval.Ropen(sp.sqrt(2), 2),
            ),
        ),
        (
            r"\log_2^2(x+1)-\log_2(x+1)-6\ge 0",
            sp.Union(sp.Interval.Lopen(-1, -sp.Rational(3, 4)), sp.Interval(7, sp.oo)),
        ),
    ],
)
def test_decreasing_base_reciprocal_base_and_quadratic_inverse(formula, expected):
    same_set(analyze(formula).solution, expected)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_2^2x+x+2\log_2x-3\ge 0",
        r"\log_2^2x-3\log_3x+2\ge 0",
        r"\log_2^2x-3\log_2(x+1)+2\ge 0",
        r"\log_2^2x-10\log_2x+9\ge 0",
        r"\log_2^2x-2\log_2x+1\ge 0",
        r"\log_2^2x-2\ge 0",
        r"\log_2x+2\ge 0",
        r"\log_2^2\frac{x}{x+1}-3\log_2\frac{x}{x+1}+2\ge 0",
        r"\log_x^2(x+1)-3\log_x(x+1)+2\ge 0",
    ],
)
def test_outside_reviewed_quadratic_grammar_fails_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_parent_and_assets_are_checked_and_original_answer_is_not_calculation():
    ctx = deepcopy(ROWS[0]["context"])
    with pytest.raises(UnsupportedCondition):
        plan(ctx, PARENT + "changed")
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>wrong</p>"
    same_set(answer_set(plan(ctx).answer), EXPECTED[ROWS[0]["task"]])
    ctx["normalized_content"]["assets"] = [{"asset_id": "foreign"}]
    with pytest.raises(UnsupportedCondition):
        plan(ctx)
