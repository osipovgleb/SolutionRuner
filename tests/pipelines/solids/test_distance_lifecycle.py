"""Local fake transport verifies frozen spatial diagrams and exact content readback."""

import pytest
from distance_source_cases import CASES, GROUPS, arguments, plan, read
from midpoint_source_cases import section
from test_cube_lifecycle import remove_images
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.handler_registry import get_handler


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
def test_native_frozen_roundtrip_uploads_only_needed_figures_and_resumes(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    expected = len(
        get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    )
    assert (
        record["status"] == "prepared"
        and record["expected_answer"] == plan(case).answer
    ), record
    assert not gateway.writes and not gateway.uploads
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert len(gateway.uploads) == expected and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == expected and len(gateway.writes) == 1
    assert read({**case, "context": gateway.context}) == read(case)
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize("group", GROUPS)
def test_missing_parent_figures_restore_all_roles_without_uploads(group):
    case = next(c for c in CASES if c["task"] == group)
    gateway = OfflineGateway(case)
    remove_images(gateway)
    if group == "245360":
        # Use the already proven corrected text after deliberately removing its image.
        original = plan(case)
        fixed = next(
            t["value"]["html"]
            for t in original.transformations
            if t["transformation_target_id"].startswith("section:condition")
        )
        section(gateway.context, "condition")["html"] = fixed
        remove_images(gateway)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert not gateway.uploads
    assert len(gateway.context["normalized_content"]["assets"]) == (
        2 if group in {"245359", "245360"} else 1
    )
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize(
    "task,target",
    [
        ("270573", "asset:box_distance_condition"),
        ("270573", "asset:box_distance_solution"),
        ("270573", "section:condition:1"),
        ("270573", "section:solution"),
        ("245360", "section:condition:1"),
    ],
)
def test_missing_asset_or_section_readback_never_reports_success(task, target):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    gateway.omit = target
    result = apply_offline(case, gateway, record)
    assert result["status"] == "failed", result


@pytest.mark.parametrize("drift", ["condition", "answer", "svg", "sha"])
def test_changed_frozen_input_blocks_before_upload_or_write(drift):
    case = next(c for c in CASES if c["task"] == "270573")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if drift == "svg":
        record["generated_diagrams"][0]["svg_text"] += " "
    elif drift == "sha":
        record["generated_diagrams"][0]["sha256"] = "0" * 64
    else:
        section(gateway.context, drift)["html"] += "<p>Другие данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.writes and not gateway.uploads


def test_parent_subscript_restoration_is_an_actual_condition_transformation():
    case = next(c for c in CASES if c["task"] == "245360")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    changes = [
        t
        for t in record["transformations"]
        if t["transformation_target_id"].startswith("section:condition")
    ]
    assert (
        len(changes) == 1
        and "D_1" in changes[0]["value"]["html"]
        and "AA_1" in changes[0]["value"]["html"]
    )
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert (
        '<var data-math-identifier="AA">'
        not in section(gateway.context, "condition")["html"]
    )
    assert (
        section(case["context"], "condition")["html"]
        != section(gateway.context, "condition")["html"]
    )


def test_unreviewed_corrupt_text_without_its_pinned_image_is_not_guessed():
    case = next(c for c in CASES if c["task"] == "245360")
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    assert (
        record["status"] in {"failed", "blocked"}
        and not gateway.uploads
        and not gateway.writes
    )
