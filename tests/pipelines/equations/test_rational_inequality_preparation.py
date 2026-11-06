"""Pure plans preserve source methods, chart semantics and replay identity."""

import gzip
import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_rational_inequality import METHODS, SOURCES, answer_set

from solution_runner.dashboard.teacherhelper import teacherhelper_navigation
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.rational_inequality import set_latex
from solution_runner.pipelines.equations.rational_inequality_figures import (
    DIRECTORY,
    GROUPS,
    KEY,
    read,
)
from solution_runner.pipelines.equations.rational_inequality_figures import (
    SOURCES as CHARTS,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition


def section(ctx, key):
    return next(s for s in ctx["normalized_content"]["sections"] if s["key"] == key)


def handler(row):
    return get_handler(
        "exam-rational-inequality-" + METHODS[row["group"]].replace("_", "-")
    )


def parent(row):
    return section(
        next(r for r in SOURCES if r["task"] == row["group"])["context"], "solution"
    )["html"]


def plan(row, ctx):
    h = handler(row)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in h.diagram_specs(ctx)
    )
    return h.plan(
        PlanInput(
            ctx, parent_solution_html=parent(row), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_plans_answers_source_reuse_and_replay(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    assert ctx == row["context"]
    assert answer_set(p.answer) == answer_set(row["expected_answer"])
    assert not any(
        t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    original_others = [
        s
        for s in ctx["normalized_content"]["sections"]
        if s["key"] not in ("answer", "solution")
    ]
    if row["task"] == "511561":
        assert len(handler(row).diagram_specs(ctx)) == 1
        assert any(
            t["transformation_target_id"] == "asset:" + KEY for t in p.transformations
        )
    else:
        assert not handler(row).diagram_specs(ctx)
        for asset in ctx["normalized_content"].get("assets", []):
            assert asset["asset_id"] in p.solution_html
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    assert [
        s
        for s in ctx["normalized_content"]["sections"]
        if s["key"] not in ("answer", "solution")
    ] == original_others


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_answers_and_solution_text_do_not_supply_the_computed_answer(row):
    ctx = deepcopy(row["context"])
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Это неверно</p>"
    assert plan(row, ctx).answer == set_latex(read(row["context"])[1].solution)


@pytest.mark.parametrize("record", GROUPS, ids=lambda r: r[0])
def test_exact_catalog_binding_and_shared_planner(record):
    key, group_id, index, theme, theme_index, theme_id, method = record
    profile = get_group_profile(key)
    assert (
        profile.source_group_id,
        profile.group_order_index,
        profile.theme_title,
        profile.theme_order_index,
        profile.snapshot_theme_id,
        profile.category_key,
    ) == (group_id, index, theme, theme_index, theme_id, "16")
    assert profile.content_rule_key == "exam-rational-inequality-" + method.replace(
        "_", "-"
    )
    get_handler(profile.content_rule_key).validate()
    navigation = teacherhelper_navigation(profile)
    assert navigation["category_id"] == "f1f2f85a-56b3-4188-b1d7-d330025173a7"
    assert navigation["theme_id"] == theme_id and navigation["group_id"] == group_id


def test_missing_answer_is_added_and_replay_is_empty():
    row = next(r for r in SOURCES if r["task"] == "511531")
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["sections"].remove(section(ctx, "answer"))
    p = plan(row, ctx)
    assert any(
        t["operation"] == "add"
        and t["transformation_target_id"].startswith("section:answer")
        for t in p.transformations
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


def test_missing_child_chart_keeps_parent_rows_domain_hole_and_correct_signs():
    row = next(r for r in SOURCES if r["task"] == "511561")
    root = ET.fromstring(handler(row).diagram_specs(row["context"])[0]["svg_text"])
    markers = {c.get("data-boundary"): c for c in root.iter() if c.get("data-boundary")}
    assert set(markers) == {"-5", "-3", "3", "5"}
    assert markers["-5"].get("fill") == markers["-3"].get("fill") == "#000000"
    assert markers["3"].get("fill") == markers["5"].get("fill") == "#FFFFFF"
    assert markers["5"].get("cy") != markers["3"].get("cy")
    assert float(markers["5"].get("cx")) > float(markers["3"].get("cx"))
    assert [n.get("data-sign") for n in root.iter() if n.get("data-sign")] == [
        "-1",
        "1",
        "-1",
        "1",
    ]
    assert [
        n.get("data-selected-interval")
        for n in root.iter()
        if n.get("data-selected-interval")
    ] == ["1", "3"]


def test_changed_native_single_chart_uses_parent_two_row_composition():
    row = next(r for r in SOURCES if r["task"] == "508516")
    ctx = deepcopy(row["context"])
    soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
    soup.span["data-inline-latex"] = (
        r"x+\frac{8x-45}{x-7}+\frac{x^2+15x-132}{x^2-16x+63}\le 1"
    )
    section(ctx, "condition")["html"] = str(soup)
    spec = handler(row).diagram_specs(ctx)[0]
    assert 'data-excluded="7"' in spec["svg_text"]
    assert spec["sha256"] == hashlib.sha256(spec["svg_text"].encode()).hexdigest()
    assert answer_set(plan(row, ctx).answer) == answer_set(
        r"(-\infty;-5]\cup[6;7)\cup(7;9)"
    )


@pytest.mark.parametrize("uid,entry", CHARTS["figures"].items())
def test_packaged_source_svg_bytes_match_visual_review(uid, entry):
    raw = gzip.decompress((DIRECTORY / (uid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]


@pytest.mark.parametrize(
    "change", ("unknown_asset", "extra_instruction", "wrong_parent")
)
def test_unknown_figures_instructions_or_parent_are_rejected(change):
    row = next(r for r in SOURCES if r["task"] == "508516")
    ctx = deepcopy(row["context"])
    if change == "unknown_asset":
        ctx["normalized_content"]["assets"][0]["asset_id"] = "unreviewed"
    elif change == "extra_instruction":
        section(ctx, "condition")["html"] += (
            "<p>Укажите только положительные решения.</p>"
        )
    with pytest.raises(UnsupportedCondition):
        if change == "wrong_parent":
            handler(row).plan(PlanInput(ctx, parent_solution_html=parent(row) + " "))
        else:
            plan(row, ctx)


class ReadOnlyGateway:
    def __init__(self, ctx):
        self.ctx = deepcopy(ctx)
        self.reads = []

    def get_problem_context(self, identifier):
        assert identifier == self.ctx["problem_id"]
        self.reads.append(identifier)
        return deepcopy(self.ctx)

    def __getattr__(self, name):
        raise AssertionError("unexpected external operation: " + name)


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_frozen_preparation_reads_once_and_never_requests_writes_or_uploads(row):
    from solution_runner.pipelines.core.content_runtime import _prepared_record

    gateway = ReadOnlyGateway(row["context"])
    record = _prepared_record(
        gateway,
        {"problem_id": row["context"]["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    expected = plan(row, row["context"])
    assert record["expected_answer"] == expected.answer
    assert record["transformations"] == list(expected.transformations)
    assert gateway.reads == [row["context"]["problem_id"]]
    assert gateway.ctx == row["context"]


def test_unsupported_source_freezes_without_transformations():
    from solution_runner.pipelines.core.content_runtime import _prepared_record

    row = SOURCES[0]
    ctx = deepcopy(row["context"])
    section(ctx, "condition")["html"] += "<p>Укажите только целые решения.</p>"
    record = _prepared_record(
        ReadOnlyGateway(ctx),
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=parent(row),
    )
    assert record["status"] == "blocked" and record["transformations"] == []
    assert not record.get("generated_diagrams")
