"""Apply validated frozen content transformations and resolve diagram assets."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from typing import Any

from .content_context import _context_fingerprint
from .content_diagrams import _generated_diagram_assets
from .content_gateway import RightTriangleGateway
from .errors import ContentPlanError as RightTrianglePlanError


def _has_current_image(context: dict[str, Any]) -> bool:
    """Return whether image_1 currently exists and therefore needs target readback."""

    content = context.get("normalized_content")
    assets = content.get("assets") if isinstance(content, dict) else None
    return any(
        isinstance(item, dict) and item.get("asset_key") == "image_1"
        for item in (assets if isinstance(assets, list) else [])
    )


def _write_frozen_apply(
    gateway: RightTriangleGateway,
    record: dict[str, Any],
    parent: Any,
    prepared: Any,
    *,
    registered_handler: Callable[..., Any],
) -> tuple[bool, list[dict[str, Any]]]:
    """Write the verified transformations and resolve diagram identities."""

    problem_id = str(record.get("problem_id") or "")
    source_problem_id = str(record.get("source_problem_id") or "")
    content_rule_key = parent.rule_key
    context = prepared.context
    handler = prepared.handler
    condition_asset_bytes = prepared.condition_asset_bytes
    diagram_specs = prepared.diagram_specs
    generated_assets = prepared.generated_assets
    current_transformations = prepared.current_transformations
    frozen = prepared.frozen
    changed = False
    if current_transformations:
        if registered_handler(
            content_rule_key
        ).strict_frozen_input and _context_fingerprint(context) != record.get(
            "input_fingerprint"
        ):
            raise RightTrianglePlanError("frozen input drifted; prepare again")
        if current_transformations != frozen:
            raise RightTrianglePlanError("current repair differs from frozen manifest")
        if any(
            item.get("transformation_target_id") == "asset:image_1" for item in frozen
        ) and _has_current_image(context):
            gateway.get_problem_asset_target_context(problem_id, "asset:image_1")
        if diagram_specs:
            uploaded_assets = _generated_diagram_assets(
                gateway,
                context,
                diagram_specs,
                source_problem_id,
                apply=True,
                **(
                    {"condition_asset_bytes": condition_asset_bytes}
                    if handler.diagram_builder_uses_condition_bytes
                    else {}
                ),
            )
            encoded = json.dumps(frozen, ensure_ascii=False)
            for preview, uploaded in zip(generated_assets, uploaded_assets):
                encoded = encoded.replace(
                    preview["source_asset_id"], uploaded["source_asset_id"]
                )
            frozen = json.loads(encoded)
        gateway.apply_problem_transformations(problem_id, deepcopy(frozen))
        changed = True
    if diagram_specs:
        encoded = json.dumps(frozen, ensure_ascii=False)
        for spec, asset in zip(diagram_specs, generated_assets):
            encoded = encoded.replace(
                "preview-" + spec["sha256"][:16], asset["source_asset_id"]
            )
        frozen = json.loads(encoded)
    return changed, frozen
