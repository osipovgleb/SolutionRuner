"""Verify native reuse, legacy role repair, generated SVGs and strict frozen readback."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import section
from polyhedron_source_cases import CASES, GROUPS, arguments
from test_midpoint_area_lifecycle import OfflineGateway
from test_polyhedron_preparation import condition

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
def test_every_native_frozen_roundtrip_reuses_sources_and_resumes_without_upload(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    assert record["generated_diagrams"] == []
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert not gateway.uploads and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


def generated_case(group):
    case = deepcopy(next(c for c in CASES if c["task"] == group))
    current = section(case["context"], "condition")
    image = BeautifulSoup(current["html"], "html.parser").find("img")
    current["html"] = condition(("A", "B", "C", "D", "D_1")).replace(
        "<p>", "<p>" + str(image), 1
    )
    return case


@pytest.mark.parametrize("group", ["639664", "245338"])
def test_new_condition_or_solution_svg_is_materialized_once_locally(group):
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
    "group,target",
    [
        ("639664", "asset:box_polyhedron_condition"),
        ("639664", "section:condition:1"),
        ("245338", "asset:box_polyhedron_solution"),
        ("245338", "section:solution:1"),
    ],
)
def test_missing_generated_figure_or_section_readback_fails(group, target):
    case = generated_case(group)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize(
    "target",
    ["asset:image_1", "asset:image_2", "section:condition:1", "section:solution:1"],
)
def test_legacy_image_key_owner_repair_requires_complete_readback(target):
    case = next(c for c in CASES if c["task"] == "264513")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("drift", ["condition", "answer", "svg", "sha"])
def test_frozen_drift_blocks_before_local_upload_or_write(drift):
    case = generated_case("639664")
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
