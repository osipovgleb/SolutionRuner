"""Native parent and explicit public-text probes; child assets remain unverified."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (Path(__file__).parent / "fixtures/group_27710_sources.json").read_text()
)
SOURCES = DATA["public_source_transcriptions"]


def public_text_probe(source):
    """Adapt reviewed public text in memory, without claiming a native child context."""
    text = re.sub(r"\s+\.", ".", source["condition"])
    html = re.sub(
        r"(\\overrightarrow\{[A-Z]{2}\})",
        r'<span data-inline-latex="\1"></span>',
        text,
    )
    condition = deepcopy(DATA["parent_context"]["normalized_content"]["sections"][0])
    assert condition["key"] == "condition"
    condition.update(html="<p>" + html + "</p>", asset_keys=[])
    return {
        "problem_id": source["task_uuid"],
        "local_public_text_probe": source["url"],
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [condition],
        },
    }


def plan(context):
    return get_handler(get_group_profile("27710").content_rule_key).plan(
        PlanInput(context)
    )


def test_full_catalog_group_reuses_existing_geometric_rule():
    p = get_group_profile("27710")
    assert (p.source_group_id, p.snapshot_theme_id, p.group_order_index) == (
        DATA["group_uuid"],
        DATA["theme_uuid"],
        DATA["group_order"],
    )
    assert p.category_key == "2" and p.theme_order_index == 0
    assert p.content_rule_key == "vector-geometric-operations"
    assert len(DATA["group_tasks"]) == 27
    ids = {t["uuid"] for t in DATA["group_tasks"]}
    assert len(ids) == 27 and {s["task_uuid"] for s in SOURCES} <= ids
    assert not DATA["child_native_contexts_available"]
    assert DATA["unavailable_public_figures"]


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s["task"])
def test_public_text_probes_compute_perpendicular_dot_product_without_answers(source):
    context = public_text_probe(source)
    original = deepcopy(context)
    result = plan(context)
    assert result.answer == "0" and context == original
    assert r"\cos90^{\circ}=0" in result.solution_html
    assert "Соседние стороны прямоугольника перпендикулярны" in result.solution_html
    assert all(
        t["transformation_target_id"].startswith("section:")
        for t in result.transformations
    )


def test_native_parent_keeps_its_audited_figure_and_replay_is_empty():
    context = deepcopy(DATA["parent_context"])
    original = deepcopy(context)
    first = plan(context)
    for section in context["normalized_content"]["sections"]:
        if section["key"] in {"answer", "solution"}:
            section["html"] = "<p>UNUSED 999</p>"
    poisoned = plan(context)
    assert poisoned.answer == first.answer == "0"
    assert poisoned.solution_html == first.solution_html
    for t in poisoned.transformations:
        key = t["transformation_target_id"]
        assert key.startswith(("section:solution", "section:answer"))
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        ).update(t["value"])
    assert plan(context).transformations == ()
    assert (
        context["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    assert get_handler("vector-geometric-operations").diagram_specs(original) == ()


def test_unknown_child_diagram_cannot_borrow_the_parent_audit():
    context = deepcopy(DATA["parent_context"])
    asset = context["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    asset.update(asset_id="unknown-child", url="/assets/unknown-child")
    for section in context["normalized_content"]["sections"]:
        section["html"] = section["html"].replace(old, "unknown-child")
    with pytest.raises(UnsupportedCondition):
        plan(context)


def test_nonperpendicular_vectors_are_not_given_the_constant_zero_answer():
    context = public_text_probe(SOURCES[-1])
    section = context["normalized_content"]["sections"][0]
    section["html"] = section["html"].replace(
        r"\overrightarrow{AD}", r"\overrightarrow{AC}"
    )
    with pytest.raises(UnsupportedCondition, match="perpendicular directions"):
        plan(context)
