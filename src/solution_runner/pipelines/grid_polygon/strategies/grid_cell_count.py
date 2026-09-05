"""Solve grid-aligned cell figures by exact unit-cell enumeration."""

from __future__ import annotations

from fractions import Fraction

from ..models import GeometryAnalysis, GroupProfile, PreparedGridPolygon
from .protocol import build_answer_html, format_number


def _coordinate_area(points: tuple[tuple[int, int], ...]) -> Fraction:
    """Return the exact shoelace area for one ordered polygon."""

    doubled = sum(
        start[0] * end[1] - start[1] * end[0]
        for start, end in zip(points, points[1:] + points[:1], strict=True)
    )
    return Fraction(abs(doubled), 2)


def _contains_cell_center(
    points: tuple[tuple[int, int], ...],
    x: int,
    y: int,
) -> bool:
    """Return whether the center of one integer unit cell lies inside the polygon."""

    probe_x = Fraction(2 * x + 1, 2)
    probe_y = Fraction(2 * y + 1, 2)
    crossings = 0
    for start, end in zip(points, points[1:] + points[:1], strict=True):
        if start[1] == end[1]:
            continue
        low_y, high_y = sorted((start[1], end[1]))
        if not (low_y < probe_y < high_y):
            continue
        crossings += int(Fraction(start[0]) > probe_x)
    return crossings % 2 == 1


def _count_unit_cells(points: tuple[tuple[int, int], ...]) -> int:
    """Enumerate unit-cell centers within one integer grid-aligned polygon."""

    xmin = min(x for x, _ in points)
    xmax = max(x for x, _ in points)
    ymin = min(y for _, y in points)
    ymax = max(y for _, y in points)
    return sum(
        _contains_cell_center(points, x, y)
        for x in range(xmin, xmax)
        for y in range(ymin, ymax)
    )


class GridCellCountStrategy:
    """Count whole shaded grid cells and verify the result by coordinates."""

    key = "grid-cell-count"
    requires_solution_diagram = False

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Return a cell count that exactly agrees with shoelace area."""

        if profile.strategy_key != self.key or prepared.vertex_count < 4:
            raise ValueError("grid cell-count strategy/profile mismatch")
        points = prepared.geometry_coordinates
        if any(
            start[0] != end[0] and start[1] != end[1]
            for start, end in zip(points, points[1:] + points[:1], strict=True)
        ):
            raise ValueError("grid cell-count boundary must be axis-aligned")
        area_by_coordinates = _coordinate_area(points)
        cell_count = _count_unit_cells(points)
        if area_by_coordinates != cell_count:
            raise ValueError("grid cell count and coordinate areas disagree")
        return GeometryAnalysis(
            area=Fraction(cell_count),
            area_by_coordinates=area_by_coordinates,
            details={"points": points, "cell_count": cell_count},
        )

    def render_solution_svg(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Return the unchanged condition SVG for protocol completeness."""

        return prepared.condition_svg_path.read_bytes()

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the exact cell-count equality used for internal evidence."""

        return f"S={format_number(analysis.area, latex=True)}"

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return the concise sentence used by the audited group prototype."""

        return (
            "<p>Посчитаем количество клеток внутри закрашенной области: их "
            f"{format_number(analysis.area)}.</p>"
        )

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the verified numeric answer."""

        return build_answer_html(analysis)
