"""Verify pyramid preparation, mock roundtrips, restored assets and frozen drift."""

import pytest
from midpoint_source_cases import section
from pyramid_source_cases import CASES, GROUPS, arguments
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


@pytest.mark.parametrize(
    "task,target",
    [
        ("284679", "asset:pyramid_named_solution"),
        ("285039", "asset:pyramid_named_solution"),
        ("76489", "asset:image_1"),
        ("76507", "section:solution:1"),
    ],
)
def test_missing_method_or_diagram_readback_is_failure(task, target):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case, omit=target)
    assert apply_offline(case, gateway, prepared(case, gateway))["status"] == "failed"


def test_frozen_named_diagram_tamper_blocks_local_write():
    case = next(c for c in CASES if c["task"] == "284679")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    record["generated_diagrams"][0]["svg_text"] += " "
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


def test_missing_retained_solution_asset_is_detected_on_readback():
    class MissingRetainedAsset(OfflineGateway):
        def apply_problem_transformations(self, identifier, transformations):
            result = super().apply_problem_transformations(identifier, transformations)
            self.context["normalized_content"]["assets"] = [
                a
                for a in self.context["normalized_content"]["assets"]
                if a["asset_key"] != "image_2"
            ]
            return result

    case = next(c for c in CASES if c["task"] == "27070")
    gateway = MissingRetainedAsset(case)
    assert apply_offline(case, gateway, prepared(case, gateway))["status"] == "failed"
