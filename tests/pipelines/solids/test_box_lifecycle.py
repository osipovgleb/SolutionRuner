"""Local fake transport only: static box assets, frozen plans and readback."""

import pytest
from box_source_cases import CASES, GROUPS, arguments, plan
from midpoint_source_cases import section
from test_cube_lifecycle import remove_images
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)


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
def test_native_frozen_roundtrip_uses_no_upload_and_resumes_without_duplicates(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert (
        record["status"] == "prepared"
        and record["expected_answer"] == plan(case).answer
    ), record
    assert not gateway.writes and not gateway.uploads
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert not gateway.uploads and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1 and section(gateway.context, "source") == section(
        case["context"], "source"
    )


@pytest.mark.parametrize("group", GROUPS)
def test_missing_box_image_is_restored_once_in_the_condition(group):
    case = next(c for c in CASES if c["task"] == group)
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert (
        not gateway.uploads
        and len(gateway.context["normalized_content"]["assets"]) == 1
    )
    assert section(gateway.context, "condition")["asset_keys"] == ["image_1"]
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize(
    "target", ["asset:image_1", "section:condition:1", "section:solution:1"]
)
def test_missing_readback_does_not_report_success(target):
    case = next(c for c in CASES if c["task"] == "27054")
    gateway = OfflineGateway(case, omit=target)
    remove_images(gateway)
    result = apply_offline(case, gateway, prepared(case, gateway))
    assert result["status"] == "failed", result


@pytest.mark.parametrize("change", ["condition", "answer", "asset"])
def test_frozen_changes_stop_before_local_write(change):
    case = next(c for c in CASES if c["task"] == "27054")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if change == "asset":
        gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    else:
        section(gateway.context, change)["html"] += "<p>Другие данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
