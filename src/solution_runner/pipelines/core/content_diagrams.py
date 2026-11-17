"""Verify, reuse and upload content-rule diagram assets."""

import hashlib

from .errors import ContentPlanError as RightTrianglePlanError


def _generated_diagram_assets(
    gateway,
    context,
    specs,
    source_problem_id,
    *,
    apply=False,
    condition_asset_bytes=None,
):
    """Reuse checksum-verified solution assets or prepare preview/upload identities."""
    result = []
    for spec in specs:
        svg_bytes = spec["svg_text"].encode()
        digest = hashlib.sha256(svg_bytes).hexdigest()
        if digest != spec["sha256"]:
            raise RightTrianglePlanError("generated diagram checksum changed")
        existing = next(
            (
                a
                for a in (context.get("normalized_content") or {}).get("assets", [])
                if a.get("asset_key") == spec["asset_key"]
            ),
            None,
        )
        asset = None
        if existing:
            condition_keys = next(
                (
                    section.get("asset_keys", [])
                    for section in (context.get("normalized_content") or {}).get(
                        "sections", []
                    )
                    if section.get("key") == "condition"
                ),
                [],
            )
            if (
                isinstance(condition_asset_bytes, bytes)
                and existing.get("asset_key") in condition_keys
            ):
                # The opt-in builder already downloaded this exact condition image.
                metadata = {"sha256": hashlib.sha256(condition_asset_bytes).hexdigest()}
            else:
                metadata = (
                    gateway.get_source_asset(existing["asset_id"]).get("source_asset")
                    or {}
                )
            if metadata.get("sha256") == digest:
                asset = {
                    "source_asset_id": existing["asset_id"],
                    "url": existing["url"],
                    "sha256": digest,
                }
        if asset is None and apply:
            asset = gateway.upload_solution_asset(
                source_problem_id=source_problem_id, svg_bytes=svg_bytes, sha256=digest
            )
        if asset is None:
            asset = {
                "source_asset_id": "preview-" + digest[:16],
                "url": "/assets/preview-" + digest[:16],
                "sha256": digest,
            }
        result.append({**asset, "asset_key": spec["asset_key"]})
    return tuple(result)
