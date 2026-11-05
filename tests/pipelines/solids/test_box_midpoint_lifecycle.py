"""Use local fake transport for source reuse, generated diagrams and mandatory readback."""

from copy import deepcopy

import pytest
from box_midpoint_source_cases import CASES, arguments
from midpoint_source_cases import section
from test_box_midpoint_preparation import RULE, condition
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
        content_rule_key=RULE,
        **arguments("315131"),
    )


def apply_offline(case, gateway, record):
    return _apply_record(gateway, record, content_rule_key=RULE, **arguments("315131"))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_prepare_no_writes_then_mock_roundtrip_without_upload_and_resume(case):
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and record["generated_diagrams"] == []
    assert not gateway.writes and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1


def generated_case(with_condition):
    case = deepcopy(CASES[1] if with_condition else CASES[-1])
    current = section(case["context"], "condition")
    html = condition("B_1", "C_1", "A")
    if with_condition:
        from bs4 import BeautifulSoup

        image = BeautifulSoup(current["html"], "html.parser").img
        html = html.replace("<p>", "<p>" + str(image), 1)
    current["html"] = html
    return case


@pytest.mark.parametrize("with_condition", [False, True])
def test_one_or_two_relabelled_figures_mock_upload_once_then_resume(with_condition):
    case = generated_case(with_condition)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert (
        record["status"] == "prepared"
        and len(record["generated_diagrams"]) == 1 + with_condition
    )
    assert not gateway.writes and not gateway.uploads
    assert apply_offline(case, gateway, record)["status"] == "applied"
    assert len(gateway.writes) == 1 and len(gateway.uploads) == 1 + with_condition
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1 and len(gateway.uploads) == 1 + with_condition


@pytest.mark.parametrize(
    "target",
    [
        "asset:box_midpoint_condition",
        "asset:box_midpoint_solution",
        "section:condition:1",
        "section:solution:1",
    ],
)
def test_each_generated_picture_and_section_requires_readback(target):
    case = generated_case(True)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    gateway.omit = target
    assert target in {t["transformation_target_id"] for t in record["transformations"]}
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("drift", ["condition", "answer", "svg", "sha"])
def test_frozen_drift_blocks_before_any_local_upload_or_write(drift):
    case = generated_case(True)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if drift in {"svg", "sha"}:
        record["generated_diagrams"][0]["svg_text" if drift == "svg" else "sha256"] += (
            "changed"
        )
    else:
        section(gateway.context, drift)["html"] += "<p>Изменено.</p>"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.writes and not gateway.uploads
