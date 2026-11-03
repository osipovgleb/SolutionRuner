"""Only local fake transport materializes and verifies the frozen preparations."""

import pytest
from bs4 import BeautifulSoup
from iso_trapezoid_source_cases import CASES, GROUPS, arguments, plan
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
def test_all_native_local_roundtrips_upload_once_verify_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert record["expected_answer"] == plan(case).answer
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert len(gateway.uploads) == 1 and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == 1 and len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize(
    "task,prefix",
    [
        ("27439", "asset:iso"),
        ("27439", "section:condition"),
        ("27439", "section:solution"),
        ("519802", "asset:iso"),
        ("519802", "section:solution"),
        ("27635", "asset:iso"),
        ("27635", "section:solution"),
        ("27834", "section:solution"),
        ("27837", "asset:iso"),
    ],
)
def test_missing_asset_or_solution_readback_is_a_failure(task, prefix):
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
def test_strict_frozen_drift_blocks_before_local_upload_and_write(change):
    case = next(c for c in CASES if c["task"] == "61309")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if change == "svg":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        section(gateway.context, change)["html"] += "<p>Другие данные.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"blocked", "failed"}
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("task", ["27439", "519802", "27635", "27837"])
def test_all_missing_assets_restore_reviewed_roles_locally(task):
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
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == 1


@pytest.mark.parametrize("task", ["519802", "57107"])
def test_missing_bare_condition_with_surviving_image_two_has_no_duplicate_removals(
    task,
):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    condition = section(gateway.context, "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    soup.find("img").decompose()
    condition["html"], condition["asset_keys"] = str(soup), []
    gateway.context["normalized_content"]["assets"] = [
        a
        for a in gateway.context["normalized_content"]["assets"]
        if a["asset_key"] != "image_1"
    ]
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    targets = [
        (t["transformation_target_id"], t["operation"])
        for t in record["transformations"]
    ]
    assert len(targets) == len(set(targets))
    assert apply_offline(case, gateway, record)["status"] == "applied"
