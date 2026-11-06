"""Local fake transport verifies frozen spatial diagrams and exact content readback."""

import pytest
from line_projection_source_cases import CASES, GROUPS, arguments, plan, read
from midpoint_source_cases import section
from test_cube_lifecycle import remove_images
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.handler_registry import get_handler


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
def test_native_frozen_roundtrip_uploads_only_needed_figures_and_resumes(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    expected = len(
        get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    )
    assert (
        record["status"] == "prepared"
        and record["expected_answer"] == plan(case).answer
    ), record
    assert not gateway.writes and not gateway.uploads
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert len(gateway.uploads) == expected and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == expected and len(gateway.writes) == 1
    assert read(gateway.context) == read(case["context"])
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("key", ("condition", "criteria", "solution"))
def test_frozen_changes_stop_before_local_write(case, key):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    current = section(gateway.context, key)
    if current is None:
        gateway.context["normalized_content"]["sections"].append(
            {
                "key": key,
                "title": "Решение",
                "html": "<p>Изменение</p>",
                "asset_keys": [],
                "section_id": "solution:1",
                "transformation_target_id": "section:solution:1",
            }
        )
    else:
        current["html"] += "<p>Изменение</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.writes and not gateway.uploads


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_the_reviewed_scene_set_and_resume(case):
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert len(gateway.context["normalized_content"]["assets"]) == (1)
    assert not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("key", ("answer", "solution"))
def test_missing_sections_are_added_and_complete_readback_is_required(case, key):
    gateway = OfflineGateway(case)
    gateway.context["normalized_content"]["sections"] = [
        s for s in gateway.context["normalized_content"]["sections"] if s["key"] != key
    ]
    if key == "solution":
        remove_images(gateway)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    target = "section:" + key
    assert any(
        t["transformation_target_id"] == target for t in record["transformations"]
    )
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"
    assert len(gateway.writes) == 1 and not gateway.uploads
