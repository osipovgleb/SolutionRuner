"""Offline gateways exercise preview IDs, source reuse and authoritative readback."""

import hashlib
import json
import uuid
from copy import deepcopy

import pytest
from ray_source_cases import CASES, GROUPS, parent_html
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)


class OfflineGateway:
    def __init__(self, case, *, omit_condition_write=False):
        self.context = deepcopy(case["context"])
        self.uploads = []
        self.writes = []
        self.metadata = {}
        self.omit_condition_write = omit_condition_write

    def get_problem_context(self, identifier):
        assert identifier == self.context["problem_id"]
        return deepcopy(self.context)

    def get_source_asset(self, identifier):
        return {"source_asset": self.metadata[identifier]}

    def get_problem_asset_target_context(self, identifier, target):
        assert identifier == self.context["problem_id"] and target == "asset:image_1"
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
            t
            for t in transformations
            if not (
                self.omit_condition_write
                and t["transformation_target_id"].startswith("section:condition")
            )
        ]
        replay(self.context, changes)
        return {"problem_id": identifier, "applied_count": len(changes)}


def prepared(case, gateway):
    group = GROUPS[case["group"]]
    return _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        group["parent_asset"],
        group["rule"],
        parent_solution_html=parent_html(case["group"]),
    )


def apply_offline(case, gateway, record):
    group = GROUPS[case["group"]]
    return _apply_record(
        gateway,
        record,
        group["parent_asset"],
        group["rule"],
        parent_solution_html=parent_html(case["group"]),
    )


@pytest.mark.parametrize("task", ["47625", "47673", "641148", "500908"])
def test_local_frozen_roundtrip_substitutes_real_ids_checks_readback_and_resumes(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    result = apply_offline(case, gateway, record)
    assert result["status"] == "applied", result
    expected_uploads = 1 if task in {"47673", "641148"} else 0
    assert len(gateway.uploads) == expected_uploads and len(gateway.writes) == 1
    assert len(gateway.context["normalized_content"]["assets"]) == 1
    # Use the runtime's metadata reader, which accepts real UUIDs after the local upload.
    assert apply_offline(case, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == expected_uploads and len(gateway.writes) == 1


@pytest.mark.parametrize("task", ["47673", "641148", "500908"])
def test_missing_condition_readback_is_not_reported_as_success(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case, omit_condition_write=True)
    result = apply_offline(case, gateway, prepared(case, gateway))
    assert result["status"] == "failed"


def test_drifted_generated_diagram_is_blocked_before_local_upload_or_write():
    case = next(c for c in CASES if c["task"] == "47673")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    record["generated_diagrams"][0]["svg_text"] += " "
    result = apply_offline(case, gateway, record)
    assert result["status"] == "failed" and "diagram drifted" in result["message"]
    assert not gateway.uploads and not gateway.writes
