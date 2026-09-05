"""Discover one explicit group's eligible raster and SVG condition targets."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Protocol

from .models import GroupProfile, ProblemTarget


RASTER_CONTENT_TYPES = frozenset({"image/png", "image/bmp", "image/x-ms-bmp"})


class InventoryError(RuntimeError):
    """Report source scope or normalized-content inventory drift."""


class InventoryGateway(Protocol):
    """Expose the read-only MCP operations required for target discovery."""

    def get_source_catalog_children(
        self,
        parent_id: str,
        parent_type: str,
    ) -> dict[str, Any]:
        """Return ordered group children."""

    def get_source_catalog_section_images(
        self,
        target_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Return compact current condition and solution image evidence."""

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Return current source identities whose solution is empty."""

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Return the current normalized status."""

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Return current normalized content and assets."""

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Return authoritative metadata for one normalized asset identity."""


@dataclass(frozen=True)
class GroupInventory:
    """Freeze ordered eligible targets split by current condition asset type."""

    targets: tuple[ProblemTarget, ...]
    png_targets: tuple[ProblemTarget, ...]
    svg_targets: tuple[ProblemTarget, ...]


@dataclass(frozen=True)
class _ChildIdentity:
    """Carry one validated child identity into independent MCP reads."""

    problem_id: str
    source_problem_id: str
    order_index: int


def _content_type(asset: dict[str, Any]) -> str:
    """Normalize one current asset content type."""

    return str(asset.get("content_type") or "").split(";", 1)[0].strip().lower()


def _classify_target(
    gateway: InventoryGateway,
    profile: GroupProfile,
    identity: _ChildIdentity,
    asset: dict[str, Any],
) -> tuple[ProblemTarget, str] | None:
    """Return one eligible target and its current asset bucket."""

    state = gateway.get_problem_pipeline_state(identity.problem_id)
    statuses = state.get("statuses")
    normalized = (
        str(statuses.get("normalized") or "")
        if isinstance(statuses, dict)
        else ""
    )
    if normalized not in {"ready", "rejected"}:
        return None
    if normalized == "rejected":
        return None
    target = ProblemTarget(
        problem_id=identity.problem_id,
        source_problem_id=identity.source_problem_id,
        source_group_id=profile.source_group_id,
        group_key=profile.group_key,
        problem_order_index=identity.order_index,
    )
    kind = _content_type(asset)
    if not kind:
        asset_id = str(asset.get("asset_id") or "")
        if not asset_id:
            raise InventoryError(
                f"task {identity.source_problem_id} image_1 has no asset identity"
            )
        metadata = gateway.get_asset_metadata(asset_id)
        if str(metadata.get("asset_id") or "") != asset_id:
            raise InventoryError(
                f"task {identity.source_problem_id} image_1 metadata identity drifted"
            )
        kind = _content_type(metadata)
    if kind in RASTER_CONTENT_TYPES:
        return target, "raster"
    if kind == "image/svg+xml":
        return target, "svg"
    raise InventoryError(
        f"task {identity.source_problem_id} has unsupported image_1 type {kind!r}"
    )


def _content_rule_target(
    gateway: InventoryGateway,
    profile: GroupProfile,
    identity: _ChildIdentity,
) -> ProblemTarget | None:
    """Return one ready non-rejected task without requiring a current image."""

    state = gateway.get_problem_pipeline_state(identity.problem_id)
    statuses = state.get("statuses")
    normalized = (
        str(statuses.get("normalized") or "")
        if isinstance(statuses, dict)
        else ""
    )
    if normalized != "ready":
        return None
    return ProblemTarget(
        problem_id=identity.problem_id,
        source_problem_id=identity.source_problem_id,
        source_group_id=profile.source_group_id,
        group_key=profile.group_key,
        problem_order_index=identity.order_index,
    )


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
        matches = [
            image
            for image in images if isinstance(image, dict)
            and image.get("asset_key") == "image_1"
            and image.get("kind") == "ordinary_image"
        ] if isinstance(images, list) else []
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


