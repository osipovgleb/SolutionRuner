"""Only a local fake gateway materializes the frozen bisector preparations."""

import pytest
from bisector_source_cases import CASES, GROUPS, arguments, plan
from midpoint_source_cases import section
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
def test_all_native_frozen_local_roundtrips_verify_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and not gateway.writes and not gateway.uploads
    assert record["expected_answer"] == plan(case).answer
    assert apply_offline(case, gateway, record)["status"] == "applied"
    dynamic = case["group"] != "27827"
    assert len(gateway.uploads) == int(dynamic) and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == int(dynamic) and len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize(
    "task,prefix",
    [
        ("27826", "asset:quantity"),
        ("27826", "section:condition"),
        ("27826", "section:solution"),
        ("282851", "asset:quantity"),
        ("282851", "section:solution"),
        ("283357", "asset:quantity"),
        ("283357", "section:solution"),
        ("27827", "section:solution"),
    ],
)
def test_missing_asset_or_section_readback_is_reported_as_failure(task, prefix):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    gateway.omit = next(
        t["transformation_target_id"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith(prefix)
    )
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("change", ["condition", "answer", "svg"])
def test_frozen_drift_blocks_before_local_upload_or_write(change):
    case = next(c for c in CASES if c["task"] == "283357")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if change == "svg":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        section(gateway.context, change)["html"] += "<p>Другие данные.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"blocked", "failed"}
    assert not gateway.uploads and not gateway.writes
