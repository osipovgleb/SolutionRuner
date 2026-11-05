"""Offline preparation, exact figure repair and frozen-input protection."""

from copy import deepcopy

import pytest
from adjacent_midpoint_source_cases import CASES, GROUPS, arguments
from midpoint_source_cases import section
from test_midpoint_area_lifecycle import OfflineGateway
from test_pyramid_midsections_lifecycle import without_figures

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
@pytest.mark.parametrize("missing", (False, True))
def test_offline_roundtrip_restores_and_reuses_without_upload(case, missing):
    context = without_figures(case) if missing else deepcopy(case["context"])
    gateway = OfflineGateway({**case, "context": context})
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.writes and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1
    if missing:
        assert [
            a["asset_id"] for a in gateway.context["normalized_content"]["assets"]
        ] == [a["asset_id"] for a in case["context"]["normalized_content"]["assets"]]
    else:
        assert (
            gateway.context["normalized_content"]["assets"]
            == case["context"]["normalized_content"]["assets"]
        )
    for key in ("condition", "source", "criteria"):
        assert section(gateway.context, key) == section(context, key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("key", ("condition", "criteria", "solution"))
def test_frozen_input_changes_refuse_local_write(case, key):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, key)["html"] += "<p>Изменение</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.writes and not gateway.uploads


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_wrong_known_figure_is_replaced_with_exact_compatible_native(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    correct = old = asset["asset_id"]
    other = next(
        c
        for c in CASES
        if c["task"] in {"500639", "511345"}
        and c["context"]["normalized_content"]["assets"][0]["asset_id"] != old
    )
    uid = other["context"]["normalized_content"]["assets"][0]["asset_id"]
    asset["asset_id"], asset["url"] = uid, "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    gateway = OfflineGateway({**case, "context": ctx})
    record = prepared(case, gateway)
    assert record["status"] == "prepared", record
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert gateway.context["normalized_content"]["assets"][0]["asset_id"] == correct
    assert not gateway.uploads


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_figure_is_blocked_before_transformation(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old, uid = asset["asset_id"], "00000000-0000-4000-8000-000000000001"
    asset["asset_id"], asset["url"] = uid, "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    gateway = OfflineGateway({**case, "context": ctx})
    record = prepared(case, gateway)
    assert record["status"] == "blocked"
    assert not record.get("transformations")
    assert not gateway.uploads and not gateway.writes
