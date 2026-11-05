"""Verify read-only preparation, mock roundtrips, restored assets and frozen drift."""

import pytest
from cylinder_source_cases import CASES, GROUPS, arguments
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
def test_native_prepare_has_no_side_effect_and_mock_roundtrip_reuses_all_assets(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert (
        record["status"] == "prepared"
        and record["generated_diagrams"] == []
        and not gateway.uploads
        and not gateway.writes
    )
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize(
    "task,target",
    [
        ("72673", "asset:image_1"),
        ("72673", "section:condition:1"),
        ("72673", "section:solution"),
        ("75601", "asset:image_1"),
        ("75601", "section:condition:1"),
        ("76557", "asset:image_1"),
        ("76557", "section:condition:1"),
        ("285801", "asset:image_1"),
        ("285801", "section:solution"),
    ],
)
def test_restored_assets_condition_or_solution_requires_complete_readback(task, target):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("drift", ["condition", "answer"])
def test_frozen_drift_prevents_local_writes(group, drift):
    case = next(c for c in CASES if c["task"] == group)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, drift)["html"] += "<p>Изменено.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
