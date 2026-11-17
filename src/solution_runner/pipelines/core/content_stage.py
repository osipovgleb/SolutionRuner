"""Run a registered content rule through its frozen manifest workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from solution_runner.pipelines.grid_polygon.progress import (
    ProgressReporter,
    TargetProgress,
)

from .content_context import (
    _children,
    _condition_asset_id,
    _problem_identity,
    _solution_assets,
    _solution_html,
)
from .content_gateway import RightTriangleGateway
from .content_reporting import _report_content_result, _write_checkpoint
from .content_services import _pinned_condition_asset_id
from .errors import ContentPlanError as RightTrianglePlanError
from .models import GroupProfile, ProblemStageResult, ProblemTarget


@dataclass(frozen=True)
class _ApplyOptions:
    batch_size: int
    max_workers: int
    checkpoint_path: Path
    batch_pause_seconds: float


def _apply_manifest(services, gateway, manifest, reporter, profile, options):
    records = manifest["records"]
    reported_results: list[ProblemStageResult] = []

    def report_batch(batch: list[dict[str, Any]], completed: int) -> None:
        start = completed - len(batch) + 1
        total = len(records)
        for index, result in enumerate(batch, start=start):
            reported_results.append(
                _report_content_result(
                    reporter,
                    profile,
                    result,
                    TargetProgress(index=index, total=total),
                )
            )

    summary = services.apply_frozen_manifest(
        gateway,
        manifest,
        batch_size=options.batch_size,
        max_workers=options.max_workers,
        checkpoint_path=options.checkpoint_path,
        batch_pause_seconds=options.batch_pause_seconds,
        on_batch_complete=report_batch,
    )
    del summary
    return tuple(reported_results)


def _parent_inputs(
    gateway, profile, handler, asset_source_target, pinned_asset_id, services
):
    parent_target = asset_source_target
    if handler.parent_from_group_listing:
        children = _children(
            gateway.get_source_catalog_children(profile.source_group_id, "group")
        )
        if children:
            parent_target = ProblemTarget(
                problem_id=_problem_identity(children[0])[0],
                source_problem_id=_problem_identity(children[0])[1],
                source_group_id=profile.source_group_id,
                group_key=profile.group_key,
                problem_order_index=0,
            )
    source_context = gateway.get_problem_context(parent_target.problem_id)
    parent_asset_id = pinned_asset_id
    if parent_asset_id is None and services._requires_parent_condition_asset(
        profile.content_rule_key
    ):
        parent_asset_id = _condition_asset_id(source_context)
    parent_solution_assets = _solution_assets(source_context)
    parent_solution_html = _solution_html(source_context)

    return parent_asset_id, parent_solution_assets, parent_solution_html


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
    services: Any,
) -> tuple[ProblemStageResult, ...]:
    """Run the registered content rule through the shared frozen workflow."""

    if not profile.content_rule_key:
        raise RightTrianglePlanError("content-rule profile requires a rule key")
    if not targets:
        return ()
    handler = services._registered_handler(profile.content_rule_key)
    if (
        handler.expected_parent_id
        and asset_source_target.problem_id != handler.expected_parent_id
    ):
        raise RightTrianglePlanError("registered handler requires its audited parent")
    manifest_path = run_dir / "prepared-manifest.json"
    pinned_asset_id = _pinned_condition_asset_id(gateway, profile)
    if resume:
        manifest = services._read_content_rule_manifest(manifest_path, targets, profile)
    else:
        parent_asset_id, parent_solution_assets, parent_solution_html = _parent_inputs(
            gateway, profile, handler, asset_source_target, pinned_asset_id, services
        )

        def report_preparation(record: dict[str, Any], index: int) -> None:
            prepared = record.get("status") == "prepared"
            reporter.task(
                profile.theme_title,
                profile.group_key,
                str(record.get("source_problem_id") or ""),
                TargetProgress(index=index, total=len(targets)),
                "SOLUTION PREPARED" if prepared else "SOLUTION BLOCKED",
                severity="info" if prepared else "error",
                stage="solution_prepare",
                details={"message": str(record.get("message") or "")}
                if not prepared
                else None,
            )

        manifest = services._content_rule_manifest(
            gateway,
            targets,
            profile=profile,
            parent_asset_id=parent_asset_id,
            parent_solution_assets=parent_solution_assets,
            parent_solution_html=parent_solution_html,
            max_workers=max_workers,
            on_record_prepared=report_preparation,
        )
        _write_checkpoint(manifest_path, manifest)
    records = manifest["records"]
    if apply:
        return _apply_manifest(
            services,
            gateway,
            manifest,
            reporter,
            profile,
            _ApplyOptions(
                batch_size,
                max_workers,
                run_dir / "apply-results.json",
                batch_pause_seconds,
            ),
        )
    else:
        raw_results = [
            {
                "problem_id": record.get("problem_id"),
                "source_problem_id": record.get("source_problem_id"),
                "status": (
                    "planned" if record.get("status") == "prepared" else "failed"
                ),
                "message": record.get("message"),
            }
            for record in records
        ]
    total = len(raw_results)
    return tuple(
        _report_content_result(
            reporter,
            profile,
            result,
            TargetProgress(index=index, total=total),
        )
        for index, result in enumerate(raw_results, start=1)
    )
