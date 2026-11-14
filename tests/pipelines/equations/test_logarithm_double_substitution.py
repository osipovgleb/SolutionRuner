"""Exact quartic identities, source substitutions and unchanged child diagrams."""

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
from solution_runner.pipelines.equations.logarithm_double_substitution import analyze
from solution_runner.pipelines.equations.logarithm_double_substitution_proof import (
    SOURCES,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_double_substitution_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
PARAMETERS = {
    "514371": (2, 2, -11, 24),
    "519643": (2, 2, -18, 45),
    "658836": (3, 2, -11, 24),
    "658886": (2, 4, -9, -36),
}


def handler():
    return get_handler(get_group_profile("514371").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_manual_quartic_identity_independent_intervals_and_answers(row):
    a = analyze(read_formula(row["context"])[1])
    base, c, b, d = PARAMETERS[row["task"]]
    assert (a.logarithm.base, a.shift, a.linear, a.constant) == (base, c, b, d)
    quartic = (X**2 - c * X) ** 2 + b * (X**2 - c * X) + d
    assert sp.expand(quartic) == a.logarithm.stage.original
    same_set(
        a.logarithm.stage.solution,
        sp.solve_univariate_inequality(quartic < 0, X, relational=False),
    )
    same_set(a.logarithm.domain, sp.Interval.open(0, sp.oo))
    same_set(a.logarithm.solution, answer_set(row["expected_answer"]))
    same_set(answer_set(plan(row).answer), a.logarithm.solution)
    assert [source.start for source, _ in a.logarithm.images] == sorted(
        source.start for source, _ in a.logarithm.images
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithm_expression_at_boundaries_and_between_them(row):
    a = analyze(read_formula(row["context"])[1])
    base, c, b, d = PARAMETERS[row["task"]]
    for exponent in [sp.Rational(n, 4) for n in range(-16, 29)]:
        point = sp.Integer(base) ** exponent
        log = sp.log(point) / sp.log(base)
        value = sp.N(
            sp.simplify((log**2 - c * log) ** 2 + b * (log**2 - c * log) + d), 40
        )
        assert bool(a.logarithm.solution.contains(point)) == bool(value < 0)
    for point in (-1, 0):
        assert a.logarithm.solution.contains(point) is sp.false


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_order_note_readonly_replay_and_original_asset_preservation(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert (
        ctx == original
        and "<img" not in p.solution_html
        and not handler().diagram_specs(ctx)
    )
    assert SOURCES["note"] in p.solution_html
    assert (
        p.solution_html.index("t=")
        < p.solution_html.index("z=")
        < p.solution_html.index("Вернёмся к переменной t")
        < p.solution_html.index("Вернёмся к переменной x")
    )
    assert "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
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
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in p.transformations
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    assert (
        ctx["normalized_content"]["assets"] == original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_is_not_an_input_and_parent_identity_is_required(row):
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), answer_set(row["expected_answer"]))
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой метод.</p>")


@pytest.mark.parametrize(
    "field,value", [("asset_key", "wrong"), ("kind", "unknown"), ("url", "/wrong")]
)
def test_reviewed_unused_child_figure_requires_full_identity(field, value):
    row = ROWS[1]
    ctx = deepcopy(row["context"])
    assert ctx["normalized_content"]["assets"]
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_unused_figure_cannot_be_attached_to_other_mathematics():
    row = ROWS[0]
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = deepcopy(
        ROWS[1]["context"]["normalized_content"]["assets"]
    )
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


@pytest.mark.parametrize(
    "formula",
    [
        r"(\log_2^2 x-2\log_2 x)^2\le11\log_2^2 x-22\log_2 x-24",
        r"(\log_2^2 x-2\log_2 x)^2<11\log_2^2 x-21\log_2 x-24",
        r"(\log_2^2 x-2\log_2 x)^2<11\log_3^2 x-22\log_2 x-24",
        r"(\log_2^2 x-2\log_2 x)^2+x<11\log_2^2 x-22\log_2 x-24",
    ],
)
def test_complete_inner_quadratic_same_base_operator_and_outer_expression_required(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_plural_instruction_does_not_allow_extra_instructions_or_formulas():
    row = ROWS[-1]
    assert "неравенства" in row["context"]["normalized_content"]["sections"][0][
        "html"
    ].replace("\xad", "")
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Округлите ответ.</p>"
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
