"""The shared frozen runtime is exercised only through a local fake gateway."""

import pytest
from bs4 import BeautifulSoup
from linear_source_cases import CASES, GROUPS, arguments, plan
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
def test_all_native_local_roundtrips_have_readback_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and not gateway.writes and not gateway.uploads
    assert record["expected_answer"] == plan(case).answer
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1
    assert section(gateway.context, "source") == section(case["context"], "source")


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["task"] == c["group"]], ids=lambda c: c["task"]
)
@pytest.mark.parametrize("omit", [None, "asset:image_1", "section:solution"])
def test_missing_figures_are_restored_exactly_and_partial_readback_fails(case, omit):
    gateway = OfflineGateway(case, omit=omit)
    condition = section(gateway.context, "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    for image in soup.find_all("img"):
        image.decompose()
    condition["html"], condition["asset_keys"] = str(soup), []
    gateway.context["normalized_content"]["assets"] = []
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and not gateway.writes and not gateway.uploads
    if omit == "section:solution":
        gateway.omit = next(
            t["transformation_target_id"]
            for t in record["transformations"]
            if t["transformation_target_id"].startswith("section:solution")
        )
    result = apply_offline(case, gateway, record)
    assert result["status"] == ("applied" if omit is None else "failed")
    if omit is None:
        assert (
            gateway.context["normalized_content"]["assets"][0]["asset_id"]
            == arguments(case["group"])["parent_asset_id"]
        )


@pytest.mark.parametrize("change", ["condition", "answer"])
def test_frozen_drift_blocks_before_local_write(change):
    case = CASES[1]
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    section(gateway.context, change)["html"] += "<p>Иные данные.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"blocked", "failed"}
    assert not gateway.writes and not gateway.uploads
