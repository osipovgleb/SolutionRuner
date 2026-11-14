"""Two parent presentations share math and chart validation without source writes."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_radical_inequality_factor import ANSWERS
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.radical_inequality_factor import analyze
from solution_runner.pipelines.equations.radical_inequality_factor_figures import (
    SOURCES,
    render,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = [
    r
    for r in json.loads(
        Path(__file__)
        .with_name("fixtures")
        .joinpath("radical_inequality_sources.json")
        .read_text()
    )
    if r["group"] in ("507582", "485951")
]
PARENTS = {
    r["group"]: next(
        s["html"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for r in ROWS
    if r["task"] == r["group"]
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def plan(row, context=None, parent=None):
    h = handler(row)
    ctx = _with_required_assets(row["context"] if context is None else context, h.key)
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
            ctx,
            parent_solution_html=PARENTS[row["group"]] if parent is None else parent,
            generated_solution_assets=generated,
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_zero_case_precedes_division_and_plans_are_readonly_and_idempotent(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original
    assert answer_set(p.answer) == answer_set(ANSWERS[row["task"]])
    assert p.solution_html.count("<img ") == 1
    assert (
        p.solution_html.index("нулю")
        < p.solution_html.index("положителен")
        < p.solution_html.index("<img ")
    )
    assert "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=PARENTS[row["group"]],
    )
    assert record["status"] == "prepared" and record["transformations"] == list(
        p.transformations
    )
    assert gateway.reads == [ctx["problem_id"]]
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    assert all(
        asset in ctx["normalized_content"]["assets"]
        for asset in original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize(
    "row",
    [r for r in ROWS if r["context"]["normalized_content"]["assets"]],
    ids=lambda r: r["task"],
)
def test_all_four_exact_native_charts_are_reused_and_missing_native_is_restored(row):
    uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    assert uid in SOURCES["figures"] and uid in plan(row).solution_html
    assert not handler(row).diagram_specs(row["context"])
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in plan(row).transformations
    )
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    restored = _with_required_assets(ctx, handler(row).key)
    assert restored["normalized_content"]["assets"][0]["asset_id"] == uid
    assert not handler(row).diagram_specs(restored)


def test_single_generated_chart_contains_only_the_rational_stage():
    row = next(r for r in ROWS if r["task"] == "511445")
    specs = handler(row).diagram_specs(row["context"])
    assert len(specs) == 1
    root = ET.fromstring(specs[0]["svg_text"])
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert [
        (c.get("data-boundary"), c.get("fill")) for c in root.findall("s:circle", ns)
    ] == [("0", "#FFFFFF"), ("1", "#000000"), ("2", "#000000")]
    assert [
        int(t.get("data-sign"))
        for t in root.findall("s:text", ns)
        if t.get("data-sign")
    ] == [-1, 1, -1, 1]
    assert root.get("data-source-style") == "45d2d373-83fa-49dc-a954-115dba252fec"


def test_double_generated_chart_keeps_cancelled_hole_and_both_sign_rows():
    row = next(r for r in ROWS if r["task"] == "511535")
    specs = handler(row).diagram_specs(row["context"])
    assert len(specs) == 1
    root = ET.fromstring(specs[0]["svg_text"])
    ns = {"s": "http://www.w3.org/2000/svg"}
    groups = {g.get("data-row"): g for g in root.findall("s:g", ns)}
    assert [
        (c.get("data-boundary"), c.get("fill"))
        for c in groups["stage"].findall("s:circle", ns)
    ] == [("-5", "#000000"), ("-4", "#FFFFFF"), ("-3", "#FFFFFF")]
    assert [
        (c.get("data-boundary"), c.get("fill"))
        for c in groups["domain"].findall("s:circle", ns)
    ] == [("-6", "#000000"), ("0", "#000000")]
    assert [
        int(t.get("data-sign"))
        for t in groups["stage"].findall("s:text", ns)
        if t.get("data-sign")
    ] == [1, -1, 1, 1]
    assert [
        int(t.get("data-sign"))
        for t in groups["domain"].findall("s:text", ns)
        if t.get("data-sign")
    ] == [-1, 1, -1]
    assert root.get("data-source-style") == "87a18f54-bf62-4452-b902-1b2a48c260a2"


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_and_another_parent_cannot_control_preparation(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert answer_set(plan(row, ctx).answer) == answer_set(ANSWERS[row["task"]])
    other = next(key for key in PARENTS if key != row["group"])
    with pytest.raises(UnsupportedCondition):
        plan(row, parent=PARENTS[other])


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_key", "wrong"),
        ("kind", None),
        ("url", "/wrong"),
        ("asset_id", "unknown"),
    ],
)
def test_native_chart_requires_verified_metadata(field, value):
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


def test_single_stage_chart_is_compatible_when_only_unplotted_root_domain_changes():
    ctx = deepcopy(ROWS[0]["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace(r"\sqrt{5-x}", r"\sqrt{6-x}")
    uid = ctx["normalized_content"]["assets"][0]["asset_id"]
    assert (
        not handler(ROWS[0]).diagram_specs(ctx)
        and uid in plan(ROWS[0], ctx).solution_html
    )


def test_intersection_chart_is_rejected_when_the_plotted_root_domain_changes():
    row = next(r for r in ROWS if r["task"] == "485951")
    ctx = deepcopy(row["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("6x-x", "7x-x")
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_intersection_chart_cannot_silently_drop_zero_branch_endpoints():
    a = analyze(r"\frac{x-3}{x-4}\sqrt{6*x-x^2}\le0")
    assert a.zero_case.contains(0) and a.zero_case.contains(6)
    assert not a.stage.solution.contains(0) and not a.stage.solution.contains(6)
    with pytest.raises(UnsupportedCondition):
        render(a)
