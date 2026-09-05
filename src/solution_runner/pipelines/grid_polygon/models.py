"""Define immutable identities and results shared by polygon pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Literal, Mapping, TypeAlias


StrategyKey: TypeAlias = Literal[
    "right-triangle",
    "base-height-triangle",
    "bounding-rectangle-quadrilateral",
    "bounding-rectangle-triangle",
    "parallel-bases-trapezoid",
    "parallelogram-three-methods",
    "bounding-rectangle-trapezoid",
    "grid-cell-count",
    "annulus-area",
    "annulus-from-known-area",
]
WorkflowKind: TypeAlias = Literal["geometry", "content_rule"]
ContentRuleKey: TypeAlias = Literal[
    "right-triangle-sine",
    "right-triangle-cosine-hypotenuse",
    "right-triangle-tangent-hypotenuse",
    "right-triangle-tangent-opposite-cathetus",
    "right-triangle-universal",
    "right-triangle-altitude-universal",
    "isosceles-triangle-27284-base-from-sine",
    "isosceles-triangle-27285-side-from-base-sine",
    "isosceles-triangle-27286-base-from-cosine",
    "isosceles-triangle-27287-side-from-base-cosine",
    "isosceles-triangle-27288-base-from-tangent",
    "isosceles-triangle-27289-side-from-base-tangent",
    "isosceles-triangle-27320-altitude-from-base-sine",
    "isosceles-triangle-27321-projection-from-base-sine",
    "isosceles-triangle-27322-altitude-from-base-cosine",
    "isosceles-triangle-27323-projection-from-base-cosine",
    "isosceles-triangle-27324-altitude-from-base-tangent",
    "isosceles-triangle-27325-projection-from-base-tangent",
    "isosceles-triangle-27326-altitude-from-side-sine",
    "isosceles-triangle-27327-projection-from-side-sine",
    "isosceles-triangle-27328-altitude-from-side-cosine",
    "isosceles-triangle-27329-projection-from-side-cosine",
    "isosceles-triangle-27330-sine-from-altitude-and-base",
    "isosceles-triangle-27331-cosine-from-altitude-and-base",
    "isosceles-triangle-27345-obtuse-sine-from-side-and-altitude",
    "isosceles-triangle-27346-obtuse-cosine-from-side-and-altitude",
    "isosceles-triangle-27347-obtuse-tangent-from-side-and-altitude",
    "isosceles-triangle-27349-obtuse-cosine-from-side-and-projection",
    "isosceles-triangle-27350-obtuse-tangent-from-side-and-projection",
]
GeometryKind: TypeAlias = Literal["polygon", "ring"]
RingAlignment: TypeAlias = Literal["concentric", "offset"]
KnownCircleArea: TypeAlias = Literal["inner", "outer"]
SolutionScope: TypeAlias = Literal[
    "all",
    "missing_only",
    "missing_or_pipeline_generated",
]
ExistingSolutionPolicy: TypeAlias = Literal["preserve", "rewrite"]
StageResultStatus: TypeAlias = Literal[
    "planned",
    "applied",
    "already_complete",
    "skipped",
    "failed",
]


@dataclass(frozen=True)
class ProblemTarget:
    """Identify one source problem and its condition-asset target."""

    problem_id: str
    source_problem_id: str
    source_group_id: str
    group_key: str
    problem_order_index: int
    asset_key: str = "image_1"


@dataclass(frozen=True)
class GroupProfile:
    """Select immutable source scope and pure solution behavior for one group."""

    catalog_snapshot_id: str
    snapshot_theme_id: str
    source_group_id: str
    group_key: str
    group_order_index: int
    theme_title: str
    theme_order_index: int
    expected_vertices: int | None
    strategy_key: StrategyKey | None
    geometry_kind: GeometryKind = "polygon"
    solution_scope: SolutionScope = "all"
    category_key: str = "9"
    formula_symbols: str | None = None
    height_clause: str | None = None
    solution_text_profile: str | None = None
    existing_solution_policy: ExistingSolutionPolicy = "preserve"
    helpers_ready_branches: tuple[str, ...] = ("p2", "p3", "p4", "p5")
    helpers_not_required_branches: tuple[str, ...] = ("p6",)
    grid_snap_tolerance: float = 0.35
    collinear_distance_tolerance: float = 0.15
    workflow_kind: WorkflowKind = "geometry"
    content_rule_key: ContentRuleKey | None = None


@dataclass(frozen=True)
class PreparedGridPolygon:
    """Freeze the verified condition SVG and geometry for downstream stages."""

    problem_id: str
    source_problem_id: str
    condition_asset_id: str
    condition_svg_path: Path
    condition_svg_sha256: str
    coordinates: tuple[tuple[int, int], ...]
    vertex_count: int
    condition_was_replaced: bool
    converter_diagnostics: Mapping[str, object]
    ordered_coordinates: tuple[tuple[int, int], ...] | None = None

    @property
    def geometry_coordinates(self) -> tuple[tuple[int, int], ...]:
        """Return the verified cyclic edge traversal for geometry work."""

        return self.ordered_coordinates or self.coordinates


@dataclass(frozen=True)
class PreparedGridRing:
    """Freeze a verified annulus SVG and exact lattice-radius evidence."""

    problem_id: str
    source_problem_id: str
    condition_asset_id: str
    condition_svg_path: Path
    condition_svg_sha256: str
    center: tuple[int, int]
    outer_point: tuple[int, int]
    inner_point: tuple[int, int]
    outer_radius_squared: int
    inner_radius_squared: int
    condition_was_replaced: bool
    converter_diagnostics: Mapping[str, object]
    inner_center: tuple[int, int] | None = None
    ring_alignment: RingAlignment = "concentric"
    known_circle_area: KnownCircleArea | None = None
    given_circle_area: Fraction | None = None


PreparedFigure: TypeAlias = PreparedGridPolygon | PreparedGridRing


@dataclass(frozen=True)
class GeometryAnalysis:
    """Hold independently verified area and strategy-specific display values."""

    area: Fraction
    area_by_coordinates: Fraction
    details: Mapping[str, object]


@dataclass(frozen=True)
class SolutionDiagramSpec:
    """Describe one deterministic generated diagram and its solution variant."""

    asset_key: str
    solution_variant_index: int
    svg_bytes: bytes
    alt_text: str


@dataclass(frozen=True)
class ProblemStageResult:
    """Record one target's terminal stage outcome without raw transport data."""

    problem_id: str
    source_problem_id: str
    stage: str
    status: StageResultStatus
    message: str | None = None
    artifact_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class PipelineSummary:
    """Summarize terminal target counts and persistent run artifacts."""

    status: Literal["completed", "completed_with_errors"]
    total: int
    applied: int
    already_complete: int
    skipped: int
    failed: int
    artifact_paths: tuple[Path, ...]
