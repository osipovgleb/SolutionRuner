"""Data and errors for polygon asset conversion workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class PipelineError(RuntimeError):
    """Base class for deterministic pipeline failures."""


class McpCallError(PipelineError):
    """Report one failed MCP JSON-RPC call without exposing credentials."""


class CandidateRejected(PipelineError):
    """Mark an input that deterministically fails conversion or validation."""


class CandidateStale(PipelineError):
    """Mark a candidate whose current MCP state no longer matches inventory."""


@dataclass(frozen=True)
class ThemeScope:
    """Hold one exact theme from the fixed production scope."""

    title: str
    snapshot_theme_id: str
    source_theme_id: str
    order_index: int
    source_groups_count: int
    expected_vertices: int


@dataclass(frozen=True)
class GroupScope:
    """Hold one exact ordered source group from the fixed production scope."""

    source_group_id: str
    group_key: str
    order_index: int


@dataclass(frozen=True)
class AssetCandidate:
    """Identify one current ordinary PNG in an eligible concrete problem."""

    theme_title: str
    snapshot_theme_id: str
    theme_order_index: int
    source_group_id: str
    group_key: str
    group_order_index: int
    problem_id: str
    source_problem_id: str
    problem_order_index: int
    asset_key: str
    sections: tuple[str, ...]
    expected_vertices: int

    @property
    def stable_key(self) -> str:
        """Return the problem-target identity used in logs and manifests."""

        return f"{self.problem_id}:{self.asset_key}"


@dataclass
class GroupInventory:
    """Record compact counts and the exact PNG candidates for one group."""

    theme_title: str
    snapshot_theme_id: str
    source_group_id: str
    group_key: str
    group_order_index: int
    counts: dict[str, int]
    non_svg_content_types: dict[str, int]
    png_problem_ids: list[str]
    png_source_problem_ids: list[str]
    candidates: list[AssetCandidate] = field(repr=False)

    def manifest_payload(self) -> dict[str, Any]:
        """Return a JSON-safe inventory payload with stable candidate identities."""

        payload = asdict(self)
        payload["candidates"] = [asdict(candidate) for candidate in self.candidates]
        return payload


@dataclass(frozen=True)
class RefreshedAsset:
    """Hold the exact current PNG state read immediately before work."""

    transformation_target_id: str
    asset: dict[str, Any]
    replacement_context: dict[str, Any]


@dataclass(frozen=True)
class PreparedAsset:
    """Hold one validated local SVG pending an optional MCP upload."""

    candidate: AssetCandidate
    transformation_target_id: str
    input_sha256: str
    input_size_bytes: int
    output_sha256: str
    output_size_bytes: int
    canonical_asset_key: str
    alt_text: str
    input_path: Path
    svg_path: Path
    diagnostic_path: Path
    validation: dict[str, Any]


@dataclass(frozen=True)
class RollbackCandidate:
    """Identify one exact applied SourceAsset transformation to remove safely."""

    candidate: AssetCandidate
    transformation_target_id: str
    source_asset_id: str
    output_sha256: str


@dataclass(frozen=True)
class _CandidateOutcome:
    """Carry one isolated asset result back to deterministic accounting."""

    candidate: AssetCandidate
    status: str
    stage: str
    prepared: PreparedAsset | None = None
    source_asset_id: str | None = None
    cleanup: dict[str, Any] | None = None
    error: str | None = None
