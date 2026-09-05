"""Local fixture and fake-MCP regression coverage; never contact production."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from solution_runner.pipelines.grid_polygon.general_triangle_pipeline.planner import (
    PARENT_ASSET_ID, PARENT_PROBLEM_ID, RULE, build_repair_plan,
)
from solution_runner.pipelines.grid_polygon.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.models import ProblemTarget
from solution_runner.pipelines.grid_polygon.right_triangle_pipeline.planner import RightTrianglePlanError
from solution_runner.pipelines.grid_polygon.right_triangle_pipeline.runtime import (
    _content_rule_manifest, _read_content_rule_manifest, apply_frozen_manifest,
)

FIXTURES = json.loads((Path(__file__).parent / "fixtures/content_rules/group_27591.json").read_text())


def plan(context):
    return build_repair_plan(context, parent_condition_asset_id=PARENT_ASSET_ID)


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


class FakeMCP:
    def __init__(self, *contexts):
        self.contexts = {c["problem_id"]: deepcopy(c) for c in (FIXTURES[0], *contexts)}
        self.writes = []

    def get_source_catalog_children(self, parent_id, parent_type):
        assert parent_id == get_group_profile("27591").source_group_id
        assert parent_type == "group"
        return {"items": [{"uuid": c["problem_id"], "name": "Задача " + c["source_problem_id"]}
                          for c in self.contexts.values()]}

    def get_problem_context(self, problem_id):
        return deepcopy(self.contexts[problem_id])

    def apply_problem_transformations(self, problem_id, transformations):
        self.writes.append((problem_id, deepcopy(transformations)))
        content = self.contexts[problem_id]["normalized_content"]
        for item in transformations:
            value = deepcopy(item["value"])
            if item["transformation_target_id"] == "asset:image_1":
                content["assets"] = [{k: value[k] for k in
                    ("asset_key", "asset_id", "url", "kind", "alt")}]
                condition = section(self.contexts[problem_id], "condition")
                condition["asset_keys"] = ["image_1"]
                condition["html"] = value["html"] + condition["html"]
            else:
                key = item["transformation_target_id"].split(":")[1]
                assert key in {"solution", "answer"}
                existing = next((s for s in content["sections"] if s["key"] == key), None)
                if existing is None:
                    content["sections"].append({"key": key, "section_id": f"{key}:1", **value})
                else:
                    existing.update(value)


def freeze(gateway, contexts):
    profile = get_group_profile("27591")
    targets = tuple(ProblemTarget(c["problem_id"], c["source_problem_id"],
                    profile.source_group_id, "27591", i) for i, c in enumerate(contexts))
    manifest = _content_rule_manifest(gateway, targets, profile=profile,
        parent_asset_id=PARENT_ASSET_ID, parent_solution_assets=(), max_workers=1)
    return manifest, targets


def apply(gateway, manifest, tmp_path):
    return apply_frozen_manifest(gateway, manifest, batch_size=1, max_workers=1,
                                 checkpoint_path=tmp_path / "checkpoint.json")


def test_parent_is_unchanged_and_child_uses_parent_proof_and_asset():
    assert plan(FIXTURES[0]).answer == "24"
    assert plan(FIXTURES[0]).transformations == ()
    result = plan(FIXTURES[1])
    assert result.answer == "32"
    assert [t["transformation_target_id"] for t in result.transformations] == [
        "asset:image_1", "section:solution"]
    assert result.transformations[0]["value"]["parent_target_id"] == "section:condition:1"
    assert r"\sin 30^{\circ}" in result.transformations[1]["value"]["html"]
    assert result.transformations[1]["value"]["asset_keys"] == []


@pytest.mark.parametrize(("a", "b", "answer"), [(1, 1, "0,25"), (21, 2, "10,5"),
                                                (3, 1, "0,75"), (999999, 4, "999999")])
def test_exact_quarter_arithmetic(a, b, answer):
    context = deepcopy(FIXTURES[1])
    section(context, "condition")["html"] = (
        f"<p>Найдите площадь треугольника, две стороны которого равны {a} и {b}, "
        "а угол между ними равен 30°.</p>")
    section(context, "answer")["html"] = f"<p>{answer}</p>"
    assert plan(context).answer == answer


@pytest.mark.parametrize("change", [
    lambda c: section(c, "condition").update(html=section(c, "condition")["html"] + "<p>И ещё угол 90°.</p>"),
    lambda c: section(c, "condition").update(html=section(c, "condition")["html"].replace("30", "150")),
    lambda c: section(c, "condition").update(html=section(c, "condition")["html"].replace("между ними", "при основании")),
    lambda c: section(c, "condition").update(html=section(c, "condition")["html"].replace("8 и 16", "0 и 16")),
    lambda c: section(c, "condition").update(html=section(c, "condition")["html"].replace("8 и 16", "8,5 и 16")),
    lambda c: section(c, "condition").update(html=section(c, "condition")["html"].replace("<p>", '<p style="display:none">')),
    lambda c: section(c, "condition").update(html=section(c, "condition")["html"].replace('></span>', '>90°</span>')),
    lambda c: c["normalized_content"]["sections"].append(deepcopy(section(c, "condition"))),
    lambda c: c["normalized_content"]["assets"].append({"asset_id": "unknown"}),
])
def test_unknown_or_ambiguous_input_fails_closed(change):
    context = deepcopy(FIXTURES[1])
    change(context)
    with pytest.raises(ValueError):
        plan(context)


def test_observed_incorrect_answer_is_repaired(tmp_path):
    gateway = FakeMCP(FIXTURES[2])
    manifest, _ = freeze(gateway, [FIXTURES[2]])
    assert manifest["records"][0]["expected_answer"] == "200"
    assert apply(gateway, manifest, tmp_path)["applied_count"] == 1
    assert section(gateway.contexts[FIXTURES[2]["problem_id"]], "answer")["html"] == (
        '<p><span data-effect="spaced">200</span></p>')
    assert plan(gateway.contexts[FIXTURES[2]["problem_id"]]).transformations == ()


@pytest.mark.parametrize("stored", [None, "", "<p>-</p>", "<p>)</p>", "<p>32.000001</p>",
                                    '<strong>broken</strong>'])
def test_missing_or_damaged_answer_is_repaired(tmp_path, stored):
    context = deepcopy(FIXTURES[1])
    if stored is None:
        context["normalized_content"]["sections"].remove(section(context, "answer"))
    else:
        section(context, "answer")["html"] = stored
    gateway = FakeMCP(context)
    manifest, _ = freeze(gateway, [context])
    assert apply(gateway, manifest, tmp_path)["applied_count"] == 1
    result = gateway.contexts[context["problem_id"]]
    assert section(result, "answer")["html"] == '<p><span data-effect="spaced">32</span></p>'
    assert plan(result).transformations == ()


@pytest.mark.parametrize("html", ["<p>Площадь равна 999.</p>", "<p></p>", None])
def test_wrong_existing_solution_is_repaired(tmp_path, html):
    context = deepcopy(FIXTURES[0])
    section(context, "solution")["html"] = html
    gateway = FakeMCP(context)
    manifest, _ = freeze(gateway, [context])
    assert apply(gateway, manifest, tmp_path)["applied_count"] == 1
    assert len(gateway.writes[0][1]) == 1
    assert gateway.writes[0][1][0]["transformation_target_id"] == "section:solution:1"
    assert plan(gateway.contexts[context["problem_id"]]).transformations == ()


def test_fake_apply_readback_and_resume(tmp_path):
    gateway = FakeMCP(FIXTURES[1])
    manifest, targets = freeze(gateway, [FIXTURES[1]])
    path = tmp_path / "prepared-manifest.json"
    path.write_text(json.dumps(manifest))
    resumed = _read_content_rule_manifest(path, targets, get_group_profile("27591"))
    assert apply(gateway, resumed, tmp_path)["applied_count"] == 1
    assert len(gateway.writes) == 1
    assert plan(gateway.contexts[FIXTURES[1]["problem_id"]]).transformations == ()
    assert apply(gateway, resumed, tmp_path)["already_complete_count"] == 1
    assert len(gateway.writes) == 1


def test_ambiguous_record_writes_nothing_and_valid_records_continue(tmp_path):
    bad = deepcopy(FIXTURES[2])
    section(bad, "condition")["html"] += "<p>Другой угол равен 90°.</p>"
    gateway = FakeMCP(bad, FIXTURES[1])
    manifest, _ = freeze(gateway, [bad, FIXTURES[1]])
    assert manifest["records"][0]["status"] == "blocked"
    summary = apply(gateway, manifest, tmp_path)
    assert summary["blocked_count"] == 1
    assert summary["applied_count"] == 1
    assert "unsupported" in summary["results"][0]["message"]
    assert [pid for pid, _ in gateway.writes] == [FIXTURES[1]["problem_id"]]
    assert gateway.contexts[bad["problem_id"]] == bad


@pytest.mark.parametrize("drift", ["answer", "condition"])
def test_stale_record_failure_does_not_block_independent_records(tmp_path, drift):
    second = deepcopy(FIXTURES[1])
    second.update(problem_id="fake-second", source_problem_id="fake-second")
    gateway = FakeMCP(FIXTURES[1], second)
    manifest, _ = freeze(gateway, [second, FIXTURES[1]])
    section(gateway.contexts["fake-second"], drift)["html"] += "extra"
    summary = apply(gateway, manifest, tmp_path)
    assert summary["failed_count"] == 1
    assert summary["applied_count"] == 1
    assert [pid for pid, _ in gateway.writes] == [FIXTURES[1]["problem_id"]]


@pytest.mark.parametrize("drift", ["scope", "asset", "membership", "records", "status"])
def test_shared_safety_failure_still_aborts_before_writes(tmp_path, drift):
    gateway = FakeMCP(FIXTURES[1])
    manifest, _ = freeze(gateway, [FIXTURES[1]])
    if drift == "scope":
        manifest["catalog_snapshot_id"] = "other"
    elif drift == "asset":
        manifest["condition_asset"]["source_asset_id"] = "unknown"
    elif drift == "membership":
        manifest["records"][0]["source_problem_id"] = "other"
    elif drift == "records":
        manifest["records"].append(deepcopy(manifest["records"][0]))
    else:
        manifest["records"][0]["status"] = "unknown"
    with pytest.raises(ValueError):
        apply(gateway, manifest, tmp_path)
    assert gateway.writes == []


def test_unselected_parent_bad_answer_is_not_a_shared_blocker(tmp_path):
    gateway = FakeMCP(FIXTURES[1])
    section(gateway.contexts[PARENT_PROBLEM_ID], "answer")["html"] = "<p>broken</p>"
    manifest, _ = freeze(gateway, [FIXTURES[1]])
    assert apply(gateway, manifest, tmp_path)["applied_count"] == 1


def test_misplaced_image_and_section_target_cannot_be_rewritten():
    context = deepcopy(FIXTURES[1])
    context["normalized_content"]["sections"].append({
        "key": "solution", "section_id": "solution:1", "asset_keys": [],
        "html": '<img src="/assets/unknown"/>',
    })
    with pytest.raises(ValueError, match="only in condition"):
        plan(context)
    section(context, "solution").update(html="", transformation_target_id="section:condition:1")
    with pytest.raises(ValueError, match="section identity"):
        plan(context)


def test_empty_solution_markup_is_filled():
    context = deepcopy(FIXTURES[1])
    context["normalized_content"]["sections"].append({
        "key": "solution", "section_id": "solution:1", "asset_keys": [], "html": "<p> </p>",
    })
    result = plan(context)
    assert result.transformations[-1]["operation"] == "rewrite"
    assert result.transformations[-1]["transformation_target_id"] == "section:solution:1"


def test_live_transformation_context_metadata_and_missing_source_id(tmp_path):
    gateway = FakeMCP(FIXTURES[1])
    parent = gateway.contexts[PARENT_PROBLEM_ID]
    section(parent, "condition")["html"] = section(parent, "condition")["html"].replace(
        '<img ', '<img data-transformation-target-id="asset:image_1" ')
    parent["normalized_content"]["assets"][0]["transformation_target_id"] = "asset:image_1"
    for context in gateway.contexts.values():
        for item in context["normalized_content"]["sections"]:
            item["transformation_target_id"] = "section:" + item["section_id"]
    original_read = gateway.get_problem_context

    def context_read(problem_id):
        context = original_read(problem_id)
        context.pop("source_problem_id")
        return context

    gateway.get_problem_context = context_read
    manifest, _ = freeze(gateway, [FIXTURES[1]])
    assert apply(gateway, manifest, tmp_path)["applied_count"] == 1
    section(parent, "condition")["html"] = section(parent, "condition")["html"].replace(
        'data-transformation-target-id="asset:image_1"',
        'data-transformation-target-id="asset:image_2"')
    with pytest.raises(ValueError, match="target drifted"):
        plan(parent)
