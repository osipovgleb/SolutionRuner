"""Local transport proves source reuse and refusal before writing impossible sections."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import section
from pyramid_midsection_source_cases import BLOCKED, CASES, GROUPS, arguments, plan
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError


def prepared(case, gateway):
    return _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )


def apply_offline(case, gateway, record):
    return _apply_record(
        gateway,
        record,
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_local_roundtrips_reuse_original_sources_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert (
        gateway.context["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )
    for key in ("condition", "source", "criteria"):
        assert section(gateway.context, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("key", ("condition", "criteria", "solution"))
def test_frozen_input_changes_stop_before_local_write(case, key):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, key)["html"] += "<p>Изменение</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


def without_figures(case):
    ctx = deepcopy(case["context"])
    for sec in ctx["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    ctx["normalized_content"]["assets"] = []
    return ctx


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_actual_median_and_given_point_names(case):
    gateway = OfflineGateway({**case, "context": without_figures(case)})
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    targets = [
        (t["operation"], t["transformation_target_id"])
        for t in record["transformations"]
    ]
    assert len(targets) == len(set(targets))
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert (
        len(gateway.context["normalized_content"]["assets"]) == 1
        and not gateway.uploads
    )
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_solution_asset_is_refused(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    asset["asset_id"] = uid = "00000000-0000-4000-8000-000000000001"
    asset["url"] = "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("missing", ("section:solution:1", "asset:image_1"))
def test_missing_solution_or_restored_asset_readback_is_failure(case, missing):
    gateway = OfflineGateway({**case, "context": without_figures(case)}, omit=missing)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads


@pytest.mark.parametrize("task,parent", (("501730", "501690"), ("513095", "509948")))
def test_known_incompatible_auxiliary_names_restore_the_correct_approved_figure(
    task, parent
):
    case = next(c for c in CASES if c["task"] == task)
    other = next(c for c in CASES if c["task"] == parent)
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    correct = old = asset["asset_id"]
    asset["asset_id"] = uid = other["context"]["normalized_content"]["assets"][0][
        "asset_id"
    ]
    asset["url"] = "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    gateway = OfflineGateway({**case, "context": ctx})
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert gateway.context["normalized_content"]["assets"][0]["asset_id"] == correct
    assert not gateway.uploads


def test_impossible_native_task_is_blocked_before_any_transform_or_local_write():
    case = BLOCKED[0]
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "blocked", record
    assert not record.get("transformations") and not record.get("generated_diagrams")
    assert "no two-dimensional section" in str(record)
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
    assert gateway.context == case["context"]


def test_wrong_source_answer_cannot_override_the_nonexistent_section_guard():
    case = BLOCKED[0]
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    gateway = OfflineGateway({**case, "context": ctx})
    record = prepared(case, gateway)
    assert record["status"] == "blocked" and not record.get("transformations")
    assert not gateway.uploads and not gateway.writes
