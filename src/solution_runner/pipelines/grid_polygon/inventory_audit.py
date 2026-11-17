"""Validate compact source inventory and image evidence."""

from typing import Any


class InventoryError(RuntimeError):
    """Report source scope or normalized-content inventory drift."""


def _source_problem_ids(payload: dict[str, Any]) -> set[str]:
    """Return one validated compact audit source-identity set."""

    values = payload.get("source_problem_ids")
    if not isinstance(values, list) or any(not str(value).strip() for value in values):
        raise InventoryError("missing-solution audit has invalid source_problem_ids")
    return {str(value).strip() for value in values}


def _section_problem_rows(
    payload: dict[str, Any],
    section_key: str,
) -> list[dict[str, Any]]:
    """Return validated problem rows for one compact section-image bucket."""

    section = payload.get(section_key)
    rows = section.get("problems") if isinstance(section, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise InventoryError(f"section-image audit has invalid {section_key} problems")
    return rows


def _condition_assets(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index the unique ordinary image_1 rendered in each current condition."""

    result: dict[str, dict[str, Any]] = {}
    for row in _section_problem_rows(payload, "condition"):
        source_problem_id = str(row.get("source_problem_id") or "").strip()
        images = row.get("images")
        matches = (
            [
                image
                for image in images
                if isinstance(image, dict)
                and image.get("asset_key") == "image_1"
                and image.get("kind") == "ordinary_image"
            ]
            if isinstance(images, list)
            else []
        )
        if not source_problem_id:
            raise InventoryError("condition-image audit has no source problem identity")
        if not matches:
            continue
        if len(matches) != 1 or source_problem_id in result:
            raise InventoryError("condition-image audit has ambiguous ordinary image_1")
        result[source_problem_id] = matches[0]
    return result


def _pipeline_generated_solution_ids(payload: dict[str, Any]) -> set[str]:
    """Return tasks whose current solution renders the pipeline diagram asset."""

    result: set[str] = set()
    for row in _section_problem_rows(payload, "solution"):
        images = row.get("images")
        if isinstance(images, list) and any(
            isinstance(image, dict)
            and image.get("asset_key") == "generated_solution_diagram"
            for image in images
        ):
            source_problem_id = str(row.get("source_problem_id") or "").strip()
            if source_problem_id:
                result.add(source_problem_id)
    return result
