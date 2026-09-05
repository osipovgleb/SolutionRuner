"""Render reusable base-height triangle solutions and red constructions."""

from __future__ import annotations

from ..geometry.triangle import analyze_axis_aligned_triangle
from ..models import GeometryAnalysis, GroupProfile, PreparedGridPolygon
from .protocol import (
    append_solution_construction,
    build_answer_html,
    centered_formula_html,
    format_number,
    svg_coordinate_mapper,
    svg_number,
)


class BaseHeightTriangleStrategy:
    """Handle horizontal or vertical bases with the same implementation."""

    key = "base-height-triangle"
    requires_solution_diagram = True

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Calculate base-height area and verify it by coordinates."""

        if profile.strategy_key != self.key or prepared.vertex_count != 3:
            raise ValueError("base-height strategy/profile mismatch")
        result = analyze_axis_aligned_triangle(prepared.coordinates)
        orientation = "horizontal" if result.base_start[1] == result.base_end[1] else "vertical"
        return GeometryAnalysis(
            area=result.area,
            area_by_coordinates=result.area_by_coordinates,
            details={
                "points": prepared.coordinates,
                "base_start": result.base_start,
                "base_end": result.base_end,
                "apex": result.apex,
                "altitude_foot": result.altitude_foot,
                "base_length": result.base_length,
                "height": result.height,
                "orientation": orientation,
            },
        )

    def render_solution_svg(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Overlay the base, height, extension, and perpendicular marker."""

        source = prepared.condition_svg_path.read_bytes()
        points = tuple(analysis.details["points"])
        mapper, cell_size = svg_coordinate_mapper(source, points)
        logical_base_start = analysis.details["base_start"]
        logical_base_end = analysis.details["base_end"]
        logical_apex = analysis.details["apex"]
        logical_foot = analysis.details["altitude_foot"]
        base_start = mapper(logical_base_start)
        base_end = mapper(logical_base_end)
        apex = mapper(logical_apex)
        foot = mapper(logical_foot)
        lines = [
            f'  <line data-kind="base" x1="{svg_number(base_start[0])}" '
            f'y1="{svg_number(base_start[1])}" x2="{svg_number(base_end[0])}" '
            f'y2="{svg_number(base_end[1])}" />',
            f'  <line data-kind="height" x1="{svg_number(apex[0])}" '
            f'y1="{svg_number(apex[1])}" x2="{svg_number(foot[0])}" '
            f'y2="{svg_number(foot[1])}" />',
        ]
        horizontal = analysis.details["orientation"] == "horizontal"
        if horizontal:
            before = logical_foot[0] < logical_base_start[0]
            after = logical_foot[0] > logical_base_end[0]
        else:
            before = logical_foot[1] < logical_base_start[1]
            after = logical_foot[1] > logical_base_end[1]
        if before or after:
            endpoint = base_start if before else base_end
            lines.append(
                f'  <line data-kind="base-extension" x1="{svg_number(endpoint[0])}" '
                f'y1="{svg_number(endpoint[1])}" x2="{svg_number(foot[0])}" '
                f'y2="{svg_number(foot[1])}" stroke-dasharray="5 4" />'
            )
        marker = cell_size * 0.28
        if horizontal:
            apex_direction = -1 if apex[1] < foot[1] else 1
            base_direction = 1 if logical_base_end[0] - logical_foot[0] >= logical_foot[0] - logical_base_start[0] else -1
            marker_x = foot[0] + base_direction * marker
            marker_y = foot[1] + apex_direction * marker
            marker_path = (
                f"M {svg_number(marker_x)} {svg_number(foot[1])} "
                f"L {svg_number(marker_x)} {svg_number(marker_y)} "
                f"L {svg_number(foot[0])} {svg_number(marker_y)}"
            )
        else:
            apex_direction = -1 if apex[0] < foot[0] else 1
            farther = max((base_start, base_end), key=lambda point: abs(point[1] - foot[1]))
            base_direction = -1 if farther[1] < foot[1] else 1
            marker_x = foot[0] + apex_direction * marker
            marker_y = foot[1] + base_direction * marker
            marker_path = (
                f"M {svg_number(foot[0])} {svg_number(marker_y)} "
                f"L {svg_number(marker_x)} {svg_number(marker_y)} "
                f"L {svg_number(marker_x)} {svg_number(foot[1])}"
            )
        lines.append(f'  <path data-kind="right-angle-marker" d="{marker_path}" />')
        return append_solution_construction(source, lines)

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the profile-selected general formula and measured values."""

        symbols = profile.formula_symbols or "ah"
        return (
            rf"S=\frac{{1}}{{2}}{symbols}="
            rf"\frac{{1}}{{2}}\cdot {analysis.details['base_length']}\cdot "
            rf"{analysis.details['height']}={format_number(analysis.area, latex=True)}"
        )

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return profile wording over the same base-height computation."""

        clause = profile.height_clause or "проведённую к этому основанию"
        return centered_formula_html(
            "Площадь треугольника равна половине произведения основания на "
            f"высоту, {clause}. Поэтому",
            self.build_formula(analysis, profile),
        )

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the exact numeric answer."""

        return build_answer_html(analysis)

