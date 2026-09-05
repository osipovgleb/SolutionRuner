"""Repair only generated rectangle-method assets from frozen prepared manifests."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Protocol

from .group_profiles import get_group_profile
from .manifest import FrozenRunScope, read_prepared_manifest
from .mcp_runtime import DEFAULT_MCP_URL, JsonRpcMcpGateway
from .models import (
    GroupProfile,
    PreparedFigure,
    PreparedGridPolygon,
    ProblemStageResult,
    SolutionDiagramSpec,
)
from .strategies import get_solution_strategy
from .strategies.protocol import SolutionStrategy


_VAR_ROOT = Path(os.environ.get("SOLUTION_RUNNER_VAR_DIR", "var"))
DEFAULT_RUN_ROOT = _VAR_ROOT / "grid-polygon" / "runs"
DEFAULT_REPAIR_ROOT = _VAR_ROOT / "grid-polygon" / "rectangle-asset-repairs"
RECTANGLE_ASSET_KEYS = ("generated_rectangle_diagram", "generated_solution_diagram")


class RectangleRepairGateway(Protocol):
    """Expose only MCP operations required by an asset-only rectangle repair."""

    def get_problem_asset_target_context(
        self,
        problem_id: str,
        transformation_target_id: str,
    ) -> dict[str, Any]:
        """Return current identity for one exact asset target."""

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Return current asset metadata including its digest."""

    def upload_solution_asset(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Upload one verified replacement SVG."""

    def replace_problem_asset_target(
        self,
        *,
        problem_id: str,
        transformation_target_id: str,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Replace one exact problem asset target with readback."""


def _rectangle_diagram(
    strategy: SolutionStrategy,
    prepared: PreparedGridPolygon,
    profile: GroupProfile,
) -> SolutionDiagramSpec:
    """Return the sole rectangle-method diagram selected by its stable asset key."""

    analysis = strategy.analyze(prepared, profile)
    renderer = getattr(strategy, "render_solution_diagrams", None)
    if callable(renderer):
        diagrams = tuple(renderer(prepared, analysis, profile))
    else:
        diagrams = (
            SolutionDiagramSpec(
                asset_key="generated_solution_diagram",
                solution_variant_index=0,
                svg_bytes=strategy.render_solution_svg(prepared, analysis),
                alt_text=str(list(prepared.coordinates)),
            ),
        )
    matches = [diagram for diagram in diagrams if diagram.asset_key in RECTANGLE_ASSET_KEYS]
    preferred = [
        diagram for diagram in matches if diagram.asset_key == "generated_rectangle_diagram"
    ]
    selected = preferred or matches
    if len(selected) != 1:
        raise ValueError("strategy does not expose one rectangle-method diagram")
    return selected[0]


def repair_rectangle_solution_asset(
    gateway: RectangleRepairGateway,
    prepared: PreparedGridPolygon,
    profile: GroupProfile,
    strategy: SolutionStrategy,
    *,
    apply: bool,
) -> ProblemStageResult:
    """Replace only one existing rectangle-method asset when its digest is stale."""

    diagram = _rectangle_diagram(strategy, prepared, profile)
    target_id = f"asset:{diagram.asset_key}"
    context = gateway.get_problem_asset_target_context(prepared.problem_id, target_id)
    current_asset_id = str(context.get("current_asset_id") or "")
    if not current_asset_id:
        raise ValueError("rectangle solution asset target is missing")
    expected_sha256 = hashlib.sha256(diagram.svg_bytes).hexdigest()
    metadata = gateway.get_asset_metadata(current_asset_id)
    if str(metadata.get("sha256") or "").lower() == expected_sha256:
        return ProblemStageResult(
            problem_id=prepared.problem_id,
            source_problem_id=prepared.source_problem_id,
            stage="rectangle_solution_asset",
            status="already_complete",
            message=f"{diagram.asset_key}; digest_verified",
        )
    if not apply:
        return ProblemStageResult(
            problem_id=prepared.problem_id,
            source_problem_id=prepared.source_problem_id,
            stage="rectangle_solution_asset",
            status="planned",
            message=f"{diagram.asset_key}; replacement_required",
        )
    uploaded = gateway.upload_solution_asset(
        source_problem_id=prepared.source_problem_id,
        svg_bytes=diagram.svg_bytes,
        sha256=expected_sha256,
    )
    replacement_asset_id = str(uploaded.get("source_asset_id") or "")
    if not replacement_asset_id:
        raise ValueError("rectangle solution upload returned no asset identity")
    gateway.replace_problem_asset_target(
        problem_id=prepared.problem_id,
        transformation_target_id=target_id,
        replacement_asset_id=replacement_asset_id,
        alt_text=diagram.alt_text,
    )
    return ProblemStageResult(
        problem_id=prepared.problem_id,
        source_problem_id=prepared.source_problem_id,
        stage="rectangle_solution_asset",
        status="applied",
        message=f"{diagram.asset_key}; replacement_verified",
    )


def _manifest_records(path: Path, profile: GroupProfile) -> tuple[PreparedFigure, ...]:
    """Read one frozen manifest after reconstructing and validating its exact scope."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_scope = payload.get("scope") if isinstance(payload, dict) else None
    if not isinstance(raw_scope, dict):
        raise ValueError(f"manifest scope is missing: {path}")
    scope = FrozenRunScope(
        catalog_snapshot_id=str(raw_scope.get("catalog_snapshot_id") or ""),
        snapshot_theme_id=str(raw_scope.get("snapshot_theme_id") or ""),
        source_group_id=str(raw_scope.get("source_group_id") or ""),
        group_key=str(raw_scope.get("group_key") or ""),
        target_problem_ids=tuple(str(value) for value in raw_scope.get("target_problem_ids", [])),
    )
    if (
        scope.catalog_snapshot_id != profile.catalog_snapshot_id
        or scope.snapshot_theme_id != profile.snapshot_theme_id
        or scope.source_group_id != profile.source_group_id
        or scope.group_key != profile.group_key
    ):
        raise ValueError(f"manifest does not belong to group {profile.group_key}: {path}")
    return read_prepared_manifest(path, expected_scope=scope)


def _discover_group_records(
    run_root: Path,
    profile: GroupProfile,
) -> tuple[PreparedGridPolygon, ...]:
    """Merge every saved successful record for one group with latest-run precedence."""

    manifests = sorted(run_root.glob(f"*-group-{profile.group_key}/prepared-manifest.json"))
    if not manifests:
        raise ValueError(f"no prepared manifests found for group {profile.group_key}")
    records: dict[str, PreparedGridPolygon] = {}
    for manifest in manifests:
        for record in _manifest_records(manifest, profile):
            if not isinstance(record, PreparedGridPolygon):
                raise ValueError("rectangle repair requires polygon records")
            previous = records.get(record.problem_id)
            if previous is not None and previous.source_problem_id != record.source_problem_id:
                raise ValueError("prepared record identity drifted between runs")
            records[record.problem_id] = record
    return tuple(
        sorted(
            records.values(),
            key=lambda record: (
                0,
                int(record.source_problem_id),
            )
            if record.source_problem_id.isdigit()
            else (1, record.source_problem_id),
        )
    )


def _api_key() -> str:
    """Return the MCP key without printing or persisting it."""

    value = os.environ.get("TEACHERHELPER_MCP_API_KEY", "").strip()
    return value or getpass.getpass("TEACHERHELPER_MCP_API_KEY: ").strip()


def _parser() -> argparse.ArgumentParser:
    """Build the explicit multi-group asset-repair command contract."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", action="append", required=True)
    parser.add_argument("--confirm-catalog", required=True)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Repair selected groups and persist one isolated result for every saved task."""

    parser = _parser()
    args = parser.parse_args(argv)
    if not 1 <= args.max_workers <= 10:
        parser.error("--max-workers must be between 1 and 10")
    groups = tuple(dict.fromkeys(args.group))
    profiles = tuple(get_group_profile(group) for group in groups)
    if any(profile.catalog_snapshot_id != args.confirm_catalog for profile in profiles):
        parser.error("--confirm-catalog does not match every selected group")
    if any(profile.strategy_key != "bounding-rectangle-quadrilateral" for profile in profiles):
        parser.error("every selected group must use bounding-rectangle-quadrilateral")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (
        args.output_dir
        or DEFAULT_REPAIR_ROOT / f"{timestamp}-groups-{'-'.join(groups)}"
    ).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    gateway = JsonRpcMcpGateway(
        url=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
        api_key=_api_key(),
    )
    jobs: list[tuple[PreparedGridPolygon, GroupProfile, SolutionStrategy]] = []
    for profile in profiles:
        strategy = get_solution_strategy(profile.strategy_key)
        jobs.extend(
            (record, profile, strategy)
            for record in _discover_group_records(args.run_root, profile)
        )

    def run_job(
        job: tuple[PreparedGridPolygon, GroupProfile, SolutionStrategy],
    ) -> ProblemStageResult:
        """Convert one task exception into a durable isolated failure."""

        record, profile, strategy = job
        try:
            return repair_rectangle_solution_asset(
                gateway,
                record,
                profile,
                strategy,
                apply=args.apply,
            )
        except Exception as exc:  # noqa: BLE001 - target isolation is intentional.
            return ProblemStageResult(
                problem_id=record.problem_id,
                source_problem_id=record.source_problem_id,
                stage="rectangle_solution_asset",
                status="failed",
                message=" ".join(str(exc).split())[:2000],
            )

    try:
        if args.max_workers == 1:
            results = tuple(map(run_job, jobs))
        else:
            with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                results = tuple(executor.map(run_job, jobs))
    finally:
        gateway.close()
    (output_dir / "results.json").write_text(
        json.dumps(
            [asdict(result) for result in results],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "apply": bool(args.apply),
                "groups": list(groups),
                "status_counts": counts,
                "targets": len(results),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"RESULTS {output_dir}")
    print(" ".join(f"{key.upper()} {value}" for key, value in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
