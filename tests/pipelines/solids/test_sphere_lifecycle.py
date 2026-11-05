"""Frozen preparation and mandatory readback on local fake transport only."""

import pytest
from midpoint_source_cases import section
from sphere_source_cases import CASES, GROUPS, arguments
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
def test_every_native_prepares_without_side_effect_then_mock_roundtrip_and_resume(case):
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
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize(
    "task,target",
    [
        ("74405", "asset:image_1"),
        ("74405", "section:condition:1"),
        ("74405", "section:solution"),
        ("76607", "asset:image_1"),
        ("76607", "section:condition:1"),
        ("76607", "section:solution"),
        ("75311", "section:answer:1"),
        ("75311", "section:solution"),
        ("76349", "section:solution:1"),
        ("76363", "section:solution"),
    ],
)
def test_restored_figures_new_solutions_and_corrected_answer_require_readback(
    task, target
):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("drift", ["condition", "answer"])
def test_frozen_drift_blocks_before_any_local_write(group, drift):
    case = next(c for c in CASES if c["task"] == group)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, drift)["html"] += "<p>Изменено.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.writes and not gateway.uploads
