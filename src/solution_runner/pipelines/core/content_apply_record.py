"""Apply one frozen content record with target-local failure isolation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .content_gateway import RightTriangleGateway


@dataclass(frozen=True)
class _ParentContent:
    """Inputs inherited from the reviewed parent for a frozen repair."""

    asset_id: str | None
    rule_key: str | None
    solution_assets: tuple[dict[str, str], ...]
    solution_html: str


def _apply_record(
    gateway: RightTriangleGateway,
    record: dict[str, Any],
    parent_asset_id: str | None,
    content_rule_key: str | None,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
    parent_solution_html: str = "",
    *,
    services: Any,
) -> dict[str, Any]:
    """Converge one frozen record through content and Helpers readback."""

    problem_id = str(record.get("problem_id") or "")
    source_problem_id = str(record.get("source_problem_id") or "")
    if record.get("status") != "prepared":
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "blocked",
            "message": str(record.get("message") or "manifest record is blocked"),
        }
    try:
        parent = _ParentContent(
            parent_asset_id,
            content_rule_key,
            parent_solution_assets,
            parent_solution_html,
        )
        prepared = services._prepare_frozen_apply(gateway, record, parent)
        changed, frozen = services._write_frozen_apply(
            gateway, record, parent, prepared
        )
        context = prepared.context
        current_plan = prepared.current_plan
        if (
            services._registered_handler(content_rule_key).presentation_only
            or services._registered_handler(content_rule_key).verify_content_readback
        ):
            services._verify_content_readback(
                gateway,
                record,
                context,
                frozen,
                parent,
            )
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "applied" if changed else "already_complete",
            **(
                {"message": "; ".join(current_plan.warnings)}
                if getattr(current_plan, "warnings", ())
                else {}
            ),
        }
    except Exception as exc:  # noqa: BLE001 - preserve one target-local failure.
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "failed",
            "message": " ".join(str(exc).split())[:500],
        }
