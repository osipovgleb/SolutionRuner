"""Verify orthogonal-volume preparation, mock roundtrips, retained drawings and frozen drift."""

import pytest
from midpoint_source_cases import section
from orthogonal_source_cases import CASES, GROUPS, arguments
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
def test_native_prepare_has_no_side_effect_and_mock_roundtrip_reuses_all_assets(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1
    assert len(gateway.uploads) == len(record["generated_diagrams"])
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("drift", ["condition", "answer"])
def test_frozen_drift_prevents_local_writes(group, drift):
    case = next(c for c in CASES if c["task"] == group)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, drift)["html"] += "<p>Изменено.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


def test_missing_published_method_is_failure():
    case = CASES[0]
    gateway = OfflineGateway(case, omit="section:solution:1")
    assert apply_offline(case, gateway, prepared(case, gateway))["status"] == "failed"


def test_missing_retained_numeric_drawing_is_failure():
    class LostNumericAsset(OfflineGateway):
        def apply_problem_transformations(self, identifier, transformations):
            result = super().apply_problem_transformations(identifier, transformations)
            self.context["normalized_content"]["assets"] = []
            return result

    case = CASES[0]
    gateway = LostNumericAsset(case)
    assert apply_offline(case, gateway, prepared(case, gateway))["status"] == "failed"


def test_current_numeric_asset_drift_blocks_local_writes():
    case = CASES[0]
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.writes and not gateway.uploads
