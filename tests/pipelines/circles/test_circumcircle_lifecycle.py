"""Only local fake transport verifies static circumcircle figure reuse."""

import pytest
from bs4 import BeautifulSoup
from circumcircle_source_cases import CASES, GROUPS, arguments, plan, read
from midpoint_source_cases import section
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.circles.circumcircle_figures import DETAILS
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
def test_native_frozen_roundtrips_reuse_sources_and_resume_without_uploads(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == plan(case).answer
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert not gateway.uploads and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert not gateway.uploads and len(gateway.writes) == 1
    assert read(gateway.context) == read(case["context"])
    assert section(gateway.context, "source") == section(case["context"], "source")


def remove_images(gateway):
    for sec in gateway.context["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    gateway.context["normalized_content"]["assets"] = []


@pytest.mark.parametrize("group", GROUPS)
def test_missing_pictures_restore_all_roles_without_duplicates_or_uploads(group):
    case = next(c for c in CASES if c["task"] == group)
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    pairs = [
        (t["transformation_target_id"], t["operation"])
        for t in record["transformations"]
    ]
    assert len(pairs) == len(set(pairs))
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert not gateway.uploads
    assert len(gateway.context["normalized_content"]["assets"]) == 1 + len(
        DETAILS.get(read(case["context"]).mode, ())
    )
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize(
    "prefix",
    ["asset:image_1", "section:condition", "section:solution"],
)
def test_missing_readback_for_either_diagram_or_section_is_not_success(prefix):
    case = next(c for c in CASES if c["task"] == "27895")
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    gateway.omit = next(
        t["transformation_target_id"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith(prefix)
    )
    assert apply_offline(case, gateway, record)["status"] == "failed"
    assert not gateway.uploads


@pytest.mark.parametrize("change", ["condition", "answer", "assets"])
def test_frozen_input_changes_block_before_write(change):
    case = next(c for c in CASES if c["task"] == "52549")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["expected_answer"] == "3"
    if change == "assets":
        gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    else:
        section(gateway.context, change)["html"] += "<p>Другие данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
