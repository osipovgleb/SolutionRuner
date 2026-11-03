"""Only local fake transport applies plans, including mixed solution and condition images."""

import pytest
from midpoint_source_cases import section
from quantity_source_cases import CASES, GROUPS, arguments
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)


def prepared(case, gw):
    return _prepared_record(
        gw,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )


def apply_offline(case, gw, record):
    return _apply_record(
        gw,
        record,
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_frozen_roundtrips_materialize_correct_ids_verify_and_resume(case):
    gw = OfflineGateway(case)
    record = prepared(case, gw)
    assert record["status"] == "prepared", record
    assert not gw.writes and not gw.uploads
    result = apply_offline(case, gw, record)
    assert result["status"] == "applied", result
    dynamic = (
        case["group"] == "27436" or case["group"] == "27611" and case["task"] != "27611"
    )
    assert len(gw.uploads) == int(dynamic)
    assert len(gw.writes) == 1
    assert apply_offline(case, gw, record)["status"] == "already_complete"
    assert len(gw.writes) == 1 and len(gw.uploads) == int(dynamic)
    assert section(gw.context, "source") == section(case["context"], "source")
    if case["task"] == "56453":
        assert section(gw.context, "condition")["asset_keys"] == ["image_1"]
        assert section(gw.context, "solution")["asset_keys"] == []


@pytest.mark.parametrize(
    "task,omitted",
    [
        ("44409", "section:condition:1"),
        ("56157", "section:solution"),
        ("56257", "asset:image_1"),
        ("56453", "section:condition:1"),
    ],
)
def test_missing_condition_or_solution_readback_is_not_success(task, omitted):
    case = next(c for c in CASES if c["task"] == task)
    gw = OfflineGateway(case, omit=omitted)
    result = apply_offline(case, gw, prepared(case, gw))
    assert result["status"] == "failed", result


@pytest.mark.parametrize("kind", ["condition", "answer", "svg"])
def test_frozen_drift_blocks_before_local_upload_or_write(kind):
    case = next(c for c in CASES if c["task"] == "44409")
    gw = OfflineGateway(case)
    record = prepared(case, gw)
    if kind == "svg":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        section(gw.context, kind)["html"] += "<p>Другие данные.</p>"
    result = apply_offline(case, gw, record)
    assert result["status"] in {"failed", "blocked"}, result
    assert not gw.writes and not gw.uploads
