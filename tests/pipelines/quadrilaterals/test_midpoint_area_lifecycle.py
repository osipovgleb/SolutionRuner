"""Local fake transport verifies mixed figures, missing assets and frozen replay."""

import hashlib
import json
import uuid
from copy import deepcopy

import pytest
from midpoint_source_cases import CASES, GROUPS, parent_arguments, replay, section

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)


class OfflineGateway:
    def __init__(self, case, *, omit=None):
        self.context = deepcopy(case["context"])
        self.omit = omit
        self.uploads, self.writes, self.metadata = [], [], {}

    def get_problem_context(self, identifier):
        assert identifier == self.context["problem_id"]
        return deepcopy(self.context)

    def get_source_asset(self, identifier):
        return {"source_asset": self.metadata[identifier]}

    def get_problem_asset_target_context(self, identifier, target):
        assert identifier == self.context["problem_id"] and target.startswith("asset:")
        return {"problem_id": identifier, "transformation_target_id": target}

    def upload_solution_asset(self, *, source_problem_id, svg_bytes, sha256):
        assert hashlib.sha256(svg_bytes).hexdigest() == sha256
        identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, sha256))
        metadata = {
            "source_asset_id": identifier,
            "url": "/assets/" + identifier,
            "sha256": sha256,
        }
        self.metadata[identifier] = metadata
        self.uploads.append((source_problem_id, svg_bytes, sha256))
        return metadata

    def apply_problem_transformations(self, identifier, transformations):
        assert identifier == self.context["problem_id"]
        assert "preview-" not in json.dumps(transformations)
        self.writes.append(deepcopy(transformations))
        changes = [
            t for t in transformations if t["transformation_target_id"] != self.omit
        ]
        replay(self.context, changes)
        return {"problem_id": identifier, "applied_count": len(changes)}


def prepare(case, gateway):
    return _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=GROUPS[case["group"]]["rule"],
        **parent_arguments(case["group"]),
    )


def apply_offline(case, gateway, record):
    return _apply_record(
        gateway,
        record,
        content_rule_key=GROUPS[case["group"]]["rule"],
        **parent_arguments(case["group"]),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_frozen_roundtrips_reuse_sources_and_resume_without_duplicates(case):
    gateway = OfflineGateway(case)
    record = prepare(case, gateway)
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    assert len(gateway.uploads) == (1 if case["task"] == "317439" else 0)
    assert len(gateway.writes) == 1
    assert section(gateway.context, "condition") == section(
        case["context"], "condition"
    )
    assert section(gateway.context, "source") == section(case["context"], "source")
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.writes) == 1


@pytest.mark.parametrize(
    "task,target",
    [
        ("319063", "asset:image_1"),
        ("530550", "asset:image_2"),
        ("637806", "section:solution:1"),
    ],
)
def test_missing_figure_or_method_readback_is_reported_as_failure(task, target):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case, omit=target)
    result = apply_offline(case, gateway, prepare(case, gateway))
    assert result["status"] == "failed", result


@pytest.mark.parametrize("drift", ["diagram", "condition", "answer"])
def test_frozen_drift_is_blocked_before_local_upload_or_write(drift):
    case = next(c for c in CASES if c["task"] == "317439")
    gateway = OfflineGateway(case)
    record = prepare(case, gateway)
    if drift == "diagram":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        section(gateway.context, drift)["html"] += "<p>Другие данные.</p>"
    result = apply_offline(case, gateway, record)
    assert result["status"] in {"failed", "blocked"}, result
    assert not gateway.uploads and not gateway.writes
