"""Only local fake transport: frozen replay, generated images and readback failures."""

import pytest
from midpoint_source_cases import section
from prism_metric_source_cases import CASES, GROUPS, arguments
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
def test_native_prepare_is_read_only_and_mock_roundtrip_stable(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    expected_uploads = len(record["generated_diagrams"])
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert len(gateway.uploads) == expected_uploads and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == expected_uploads and len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize("task", ["273055", "316755", "245365"])
@pytest.mark.parametrize("drift", ["condition", "answer"])
def test_frozen_drift_blocks_local_write(task, drift):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, drift)["html"] += "<p>Изменено.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize(
    "target", ["asset:prism_metric_solution", "section:solution", "asset:image_1"]
)
def test_missing_readback_is_failure(target):
    case = next(c for c in CASES if c["task"] == "273055")
    gateway = OfflineGateway(case, omit=target)
    assert apply_offline(case, gateway, prepared(case, gateway))["status"] == "failed"


def test_frozen_generated_drawing_tamper_blocks_local_write():
    case = next(c for c in CASES if c["task"] == "273055")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    record["generated_diagrams"][0]["svg_text"] += " "
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
