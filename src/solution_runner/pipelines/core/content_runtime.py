"""Run manifest-scoped content repairs for all mathematical domains."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from solution_runner.pipelines.core import (
    content_apply_batch,
    content_apply_prepare,
    content_apply_record,
    content_assets,
    content_context,
    content_diagrams,
    content_legacy_run,
    content_manifest,
    content_prepare_record,
    content_services,
    content_stage,
    content_verify,
    content_write,
)
from solution_runner.pipelines.core.content_gateway import RightTriangleGateway
from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)
from solution_runner.pipelines.core.models import (
    GroupProfile,
    ProblemStageResult,
    ProblemTarget,
)
from solution_runner.pipelines.grid_polygon.progress import (
    ProgressReporter,
)

_pinned_condition_asset_id = content_services._pinned_condition_asset_id
_children = content_context._children
_problem_identity = content_context._problem_identity
_condition_asset_id = content_context._condition_asset_id
_context_fingerprint = content_context._context_fingerprint
_solution_assets = content_context._solution_assets
_generated_diagram_assets = content_diagrams._generated_diagram_assets
_preserving_solution_transformations = (
    content_context._preserving_solution_transformations
)


def _current_condition_asset_content_type(
    gateway: RightTriangleGateway,
    context: dict[str, Any],
    content_rule_key: str | None,
) -> str | None:
    return content_assets._current_condition_asset_content_type(
        gateway=gateway,
        context=context,
        content_rule_key=content_rule_key,
        registered_handler=_registered_handler,
    )


def _planner_constraints(content_rule_key: str | None) -> dict[str, str]:
    return dict(_registered_handler(content_rule_key).constraints)


def _requires_parent_condition_asset(content_rule_key: str | None) -> bool:
    return _registered_handler(content_rule_key).requires_parent_condition_asset


def _registered_handler(content_rule_key: str | None):
    from solution_runner.pipelines.core.handler_registry import get_handler

    try:
        return get_handler(content_rule_key or "right-triangle-sine")
    except KeyError as exc:
        raise RightTrianglePlanError(str(exc)) from exc


def _build_content_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str | None,
    content_rule_key: str | None,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
    condition_asset_bytes: bytes | None = None,
    generated_solution_assets: tuple[dict[str, str], ...] = (),
):
    from solution_runner.pipelines.core.handlers import PlanInput

    return _registered_handler(content_rule_key).plan(
        PlanInput(
            context=context,
            parent_asset_id=parent_asset_id,
            parent_solution_assets=parent_solution_assets,
            parent_solution_html=parent_solution_html,
            current_asset_content_type=current_asset_content_type,
            condition_asset_bytes=condition_asset_bytes,
            generated_solution_assets=generated_solution_assets,
        )
    )


def _condition_asset_bytes(
    gateway: RightTriangleGateway,
    problem_id: str,
    source_problem_id: str,
    content_rule_key: str | None,
) -> bytes | None:
    return content_assets._condition_asset_bytes(
        gateway=gateway,
        problem_id=problem_id,
        source_problem_id=source_problem_id,
        content_rule_key=content_rule_key,
        registered_handler=_registered_handler,
    )


def _with_required_assets(
    context: dict[str, Any], content_rule_key: str | None
) -> dict[str, Any]:
    return content_assets._with_required_assets(
        context=context,
        content_rule_key=content_rule_key,
        registered_handler=_registered_handler,
    )


def _ensure_required_assets(
    gateway: RightTriangleGateway,
    problem_id: str,
    context: dict[str, Any],
    content_rule_key: str | None,
) -> dict[str, Any]:
    return content_assets._ensure_required_assets(
        gateway=gateway,
        problem_id=problem_id,
        context=context,
        content_rule_key=content_rule_key,
        registered_handler=_registered_handler,
    )


def _prepared_record(
    gateway: RightTriangleGateway,
    child: dict[str, Any],
    parent_asset_id: str | None,
    content_rule_key: str | None = None,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
    parent_solution_html: str = "",
    preserve_existing_solution: bool = False,
) -> dict[str, Any]:
    return content_prepare_record._prepared_record(
        gateway=gateway,
        child=child,
        parent_asset_id=parent_asset_id,
        content_rule_key=content_rule_key,
        parent_solution_assets=parent_solution_assets,
        parent_solution_html=parent_solution_html,
        preserve_existing_solution=preserve_existing_solution,
        services=SimpleNamespace(
            _registered_handler=_registered_handler,
            _with_required_assets=_with_required_assets,
            _current_condition_asset_content_type=_current_condition_asset_content_type,
            _condition_asset_bytes=_condition_asset_bytes,
            _build_content_plan=_build_content_plan,
        ),
    )


def prepare_manifest(
    gateway: RightTriangleGateway,
    *,
    catalog_snapshot_id: str,
    source_group_number: str,
    max_workers: int,
) -> dict[str, Any]:
    return content_manifest.prepare_manifest(
        gateway=gateway,
        catalog_snapshot_id=catalog_snapshot_id,
        source_group_number=source_group_number,
        max_workers=max_workers,
        record_factory=_prepared_record,
    )


_has_current_image = content_write._has_current_image


_ParentContent = content_apply_record._ParentContent


def _verify_content_readback(
    gateway: RightTriangleGateway,
    record: dict[str, Any],
    context: dict[str, Any],
    frozen: list[dict[str, Any]],
    parent: _ParentContent,
) -> None:
    return content_verify._verify_content_readback(
        gateway,
        record,
        context,
        frozen,
        parent,
        services=SimpleNamespace(
            registered_handler=_registered_handler,
            condition_asset_bytes=_condition_asset_bytes,
            build_content_plan=_build_content_plan,
        ),
    )


_PreparedApply = content_apply_prepare._PreparedApply


def _prepare_frozen_apply(
    gateway: RightTriangleGateway, record: dict[str, Any], parent: _ParentContent
) -> _PreparedApply:
    return content_apply_prepare._prepare_frozen_apply(
        gateway,
        record,
        parent,
        services=SimpleNamespace(
            _ensure_required_assets=_ensure_required_assets,
            _registered_handler=_registered_handler,
            _current_condition_asset_content_type=_current_condition_asset_content_type,
            _condition_asset_bytes=_condition_asset_bytes,
            _build_content_plan=_build_content_plan,
        ),
    )


def _write_frozen_apply(
    gateway: RightTriangleGateway,
    record: dict[str, Any],
    parent: _ParentContent,
    prepared: _PreparedApply,
) -> tuple[bool, list[dict[str, Any]]]:
    return content_write._write_frozen_apply(
        gateway, record, parent, prepared, registered_handler=_registered_handler
    )


def _apply_record(
    gateway: RightTriangleGateway,
    record: dict[str, Any],
    parent_asset_id: str | None,
    content_rule_key: str | None,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
    parent_solution_html: str = "",
) -> dict[str, Any]:
    return content_apply_record._apply_record(
        gateway=gateway,
        record=record,
        parent_asset_id=parent_asset_id,
        content_rule_key=content_rule_key,
        parent_solution_assets=parent_solution_assets,
        parent_solution_html=parent_solution_html,
        services=SimpleNamespace(
            _prepare_frozen_apply=_prepare_frozen_apply,
            _write_frozen_apply=_write_frozen_apply,
            _registered_handler=_registered_handler,
            _verify_content_readback=_verify_content_readback,
        ),
    )


def apply_frozen_manifest(
    gateway: RightTriangleGateway,
    manifest: dict[str, Any],
    *,
    batch_size: int,
    max_workers: int,
    checkpoint_path: Path,
    batch_pause_seconds: float = 0.0,
    on_batch_complete: Callable[[list[dict[str, Any]], int], None] | None = None,
) -> dict[str, Any]:
    return content_apply_batch.apply_frozen_manifest(
        gateway=gateway,
        manifest=manifest,
        batch_size=batch_size,
        max_workers=max_workers,
        checkpoint_path=checkpoint_path,
        batch_pause_seconds=batch_pause_seconds,
        on_batch_complete=on_batch_complete,
        services=SimpleNamespace(
            _planner_constraints=_planner_constraints,
            _requires_parent_condition_asset=_requires_parent_condition_asset,
            _registered_handler=_registered_handler,
            _apply_record=_apply_record,
        ),
    )


def _content_rule_manifest(
    gateway: RightTriangleGateway,
    targets: tuple[ProblemTarget, ...],
    *,
    profile: GroupProfile,
    parent_asset_id: str | None,
    parent_solution_assets: tuple[dict[str, str], ...],
    parent_solution_html: str = "",
    max_workers: int,
    on_record_prepared: Callable[[dict[str, Any], int], None] | None = None,
) -> dict[str, Any]:
    return content_manifest._content_rule_manifest(
        gateway=gateway,
        targets=targets,
        profile=profile,
        parent_asset_id=parent_asset_id,
        parent_solution_assets=parent_solution_assets,
        parent_solution_html=parent_solution_html,
        max_workers=max_workers,
        on_record_prepared=on_record_prepared,
        record_factory=_prepared_record,
    )


def _read_content_rule_manifest(
    path: Path,
    targets: tuple[ProblemTarget, ...],
    profile: GroupProfile,
) -> dict[str, Any]:
    return content_manifest._read_content_rule_manifest(
        path=path,
        targets=targets,
        profile=profile,
        requires_parent=_requires_parent_condition_asset,
    )


def run_content_rule_stage(
    gateway: RightTriangleGateway,
    targets: tuple[ProblemTarget, ...],
    asset_source_target: ProblemTarget,
    profile: GroupProfile,
    reporter: ProgressReporter,
    *,
    run_dir: Path,
    resume: bool,
    apply: bool,
    batch_size: int,
    batch_pause_seconds: float,
    max_workers: int,
) -> tuple[ProblemStageResult, ...]:
    return content_stage.run_content_rule_stage(
        gateway=gateway,
        targets=targets,
        asset_source_target=asset_source_target,
        profile=profile,
        reporter=reporter,
        run_dir=run_dir,
        resume=resume,
        apply=apply,
        batch_size=batch_size,
        batch_pause_seconds=batch_pause_seconds,
        max_workers=max_workers,
        services=SimpleNamespace(
            _registered_handler=_registered_handler,
            _read_content_rule_manifest=_read_content_rule_manifest,
            _requires_parent_condition_asset=_requires_parent_condition_asset,
            _content_rule_manifest=_content_rule_manifest,
            apply_frozen_manifest=apply_frozen_manifest,
        ),
    )


def run_manifest(
    gateway: RightTriangleGateway,
    manifest: dict[str, Any],
    *,
    apply: bool,
) -> dict[str, Any]:
    return content_legacy_run.run_manifest(
        gateway,
        manifest,
        apply=apply,
        services=SimpleNamespace(
            _registered_handler=_registered_handler,
            _planner_constraints=_planner_constraints,
            _requires_parent_condition_asset=_requires_parent_condition_asset,
            _build_content_plan=_build_content_plan,
        ),
    )
