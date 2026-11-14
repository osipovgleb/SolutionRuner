"""Parent method, exact chart reuse, generated domain and read-only replay."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.radical_inequality_figures import SOURCES
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = [
    r
    for r in json.loads(
        Path(__file__)
        .with_name("fixtures")
        .joinpath("radical_inequality_sources.json")
        .read_text()
    )
    if r["group"] == "507612"
]
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
ANSWERS = {
    "507612": r"(1;2)\cup(3;7]",
    "507833": r"(1;2)\cup(4;5]",
    "511449": r"(0;2)\cup(4;6]",
}


def handler():
    return get_handler(get_group_profile("507612").content_rule_key)


def plan(row, context=None, parent=PARENT):
    ctx = _with_required_assets(
        row["context"] if context is None else context, handler().key
    )
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler().diagram_specs(ctx)
    )
    return handler().plan(
        PlanInput(ctx, parent_solution_html=parent, generated_solution_assets=generated)
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_method_note_and_readonly_replay(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert p.answer.replace(" ", "") == ANSWERS[row["task"]]
    assert ctx == original
    assert p.solution_html.count("<img ") == 1
    assert "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
    assert (
        p.solution_html.index("Умножая")
        < p.solution_html.index("раскроем скобки")
        < p.solution_html.index("<img ")
        < p.solution_html.index("Примечание")
    )
    assert "нет необходимости дополнительно решать" in p.solution_html
    assert not any(
        t["transformation_target_id"].startswith("section:condition")
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
    assert record["status"] == "prepared" and gateway.reads == [ctx["problem_id"]]
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    assert all(
        asset in ctx["normalized_content"]["assets"]
        for asset in original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("row", ROWS[:2], ids=lambda r: r["task"])
def test_native_source_charts_are_reused_exactly_and_restored_if_missing(row):
    asset = row["context"]["normalized_content"]["assets"][0]
    uid = asset["asset_id"]
    assert uid in SOURCES["figures"]
    assert not handler().diagram_specs(row["context"])
    assert uid in plan(row).solution_html
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in plan(row).transformations
    )
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    restored = _with_required_assets(ctx, handler().key)
    assert restored["normalized_content"]["assets"][0]["asset_id"] == uid
    assert not handler().diagram_specs(restored)


def test_missing_child_chart_has_its_own_domain_and_exact_intersections():
    row = ROWS[-1]
    specs = handler().diagram_specs(row["context"])
    assert len(specs) == 1
    root = ET.fromstring(specs[0]["svg_text"])
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.get("viewBox") == "0 0 242.2822 83.2424"
    groups = {g.get("data-row"): g for g in root.findall("s:g", ns)}
    assert [
        (c.get("data-boundary"), c.get("fill"))
        for c in groups["stage"].findall("s:circle", ns)
    ] == [("0", "#FFFFFF"), ("2", "#FFFFFF"), ("4", "#FFFFFF")]
    assert [
        (c.get("data-boundary"), c.get("fill"))
        for c in groups["domain"].findall("s:circle", ns)
    ] == [("-1", "#FFFFFF"), ("6", "#000000")]
    assert [
        int(t.get("data-sign"))
        for t in groups["stage"].findall("s:text", ns)
        if t.get("data-sign")
    ] == [-1, 1, -1, 1]
    assert [r.get("data-intersection") for r in root.findall("s:rect", ns)] == [
        "Interval.open(0, 2)",
        "Interval.Lopen(4, 6)",
    ]
    assert root.get("data-source-style") == "652fe099-f167-4deb-81c6-c0327f1d1731"


def test_equal_cubic_does_not_allow_reusing_a_chart_with_different_domain():
    ctx = deepcopy(ROWS[-1]["context"])
    ctx["normalized_content"]["assets"] = deepcopy(
        ROWS[1]["context"]["normalized_content"]["assets"]
    )
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[-1], ctx)


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_key", "wrong"),
        ("kind", None),
        ("url", "/wrong"),
        ("asset_id", "unknown"),
    ],
)
def test_unverified_native_chart_metadata_is_rejected(field, value):
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_is_ignored_and_other_parent_is_rejected(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(row, ctx).answer.replace(" ", "") == ANSWERS[row["task"]]
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой метод.</p>")