def _audit_scope(
    gateway: InventoryGateway,
    profile: GroupProfile,
    *,
    max_workers: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Read group identities, section images, and missing solutions concurrently."""

    with ThreadPoolExecutor(max_workers=min(3, max_workers)) as executor:
        children = executor.submit(
            gateway.get_source_catalog_children,
            profile.source_group_id,
            "group",
        )
        images = executor.submit(
            gateway.get_source_catalog_section_images,
            profile.source_group_id,
            "group",
        )
        missing = executor.submit(
            gateway.get_source_catalog_missing_solution_summary,
            profile.source_group_id,
            "group",
        )
        return children.result(), images.result(), missing.result()


def _child_identities(children: dict[str, Any]) -> tuple[_ChildIdentity, ...]:
    """Validate and normalize one group's ordered child identities."""

    raw_items = children.get("items")
    if not isinstance(raw_items, list):
        raise InventoryError("source group children are missing")
    identities: list[_ChildIdentity] = []
    seen_problem_ids: set[str] = set()
    seen_source_ids: set[str] = set()
    for order_index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise InventoryError("source group child is not an object")
        name = str(item.get("name") or "")
        problem_id = str(item.get("uuid") or "")
        if not name.startswith("Задача ") or not problem_id:
            raise InventoryError("source group child has no canonical problem identity")
        source_problem_id = name.removeprefix("Задача ").strip()
        if (
            not source_problem_id
            or source_problem_id in seen_source_ids
            or problem_id in seen_problem_ids
        ):
            raise InventoryError("source group contains duplicate problem identity")
        seen_problem_ids.add(problem_id)
        seen_source_ids.add(source_problem_id)
        identities.append(
            _ChildIdentity(
                problem_id=problem_id,
                source_problem_id=source_problem_id,
                order_index=order_index,
            )
        )
    return tuple(identities)


def _requested_identities(
    identities: tuple[_ChildIdentity, ...],
    *,
    source_problem_ids: tuple[str, ...],
    problem_ids: tuple[str, ...],
) -> tuple[_ChildIdentity, ...]:
    """Select exact group members without reading any problem content."""

    if bool(source_problem_ids) == bool(problem_ids):
        raise InventoryError("targeted inventory requires exactly one problem selector")
    requested = set(problem_ids or source_problem_ids)
    if len(requested) != len(problem_ids or source_problem_ids):
        raise InventoryError("targeted inventory contains duplicate problem selectors")
    field = "problem_id" if problem_ids else "source_problem_id"
    selected = tuple(
        identity for identity in identities if getattr(identity, field) in requested
    )
    if {getattr(identity, field) for identity in selected} != requested:
        flag = "--only-problem-id" if problem_ids else "--only-source-problem-id"
        raise InventoryError(f"{flag} is outside the selected source group")
    return selected


def discover_targeted_inventory(
    gateway: InventoryGateway,
    profile: GroupProfile,
    *,
    source_problem_ids: tuple[str, ...] = (),
    problem_ids: tuple[str, ...] = (),
    max_workers: int = 1,
) -> GroupInventory:
    """Inventory only explicit members plus a content-rule parent when required."""

    if max_workers <= 0:
        raise ValueError("max_workers must be positive")
    children = gateway.get_source_catalog_children(profile.source_group_id, "group")
    identities = _child_identities(children)
    selected = _requested_identities(
        identities,
        source_problem_ids=source_problem_ids,
        problem_ids=problem_ids,
    )
    if profile.workflow_kind == "content_rule":
        if not identities:
            raise InventoryError("content-rule group has no parent problem")
        selected_problem_ids = {identity.problem_id for identity in selected}
        candidates = tuple(
            identity
            for identity in identities
            if identity is identities[0] or identity.problem_id in selected_problem_ids
        )
        classify_content = lambda identity: _content_rule_target(
            gateway, profile, identity
        )
        if max_workers == 1:
            classified = tuple(map(classify_content, candidates))
        else:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(candidates))) as executor:
                classified = tuple(executor.map(classify_content, candidates))
        targets = tuple(target for target in classified if target is not None)
        if not targets or targets[0].problem_id != identities[0].problem_id:
            raise InventoryError("content-rule parent is not ready")
        return GroupInventory(targets=targets, png_targets=(), svg_targets=())

    # Geometry workflows still need the compact group audits to locate image_1
    # and determine solution eligibility, but only selected problems receive
    # state, context, or asset-metadata reads.
    with ThreadPoolExecutor(max_workers=min(2, max_workers)) as executor:
        images_future = executor.submit(
            gateway.get_source_catalog_section_images,
            profile.source_group_id,
            "group",
        )
        missing_future = executor.submit(
            gateway.get_source_catalog_missing_solution_summary,
            profile.source_group_id,
            "group",
        )
        section_images = images_future.result()
        missing_solutions = missing_future.result()
    assets_by_source_problem_id = _condition_assets(section_images)
    missing_source_problem_ids = _source_problem_ids(missing_solutions)
    generated_source_problem_ids = _pipeline_generated_solution_ids(section_images)
    if profile.solution_scope == "all":
        eligible_source_problem_ids = set(assets_by_source_problem_id)
    elif profile.solution_scope == "missing_only":
        eligible_source_problem_ids = set(assets_by_source_problem_id) & missing_source_problem_ids
    else:
        eligible_source_problem_ids = set(assets_by_source_problem_id) & (
            missing_source_problem_ids | generated_source_problem_ids
        )
    eligible = tuple(
        identity
        for identity in selected
        if identity.source_problem_id in eligible_source_problem_ids
    )
    classify = lambda identity: _classify_target(
        gateway,
        profile,
        identity,
        assets_by_source_problem_id[identity.source_problem_id],
    )
    if max_workers == 1:
        classified = tuple(map(classify, eligible))
    else:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(eligible) or 1)) as executor:
            classified = tuple(executor.map(classify, eligible))
    present = tuple(item for item in classified if item is not None)
    targets = tuple(target for target, _ in present)
    return GroupInventory(
        targets=targets,
        png_targets=tuple(target for target, kind in present if kind == "raster"),
        svg_targets=tuple(target for target, kind in present if kind == "svg"),
    )


