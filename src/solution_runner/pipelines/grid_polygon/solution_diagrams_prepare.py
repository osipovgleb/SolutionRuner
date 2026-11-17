"""Validate uploaded diagrams before creating solution transformations."""

from typing import Any

from .solution_html import _centered_asset_html


def _prepare_diagrams(uploaded):
    from .solution_plan import SolutionRuntimeError

    centered_diagrams: list[tuple[int, str]] = []
    diagram_items: list[dict[str, Any]] = []
    asset_target_ids: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    asset_key_order: list[str] = []
    for item in uploaded:
        asset_key = str(item.get("asset_key") or "")
        source_asset_id = str(item.get("source_asset_id") or "")
        asset_url = str(item.get("url") or "")
        alt_text = str(item.get("alt_text") or "")
        try:
            variant_index = int(item.get("solution_variant_index") or 0)
        except (TypeError, ValueError) as exc:
            raise SolutionRuntimeError("solution diagram variant is invalid") from exc
        if (
            not asset_key
            or asset_key in seen_keys
            or not source_asset_id
            or not asset_url
        ):
            raise SolutionRuntimeError("uploaded solution asset identity is incomplete")
        seen_keys.add(asset_key)
        asset_key_order.append(asset_key)
        centered = _centered_asset_html(
            asset_key=asset_key,
            source_asset_id=source_asset_id,
            asset_url=asset_url,
            alt_text=alt_text,
        )
        centered_diagrams.append((variant_index, centered))
        diagram_items.append(
            {**item, "html": centered, "asset_position": len(diagram_items)}
        )
        asset_target_ids.append((f"asset:{asset_key}", source_asset_id))
    return (
        centered_diagrams,
        diagram_items,
        asset_target_ids,
        seen_keys,
        asset_key_order,
    )
