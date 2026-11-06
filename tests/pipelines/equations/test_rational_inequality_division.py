"""Shared division proofs preserve original holes and the source sign orientation."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_rational_inequality import answer_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.rational_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_algebraic_methods import (
    presentation,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read
from solution_runner.pipelines.equations.rational_inequality_methods import prepare
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("rational_inequality_division_sources.json")
    .read_text()
)
METHODS = {
    "508367": "fraction_division",
    "508371": "degree_division",
    "508530": "split_cancel",
}


def handler(row):
    return get_handler(
        "exam-rational-inequality-" + METHODS[row["group"]].replace("_", "-")
    )


def parent(row):
    return next(
        s["html"]
        for r in SOURCES
        if r["task"] == row["group"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(row, ctx):
    h = handler(row)
    ctx = _with_required_assets(ctx, h.key)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(ctx)
    )
    return h.plan(
        PlanInput(
            ctx, parent_solution_html=parent(row), generated_solution_assets=generated
        )
    )


def expected(row):
    text = row["expected_answer"].replace("{,}", ".").replace(",", ";")
    return answer_set(text)


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_answers_and_every_division_or_cancellation_identity_match_the_source_condition(
    row,
):
    a = read(row["context"])[1]
    relation = {"<=": sp.Le, ">=": sp.Ge}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.original, 0), X, relational=False
    ) - sp.FiniteSet(*a.poles)
    assert a.solution == independent == expected(row)
    a = presentation(a, METHODS[row["group"]])
    _, steps = prepare(a, METHODS[row["group"]])
    assert steps
    for item in steps:
        assert sp.cancel(RationalParser(item.text).parse().value - a.original) == 0, (
            item.text
        )
    assert answer_set(plan(row, row["context"]).answer) == independent


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_charts_replay_and_frozen_preparation_never_mutate_or_write(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    assert ctx == row["context"]
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    for asset in ctx["normalized_content"].get("assets", []):
        assert asset["asset_id"] in p.solution_html
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == p.answer and record["transformations"] == list(
        p.transformations
    )
    assert gateway.ctx == ctx and len(gateway.reads) == 1
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["task"] != "508575"], ids=lambda r: r["task"]
)
def test_original_hole_stays_excluded_after_early_cancellation(row):
    a = read(row["context"])[1]
    assert len(a.holes) == 1
    assert a.holes[0] not in a.solution
    assert (
        "Сокращение общего множителя сохраняет"
        in plan(row, row["context"]).solution_html
    )


def test_negative_leading_source_chart_keeps_the_original_signs_and_operator():
    row = next(r for r in SOURCES if r["task"] == "508371")
    raw = read(row["context"])[1]
    a = presentation(raw, "degree_division")
    assert raw.signs == (-1, -1, 1, -1, 1) and raw.sign_operator == "<="
    assert a.signs == (1, 1, -1, 1, -1) and a.sign_operator == ">="
    assert a.solution == raw.solution
    assert (
        "e6cacb81-5f13-46d8-ac75-82574282a248"
        in plan(row, row["context"]).solution_html
    )
    assert not handler(row).diagram_specs(row["context"])


@pytest.mark.parametrize(
    "task,points,signs,width",
    [
        ("508369", ["-3", "-2", "0", "1"], [-1, 1, -1, -1, 1], "217.7959"),
        ("508373", ["0", "1", "2", "3"], [-1, -1, 1, -1, 1], "252.0512"),
        ("508375", ["0", "2", "3", "4"], [-1, -1, 1, -1, 1], "252.0512"),
        ("511519", ["-3", "-2", "-1", "0"], [-1, 1, -1, 1, 1], "252.0512"),
        ("511564", ["-3", "-5/2", "-2", "-1"], [-1, 1, -1, -1, 1], "206.6025"),
        ("688741", ["-1", "5", "9", "11"], [-1, 1, -1, -1, 1], "206.6025"),
    ],
)
def test_missing_charts_keep_source_layout_domain_holes_and_current_signs(
    task, points, signs, width
):
    row = next(r for r in SOURCES if r["task"] == task)
    (spec,) = handler(row).diagram_specs(row["context"])
    root = ET.fromstring(spec["svg_text"])
    marks = [n for n in root.iter() if n.get("data-boundary")]
    a = read(row["context"])[1]
    assert root.get("width") == width
    assert [m.get("data-boundary") for m in marks] == points
    assert [int(n.get("data-sign")) for n in root.iter() if n.get("data-sign")] == signs
    assert {m.get("data-boundary") for m in marks if m.get("fill") == "#FFFFFF"} == set(
        map(str, a.poles)
    )


def test_missing_solution_is_prepared_from_the_condition_and_parent_method():
    row = next(r for r in SOURCES if r["task"] == "688741")
    p = plan(row, row["context"])
    assert any(
        t["operation"] == "add"
        and t["transformation_target_id"].startswith("section:solution")
        for t in p.transformations
    )
    assert r"x\ne 9" in p.solution_html
    assert answer_set(p.answer) == expected(row)


@pytest.mark.parametrize(
    "task,factor", [("508369", "3"), ("508375", "2"), ("508575", "3")]
)
def test_omitted_positive_factors_are_explained_instead_of_dropped(task, factor):
    row = next(r for r in SOURCES if r["task"] == task)
    html = plan(row, row["context"]).solution_html
    assert "положительный множитель" in html
    assert factor in html


@pytest.mark.parametrize(
    "formula,method",
    [
        (r"\frac{x^2+1}{x^2-1}\le0", "fraction_division"),
        (r"\frac{x^3+1}{x^2-1}\le x+1", "degree_division"),
        (r"x+\frac{1}{x-1}\le0", "split_cancel"),
    ],
)
def test_unproved_division_shapes_fail_closed(formula, method):
    with pytest.raises(UnsupportedCondition):
        prepare(analyze(formula), method)
