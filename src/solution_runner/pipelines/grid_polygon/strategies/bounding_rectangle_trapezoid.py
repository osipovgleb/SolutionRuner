"""Render trapezoid area as a shared bounding-rectangle complement."""

from __future__ import annotations

from ..geometry.quadrilateral import convex_hull
from ..models import GeometryAnalysis, GroupProfile, PreparedGridPolygon
from .bounding_rectangle_triangle import (
    BoundingRectangleTriangleStrategy,
    _analyze_complement,
)
from .protocol import centered_formula_html


class BoundingRectangleTrapezoidStrategy(BoundingRectangleTriangleStrategy):
    """Reuse common complement math and SVG drawing for trapezoids."""

    key = "bounding-rectangle-trapezoid"

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Calculate complement area after validating trapezoid geometry."""

        if profile.strategy_key != self.key or prepared.vertex_count != 4:
            raise ValueError("bounding trapezoid strategy/profile mismatch")
        hull = convex_hull(prepared.coordinates)
        edges = [
            (
                hull[(index + 1) % 4][0] - hull[index][0],
                hull[(index + 1) % 4][1] - hull[index][1],
            )
            for index in range(4)
        ]
        parallel_pairs = sum(
            edges[first][0] * edges[second][1]
            == edges[first][1] * edges[second][0]
            for first, second in ((0, 2), (1, 3))
        )
        if parallel_pairs != 1:
            raise ValueError("bounding strategy requires one parallel opposite pair")
        return _analyze_complement(prepared.coordinates)

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return complement prose over the shared formula."""

        terms = analysis.details["exterior_terms"]
        rectangles = sum(term[0] == "rectangle" for term in terms)
        triangles = sum(term[0] == "triangle" for term in terms)
        pieces: list[str] = []
        if rectangles == 1:
            pieces.append("прямоугольника")
        elif rectangles:
            pieces.append(f"{rectangles} прямоугольников")
        if triangles == 1:
            pieces.append("прямоугольного треугольника")
        elif triangles:
            pieces.append(f"{triangles} прямоугольных треугольников")
        if not pieces:
            raise ValueError("bounding construction has no exterior pieces")
        exterior = " и ".join(pieces)
        width = analysis.details["rectangle_width"]
        height = analysis.details["rectangle_height"]
        shape = "квадрата" if width == height else "прямоугольника"
        return centered_formula_html(
            f"Дополним трапецию до {shape}. Её площадь равна разности площади "
            f"этого {shape} и площадей внешних фигур: {exterior}.",
            self.build_formula(analysis, profile),
        )
