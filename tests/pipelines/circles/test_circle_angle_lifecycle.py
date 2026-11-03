"""Only local fake transport exercises frozen circle assets and readback."""

import pytest
from bs4 import BeautifulSoup
from circle_angle_source_cases import CASES, GROUPS, arguments, plan
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
def test_all_native_frozen_roundtrips_materialize_only_numbered_arcs_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert record["expected_answer"] == plan(case).answer
    assert apply_offline(case, gateway, record)["status"] == "applied"
    expected = 1 if case["group"] == "27866" else 0
    assert len(gateway.uploads) == expected and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == expected and len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize("group", GROUPS)
def test_missing_images_restore_the_parent_role_without_duplicate_operations(group):
    case = next(c for c in CASES if c["task"] == group)
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
    assert len(gateway.context["normalized_content"]["assets"]) == 1
    assert len(gateway.uploads) == (1 if group == "27866" else 0)
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize(
    "task,prefix",
    [
        ("51343", "asset:circle"),
        ("51343", "section:condition"),
        ("245387", "asset:image_1"),
        ("245387", "section:solution"),
    ],
)
def test_missing_figure_or_solution_readback_is_not_success(task, prefix):
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
def test_strict_frozen_drift_blocks_before_local_upload_or_write(change):
    case = next(c for c in CASES if c["task"] == "51343")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if change == "svg":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        section(gateway.context, change)["html"] += "<p>Другие данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes
