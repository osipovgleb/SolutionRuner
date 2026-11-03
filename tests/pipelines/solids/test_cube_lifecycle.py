"""Local fake transport only: frozen cube plans, image restoration and readback."""

import pytest
from bs4 import BeautifulSoup
from cube_source_cases import CASES, GROUPS, arguments, plan
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
def test_native_frozen_roundtrip_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == plan(case).answer
    assert not gateway.writes and not gateway.uploads
    expected = int(case["group"] == "315130" and case["task"] != "315130")
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert len(gateway.uploads) == expected and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == expected and len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


def remove_images(gateway):
    for sec in gateway.context["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    gateway.context["normalized_content"]["assets"] = []


@pytest.mark.parametrize("group", GROUPS)
def test_missing_picture_restored_once_in_its_correct_section(group):
    case = next(c for c in CASES if c["task"] == group)
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert not gateway.uploads
    assert len(gateway.context["normalized_content"]["assets"]) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize(
    "target", ["asset:image_1", "section:condition:1", "section:solution:1"]
)
def test_omitted_readback_does_not_report_success(target):
    case = next(c for c in CASES if c["task"] == "27056")
    gateway = OfflineGateway(case, omit=target)
    remove_images(gateway)
    result = apply_offline(case, gateway, prepared(case, gateway))
    assert result["status"] == "failed", result


@pytest.mark.parametrize("change", ["condition", "answer", "diagram"])
def test_frozen_changes_fail_before_fake_upload_or_write(change):
    case = next(c for c in CASES if c["task"] == "320147")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if change == "diagram":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        section(gateway.context, change)["html"] += "<p>Другие данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.writes and not gateway.uploads


def test_section_native_to_opposite_corner_and_back_replaces_one_solution_asset():
    parent = next(c for c in CASES if c["task"] == "315130")
    child = next(c for c in CASES if c["task"] == "320147")
    gateway = OfflineGateway(parent)
    for original in (parent, child, parent):
        section(gateway.context, "condition")["html"] = section(
            original["context"], "condition"
        )["html"]
        record = prepared(parent, gateway)
        assert record["status"] == "prepared", record
        result = apply_offline(parent, gateway, record)
        assert result["status"] == "applied", result
        assert len(gateway.context["normalized_content"]["assets"]) == 1
        assert section(gateway.context, "condition")["asset_keys"] == []
        assert apply_offline(parent, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == 1
