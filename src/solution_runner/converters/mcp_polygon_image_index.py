"""Validate and index the source catalog's section images."""

from __future__ import annotations

from typing import Any

if __package__:
    from .mcp_polygon_models import PipelineError
else:
    from mcp_polygon_models import PipelineError


def _normalized_content_type(value: Any) -> str:
    """Normalize an optional media type without parameters."""

    return str(value or "").split(";", 1)[0].strip().lower()


def _validate_image_scope(images_payload, catalog_snapshot_id, group):
    """Reject image inventories that escape the selected catalog or group."""
    returned_scope = images_payload.get("scope")
    if not isinstance(returned_scope, dict):
        raise PipelineError("section-image response has no exact scope")
    if str(returned_scope.get("catalog_snapshot_id") or "") != catalog_snapshot_id:
        raise PipelineError("section-image response escaped the fixed catalog")
    returned_group_ids = {
        str(value) for value in returned_scope.get("source_group_ids", [])
    }
    if returned_group_ids != {group.source_group_id}:
        raise PipelineError("section-image response escaped the fixed source group")
    try:
        concrete_problem_count = int(images_payload["concrete_problem_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PipelineError(
            "section-image response has no concrete problem count"
        ) from exc
    if concrete_problem_count < 0:
        raise PipelineError("section-image response has a negative problem count")

    return concrete_problem_count


def _index_section_images(images_payload):
    """Group normalized image occurrences by source problem and section."""
    images_by_source_problem: dict[str, dict[tuple[str, str, str], set[str]]] = {}
    for section in ("condition", "solution"):
        section_payload = images_payload.get(section, {})
        problems = (
            section_payload.get("problems", [])
            if isinstance(section_payload, dict)
            else []
        )
        for problem in problems:
            if not isinstance(problem, dict):
                continue
            source_problem_id = str(problem.get("source_problem_id") or "")
            if not source_problem_id:
                raise PipelineError(
                    "section-image response contains an empty source problem id"
                )
            bucket = images_by_source_problem.setdefault(source_problem_id, {})
            for image in problem.get("images", []):
                if not isinstance(image, dict):
                    continue
                identity = (
                    str(image.get("asset_key") or ""),
                    str(image.get("kind") or ""),
                    _normalized_content_type(image.get("content_type")),
                )
                if identity[0]:
                    bucket.setdefault(identity, set()).add(section)

    return images_by_source_problem
