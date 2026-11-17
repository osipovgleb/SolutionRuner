"""Run the legacy manifest workflow with task-level failure isolation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .content_context import _children, _problem_identity
from .content_gateway import RightTriangleGateway
from .content_services import _helpers_update
from .errors import ContentPlanError as RightTrianglePlanError


def run_manifest(
    gateway: RightTriangleGateway,
    manifest: dict[str, Any],
    *,
    apply: bool,
    services: Any,
) -> dict[str, Any]:
    """Discover, repair, verify, and optionally mark ready one manifest group."""

    if services._registered_handler(
        manifest.get("content_rule_key")
    ).requires_frozen_manifest:
        raise RightTrianglePlanError(
            "registered handler requires the shared frozen-manifest launcher"
        )

    source_group_id = str(manifest.get("source_group_id") or "")
    parent_asset_id = str(
        (manifest.get("condition_asset") or {}).get("source_asset_id") or ""
    )
    content_rule_key = manifest.get("content_rule_key")
    if content_rule_key is not None and not isinstance(content_rule_key, str):
        raise RightTrianglePlanError("manifest content rule is invalid")
    services._planner_constraints(content_rule_key)
    raw_solution_assets = manifest.get("solution_assets", [])
    if not isinstance(raw_solution_assets, list) or not all(
        isinstance(item, dict) for item in raw_solution_assets
    ):
        raise RightTrianglePlanError("manifest solution assets are invalid")
    parent_solution_assets = tuple(deepcopy(item) for item in raw_solution_assets)
    selection = manifest.get("selection") or {}
    skipped = {str(value) for value in selection.get("skip_source_problem_ids", [])}
    if not source_group_id or (
        not parent_asset_id
        and services._requires_parent_condition_asset(content_rule_key)
    ):
        raise RightTrianglePlanError(
            "manifest requires source_group_id and parent asset"
        )
    results: list[dict[str, Any]] = []
    verified_ids: list[str] = []
    for child in _children(
        gateway.get_source_catalog_children(source_group_id, "group")
    ):
        problem_id, source_problem_id = _problem_identity(child)
        if source_problem_id in skipped:
            results.append(
                {
                    "source_problem_id": source_problem_id,
                    "problem_id": problem_id,
                    "status": "skipped",
                    "transformations": [],
                }
            )
            continue
        try:
            context = gateway.get_problem_context(problem_id)
            plan = services._build_content_plan(
                context,
                parent_asset_id=parent_asset_id,
                content_rule_key=content_rule_key,
                parent_solution_assets=parent_solution_assets,
                parent_solution_html=str(manifest.get("parent_solution_html") or ""),
            )
            targets = [
                item["transformation_target_id"] for item in plan.transformations
            ]
            if not apply:
                results.append(
                    {
                        "source_problem_id": source_problem_id,
                        "problem_id": problem_id,
                        "status": "planned",
                        "transformations": targets,
                    }
                )
                continue
            if plan.transformations:
                if "asset:image_1" in targets:
                    gateway.get_problem_asset_target_context(
                        problem_id, "asset:image_1"
                    )
                gateway.apply_problem_transformations(
                    problem_id, list(plan.transformations)
                )
            verified_ids.append(problem_id)
            results.append(
                {
                    "source_problem_id": source_problem_id,
                    "problem_id": problem_id,
                    "status": "applied" if plan.transformations else "already_complete",
                    "transformations": targets,
                }
            )
        except Exception as exc:  # noqa: BLE001 - retain one failure per task.
            results.append(
                {
                    "source_problem_id": source_problem_id,
                    "problem_id": problem_id,
                    "status": "failed",
                    "transformations": [],
                    "message": " ".join(str(exc).split())[:500],
                }
            )
    if apply:
        for result in results:
            if result["problem_id"] not in verified_ids:
                continue
            try:
                _helpers_update(gateway, result["problem_id"])
                result["helpers"] = "ready"
            except Exception as exc:  # noqa: BLE001 - content remains verified if state fails.
                result["helpers"] = "failed"
                result["helpers_message"] = " ".join(str(exc).split())[:500]
    return {
        "planned_count": sum(item["status"] == "planned" for item in results),
        "applied_count": sum(item["status"] == "applied" for item in results),
        "already_complete_count": sum(
            item["status"] == "already_complete" for item in results
        ),
        "failed_count": sum(item["status"] == "failed" for item in results),
        "results": results,
    }
