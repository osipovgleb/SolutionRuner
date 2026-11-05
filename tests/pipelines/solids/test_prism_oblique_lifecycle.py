"""Local fake transport verifies frozen spatial diagrams and exact content readback."""

import pytest
from midpoint_source_cases import section
from prism_oblique_source_cases import CASES, GROUPS, arguments, plan, read
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
    assert len(gateway.context["normalized_content"]["assets"]) == (
        4 if case["group"] == "634951" else 1
    )
    assert not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize(
    "task,target",
    (
        ("501752", "section:answer"),
        ("681580", "section:solution"),
        ("694819", "section:solution"),
        ("647136", "section:answer:1"),
        ("647136", "section:solution:1"),
    ),
)
def test_missing_sections_and_ratio_origin_require_complete_readback(task, target):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case, omit=target)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert any(
        t["transformation_target_id"] == target for t in record["transformations"]
    )
    assert apply_offline(case, gateway, record)["status"] == "failed"
    assert len(gateway.writes) == 1 and not gateway.uploads
