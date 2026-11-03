"""Only local fake transport materializes the two frozen trapezoid drawings."""

import pytest
from altitude_trapezoid_source_cases import CASES, GROUPS, arguments, plan
from bs4 import BeautifulSoup
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
def test_all_native_frozen_roundtrips_materialize_both_ids_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert record["expected_answer"] == plan(case).answer
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == 2 and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == 2 and len(gateway.writes) == 1
    assert len(gateway.context["normalized_content"]["assets"]) == 2
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize(
    "task,prefix",
    [
        ("27633", "asset:trapezoid"),
        ("27633", "section:condition"),
        ("27633", "section:solution"),
        ("57223", "asset:trapezoid"),
        ("57223", "section:condition"),
        ("57307", "asset:trapezoid"),
        ("57307", "section:solution"),
    ],
)
def test_lost_asset_or_section_readback_is_not_success(task, prefix):
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
def test_frozen_input_and_svg_drift_block_before_local_upload(change):
    case = next(c for c in CASES if c["task"] == "57307")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if change == "svg":
        record["generated_diagrams"][1]["svg_text"] += " "
    else:
        section(gateway.context, change)["html"] += "<p>Другие данные.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("task", ["27633", "27634", "27637", "27638"])
def test_missing_native_images_restore_both_roles_without_duplicate_operations(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    for sec in gateway.context["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    gateway.context["normalized_content"]["assets"] = []
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    targets = [
        (t["transformation_target_id"], t["operation"])
        for t in record["transformations"]
    ]
    assert len(targets) == len(set(targets))
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == 2
