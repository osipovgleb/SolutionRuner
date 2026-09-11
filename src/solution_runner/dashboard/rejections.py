"""Reject one explicitly selected dashboard task through TeacherHelper MCP."""

from pathlib import Path
from typing import Any

from solution_runner.group_inventory_store import GroupInventoryStore

from .previews import load_preview, preview_path, save_preview


def reject_indexed_problem(
    gateway: Any,
    inventory: GroupInventoryStore,
    preview_dir: Path,
    group_key: str,
    problem_id: str,
    reason: str,
) -> dict[str, str]:
    reason = reason.strip()
    if not reason:
        raise ValueError("rejection reason is required")
    snapshot = inventory.get(group_key)
    if snapshot is None:
        raise KeyError(group_key)
    item = next((item for item in snapshot.items if item.problem_id == problem_id), None)
    if item is None:
        raise KeyError(problem_id)
    if problem_id == snapshot.parent_problem_id:
        raise ValueError("the group parent cannot be rejected from the task table")

    write_error = None
    try:
        gateway.reject_problem_content_pipeline(problem_id, reason)
    except Exception as exc:  # noqa: BLE001 - ambiguous writes are resolved by readback.
        write_error = exc
    state = gateway.get_problem_pipeline_state(problem_id)
    statuses = state.get("statuses") if isinstance(state, dict) else None
    if not isinstance(statuses, dict) or statuses.get("normalized") != "rejected":
        raise RuntimeError("reject write was not confirmed by readback") from write_error

    inventory.remove_item(group_key, problem_id)
    preview = load_preview(preview_dir, group_key)
    if preview:
        preview["samples"] = [
            sample for sample in preview.get("samples", [])
            if not isinstance(sample, dict) or str(sample.get("problem_id")) != problem_id
        ]
        if preview["samples"]:
            save_preview(preview_dir, preview)
        else:
            preview_path(preview_dir, group_key).unlink(missing_ok=True)
    return {
        "problem_id": problem_id,
        "source_problem_id": item.source_problem_id,
        "status": "rejected",
    }
