"""Render reusable right-triangle formulas without a solution diagram."""

from __future__ import annotations

from ..geometry.triangle import analyze_right_triangle
from ..models import GeometryAnalysis, GroupProfile, PreparedGridPolygon
from .protocol import build_answer_html, centered_formula_html, format_number


class RightTriangleStrategy:
    """Apply the catheti formula to every matching triangle profile."""

    key = "right-triangle"
    requires_solution_diagram = False

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Calculate area from catheti and verify it by coordinates."""

        if profile.strategy_key != self.key or prepared.vertex_count != 3:
            raise ValueError("right-triangle strategy/profile mismatch")
        result = analyze_right_triangle(prepared.coordinates)
        return GeometryAnalysis(
            area=result.area,
            area_by_coordinates=result.area_by_coordinates,
            details={
                "points": prepared.coordinates,
                "right_angle": result.right_angle,
                "cathetus_lengths": result.cathetus_lengths,
            },
        )

    def render_solution_svg(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Return original bytes because this strategy has no diagram stage."""

        return prepared.condition_svg_path.read_bytes()

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the complete right-triangle substitution formula."""

        horizontal, vertical = analysis.details["cathetus_lengths"]
        return (
            r"S=\frac{1}{2}ab="
            rf"\frac{{1}}{{2}}\cdot {horizontal}\cdot {vertical}="
            f"{format_number(analysis.area, latex=True)}"
        )

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return the prototype right-triangle explanation."""

        return centered_formula_html(
            "Площадь прямоугольного треугольника равна половине произведения "
            "его катетов. Поэтому",
            self.build_formula(analysis, profile),
        )

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the exact numeric answer."""

        return build_answer_html(analysis)

