"""Local fake transport verifies strict frozen reuse without any asset upload."""

import pytest
from bs4 import BeautifulSoup
from midline_trapezoid_source_cases import CASES, GROUPS, arguments, plan
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
def test_all_native_frozen_roundtrips_reuse_exact_sources_without_uploads(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == plan(case).answer
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert not gateway.uploads and len(gateway.writes) == 1
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert not gateway.uploads and len(gateway.writes) == 1
    assert section(gateway.context, "condition") == section(
        case["context"], "condition"
    )
    assert section(gateway.context, "source") == section(case["context"], "source")


def remove_images(gateway):
    for sec in gateway.context["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    gateway.context["normalized_content"]["assets"] = []


@pytest.mark.parametrize("group", GROUPS)
def test_missing_figures_restore_originals_without_duplicate_operations_or_uploads(
    group,
):
    case = next(c for c in CASES if c["task"] == group)
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    targets = [
        (t["transformation_target_id"], t["operation"])
        for t in record["transformations"]
    ]
    assert len(targets) == len(set(targets))
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert not gateway.uploads
    fields = ("asset_key", "asset_id", "url", "kind", "alt")
    assert [
        tuple(asset[key] for key in fields)
        for asset in gateway.context["normalized_content"]["assets"]
    ] == [
        tuple(asset[key] for key in fields)
        for asset in case["context"]["normalized_content"]["assets"]
    ]
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize(
    "prefix",
    ["asset:image_1", "asset:image_2", "section:condition", "section:solution"],
)
def test_missing_readback_for_either_figure_or_method_is_not_success(prefix):
    case = next(c for c in CASES if c["task"] == "27843")
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
def test_strict_frozen_drift_blocks_before_any_local_write(change):
    case = next(c for c in CASES if c["task"] == "50833")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if change == "assets":
        gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    else:
        section(gateway.context, change)["html"] += "<p>Другие данные.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"blocked", "failed"}
    assert not gateway.uploads and not gateway.writes
