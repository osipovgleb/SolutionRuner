"""Local fake transport verifies frozen plans, exact source reuse and readback."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import section
from spatial_altitude_source_cases import CASES, GROUPS, arguments, plan, read
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_model import condition_text


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
def test_native_roundtrips_reuse_exact_assets_without_uploads_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert (
        gateway.context["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )
    for key in ("condition", "source", "criteria"):
        assert section(gateway.context, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("key", ("condition", "criteria", "solution"))
def test_frozen_input_changes_stop_before_mock_write(case, key):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, key)["html"] += "<p>Изменение</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


def without_figures(case):
    ctx = deepcopy(case["context"])
    for sec in ctx["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    ctx["normalized_content"]["assets"] = []
    return ctx


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_reviewed_methods_without_duplicate_targets(case):
    gateway = OfflineGateway({**case, "context": without_figures(case)})
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    targets = [
        (t["operation"], t["transformation_target_id"])
        for t in record["transformations"]
    ]
    assert len(targets) == len(set(targets))
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.context["normalized_content"]["assets"]) == (
        2 if case["group"] == "514474" else 1
    )
    assert not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_source_asset_is_refused(case):
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    old = a["asset_id"]
    a["asset_id"] = uid = "00000000-0000-4000-8000-000000000001"
    a["url"] = "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("missing", ("section:solution:1", "asset:image_1"))
def test_missing_solution_or_restored_asset_readback_is_failure(case, missing):
    gateway = OfflineGateway({**case, "context": without_figures(case)}, omit=missing)
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads


def test_changed_numbers_never_reuse_the_numeric_parent_prism_diagram():
    case = next(c for c in CASES if c["task"] == "514474")
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    for old, new in (
        ("равна 6", "равна 12"),
        (r"3\sqrt{2}", r"6\sqrt{2}"),
        ("BK = 4", "BK = 8"),
        ("C_1L = 5", "C_1L = 10"),
    ):
        assert old in raw
        raw = raw.replace(old, new)
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    assert read(ctx).answer == 2 * read(case["context"]).answer
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_foot_outside_the_face_does_not_reuse_an_interior_foot_diagram():
    case = next(c for c in CASES if c["task"] == "505153")
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    raw = raw.replace("ребро равно 5", "ребро равно 6").replace(
        "основания равна 6", "основания равна 9"
    )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    assert read(ctx).q["foot"] < 0
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
