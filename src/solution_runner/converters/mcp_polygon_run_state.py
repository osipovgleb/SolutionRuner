"""Prepare polygon-run inventory and persist its completion summary."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InventoryContext:
    run_dir: Path
    source_site_id: str
    scope: Any
    converter_fingerprint: str
    template_fingerprint: str
    logger: Any


def prepare_inventory(args, client, context, handlers):
    resume, build = handlers
    run_dir, source_site_id, scope = (
        context.run_dir,
        context.source_site_id,
        context.scope,
    )
    converter_fingerprint, template_fingerprint, logger = (
        context.converter_fingerprint,
        context.template_fingerprint,
        context.logger,
    )
    if args.resume_from_run is not None:
        inventory_by_group, totals = resume(
            source_run_dir=args.resume_from_run,
            run_dir=run_dir,
            catalog_snapshot_id=args.catalog_snapshot_id,
            source_site_id=source_site_id,
            category_key=args.category_key,
            theme_titles=args.theme_titles,
            scope=scope,
            converter_fingerprint=converter_fingerprint,
            template_fingerprint=template_fingerprint,
            preserve_applied=args.resume_preserve_applied,
            logger=logger,
        )
    else:
        inventory_by_group, totals = build(
            client,
            catalog_snapshot_id=args.catalog_snapshot_id,
            source_site_id=source_site_id,
            category_key=args.category_key,
            category_title=args.category_title,
            theme_titles=args.theme_titles,
            mode=args.mode,
            converter_fingerprint=converter_fingerprint,
            template_fingerprint=template_fingerprint,
            scope=scope,
            run_dir=run_dir,
            logger=logger,
        )
    return inventory_by_group, totals


def finish_run(args, logger, identity, progress, write_json):
    run_dir, user_id, source_site_id, converter_fingerprint, template_fingerprint = (
        identity
    )
    global_tasks_seen, batches_seen, determinism_verified, stop_requested, totals = (
        progress
    )
    status = "completed"
    if stop_requested:
        status = "limited_complete"
    if totals.get("assets_rejected") or totals.get("assets_stale"):
        status += "_with_skips"
    if totals.get("asset_errors"):
        status += "_with_errors"
    summary = {
        "at": datetime.now(UTC).isoformat(),
        "status": status,
        "mode": args.mode,
        "run_dir": str(run_dir),
        "user_id": user_id,
        "catalog_snapshot_id": args.catalog_snapshot_id,
        "source_site_id": source_site_id,
        "converter_sha256": converter_fingerprint,
        "template_sha256": template_fingerprint,
        "determinism_verified": determinism_verified,
        "batches_seen": batches_seen,
        "tasks_seen": global_tasks_seen,
        "totals": dict(sorted(totals.items())),
    }
    write_json(run_dir / "summary.json", summary)
    logger.emit("run_complete", status=status, **summary["totals"])
    return 0 if not totals.get("asset_errors") else 2


def emit_start(args, logger, run_dir, fingerprints):
    converter_fingerprint, template_fingerprint = fingerprints
    logger.emit(
        "run_start",
        status=args.mode,
        run_dir=str(run_dir),
        catalog_snapshot_id=args.catalog_snapshot_id,
        category_key=args.category_key,
        theme_titles=list(args.theme_titles),
        batch_size=args.batch_size,
        batch_pause_seconds=args.batch_pause_seconds,
        max_workers=args.max_workers,
        converter_sha256=converter_fingerprint,
        template_sha256=template_fingerprint,
        resume_from_run=(
            str(args.resume_from_run.resolve()) if args.resume_from_run else None
        ),
    )
