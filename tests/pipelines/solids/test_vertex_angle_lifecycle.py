"""Exercise frozen preparation, strict readback and resumed local fake writes."""

from copy import deepcopy

import pytest
from midpoint_source_cases import section
from test_box_vertex_angles import condition
from test_midpoint_area_lifecycle import OfflineGateway
from vertex_angle_source_cases import CASES, GROUPS, arguments

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
def test_native_frozen_roundtrips_resume_and_only_upload_new_solution(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == (1 if case["task"] == "271575" else 0)
    assert len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


def condition_case():
    case = deepcopy(next(c for c in CASES if c["task"] == "245363"))
    from bs4 import BeautifulSoup

    current = section(case["context"], "condition")
    image = BeautifulSoup(current["html"], "html.parser").find("img")
    current["html"] = condition("ABD_1", "AB=5, AD=4, AA_1=3").replace(
        "<p>", "<p>" + str(image), 1
    )
    return case


def test_generated_condition_freezes_materializes_and_preserves_source():
    case = condition_case()
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and len(record["generated_diagrams"]) == 1
    assert not gateway.writes and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize(
    "target",
    ["asset:box_vertex_angle_condition", "section:condition:1", "section:solution:1"],
)
def test_missing_generated_condition_or_solution_readback_fails(target):
    case = condition_case()
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("drift", ["condition", "answer", "svg", "sha"])
def test_frozen_drift_blocks_before_upload_or_write(drift):
    case = condition_case()
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
