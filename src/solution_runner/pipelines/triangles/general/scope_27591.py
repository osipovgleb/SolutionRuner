"""Audited scope checks for group 27591; independent of task content repair."""
from typing import Any
from solution_runner.pipelines.core.errors import ContentPlanError as RightTrianglePlanError


def validate_manifest(gateway, manifest: dict[str, Any]) -> None:
    """Reject shared scope/inventory corruption, never task-local content errors."""
    from solution_runner.pipelines.core.content_runtime import _children, _problem_identity
    from solution_runner.pipelines.triangles.general.planner import PARENT_ASSET_ID
    from solution_runner.pipelines.core.group_profiles import get_group_profile

    profile = get_group_profile("27591")
    if (manifest.get("catalog_snapshot_id") != profile.catalog_snapshot_id
            or manifest.get("source_group_id") != profile.source_group_id
            or manifest.get("source_group_number") != profile.group_key
            or manifest.get("schema_version") != 1
            or manifest.get("solution_assets") != []
            or (manifest.get("condition_asset") or {}).get("source_asset_id") != PARENT_ASSET_ID):
        raise RightTrianglePlanError("group 27591 manifest scope or assets drifted")
    records = manifest["records"]
    ids = [record.get("problem_id") for record in records]
    if not records or not all(ids) or len(set(ids)) != len(ids):
        raise RightTrianglePlanError("group 27591 manifest identities are invalid")
    membership = dict(_problem_identity(child) for child in _children(
        gateway.get_source_catalog_children(profile.source_group_id, "group")
    ))
    for record in records:
        if membership.get(record["problem_id"]) != record.get("source_problem_id"):
            raise RightTrianglePlanError("group 27591 catalog membership drifted")
        if record.get("status") not in {"prepared", "blocked"}:
            raise RightTrianglePlanError("group 27591 frozen record status is invalid")
        if not isinstance(record.get("transformations"), list):
            raise RightTrianglePlanError("group 27591 frozen repairs are invalid")
        if record["status"] == "prepared" and (
                not record.get("expected_answer") or not record.get("input_fingerprint")):
            raise RightTrianglePlanError("group 27591 frozen record is incomplete")
