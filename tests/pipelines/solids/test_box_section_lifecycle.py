"""Verify preparation, legacy owner moves and frozen readback using local fakes only."""

from copy import deepcopy

import pytest
from box_section_source_cases import CASES, GROUPS, arguments
from midpoint_source_cases import section
from test_box_section_preparation import condition
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
def test_all_native_preparations_have_no_side_effect_and_local_roundtrip_reuses_assets(
    case,
):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and record["generated_diagrams"] == []
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


def generated_case(group):
    case = deepcopy(next(c for c in CASES if c["task"] == group))
    section(case["context"], "condition")["html"] = condition(("B", "B_1", "D"))
    return case


@pytest.mark.parametrize("group", GROUPS)
def test_actual_new_plane_mock_materialization_and_resume(group):
    case = generated_case(group)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and len(record["generated_diagrams"]) == 1
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == len(gateway.writes) == 1


@pytest.mark.parametrize(
    "target",
    ["asset:image_1", "asset:image_2", "section:condition:1", "section:solution:1"],
)
def test_legacy_condition_to_solution_move_requires_all_readback(target):
    case = next(c for c in CASES if c["task"] == "507883")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("target", ["asset:box_section_solution", "section:solution:1"])
def test_generated_diagram_and_solution_readback_mandatory(target):
    case = generated_case("316552")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("drift", ["condition", "answer", "svg", "sha"])
def test_frozen_drift_blocks_before_local_upload_or_write(drift):
    case = generated_case("316552")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if drift in {"svg", "sha"}:
        record["generated_diagrams"][0]["svg_text" if drift == "svg" else "sha256"] += (
            "changed"
        )
    else:
        section(gateway.context, drift)["html"] += "<p>Другие данные.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