def discover_group_inventory(
    gateway: InventoryGateway,
    profile: GroupProfile,
    *,
    max_workers: int = 1,
) -> GroupInventory:
    """Return every non-rejected ready problem with one ordinary image_1."""

    if max_workers <= 0:
        raise ValueError("max_workers must be positive")
    children, section_images, missing_solutions = _audit_scope(
        gateway,
        profile,
        max_workers=max_workers,
    )
    identities = _child_identities(children)
    if profile.workflow_kind == "content_rule":
        classify_content = lambda identity: _content_rule_target(
            gateway,
            profile,
            identity,
        )
        if max_workers == 1:
            content_targets = tuple(map(classify_content, identities))
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                content_targets = tuple(executor.map(classify_content, identities))
        targets = tuple(target for target in content_targets if target is not None)
        return GroupInventory(targets=targets, png_targets=(), svg_targets=())
    assets_by_source_problem_id = _condition_assets(section_images)
    missing_source_problem_ids = _source_problem_ids(missing_solutions)
    generated_source_problem_ids = _pipeline_generated_solution_ids(section_images)
    if profile.solution_scope == "all":
        eligible_source_problem_ids = set(assets_by_source_problem_id)
    elif profile.solution_scope == "missing_only":
        eligible_source_problem_ids = (
            set(assets_by_source_problem_id) & missing_source_problem_ids
        )
    else:
        eligible_source_problem_ids = set(assets_by_source_problem_id) & (
            missing_source_problem_ids | generated_source_problem_ids
        )
    selected_identities = tuple(
        identity
        for identity in identities
        if identity.source_problem_id in eligible_source_problem_ids
    )
    classify = lambda identity: _classify_target(
        gateway,
        profile,
        identity,
        assets_by_source_problem_id[identity.source_problem_id],
    )
    if max_workers == 1:
        classified = tuple(map(classify, selected_identities))
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            classified = tuple(executor.map(classify, selected_identities))
    eligible = tuple(item for item in classified if item is not None)
    targets = tuple(target for target, _ in eligible)
    return GroupInventory(
        targets=targets,
        png_targets=tuple(target for target, kind in eligible if kind == "raster"),
        svg_targets=tuple(target for target, kind in eligible if kind == "svg"),
    )
