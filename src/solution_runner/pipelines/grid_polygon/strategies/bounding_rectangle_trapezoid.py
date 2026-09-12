"""Render trapezoid area as a shared bounding-rectangle complement."""

from __future__ import annotations

from dataclasses import replace

from ..geometry.quadrilateral import convex_hull
from ..models import GeometryAnalysis, GroupProfile, PreparedGridPolygon, SolutionDiagramSpec
from .bounding_rectangle_triangle import (
    BoundingRectangleTriangleStrategy,
    _analyze_complement,
)
from .bounding_rectangle_quadrilateral import BoundingRectangleQuadrilateralStrategy
from .protocol import centered_formula_html, format_number


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


class TrapezoidPickStrategy(BoundingRectangleQuadrilateralStrategy):
    """Render a trapezoid by rectangle complement and Pick's formula."""

    key = "trapezoid-pick"
    requires_solution_diagram = True

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Require the trapezoid and both lattice-area methods to agree."""

        if profile.strategy_key != self.key or prepared.vertex_count != 4:
            raise ValueError("trapezoid Pick strategy/profile mismatch")
        BoundingRectangleTrapezoidStrategy().analyze(
            prepared,
            replace(profile, strategy_key="bounding-rectangle-trapezoid"),
        )
        return BoundingRectangleQuadrilateralStrategy().analyze(
            prepared,
            replace(
                profile,
                strategy_key="bounding-rectangle-quadrilateral",
                solution_text_profile="quadrilateral-pick",
            ),
        )

    @staticmethod
    def _pick_solution(analysis: GeometryAnalysis) -> str:
        """Return the exact Pick-method explanation shared by trapezoid variants."""

        interior = analysis.details["pick_interior"]
        boundary = analysis.details["pick_boundary"]
        return centered_formula_html(
            f"Внутри трапеции находится {interior} узлов квадратной решётки, "
            f"а на её границе — {boundary} узлов. По формуле Пика",
            rf"S=\mathrm{{В}}+\frac{{\mathrm{{Г}}}}{{2}}-1="
            rf"{interior}+\frac{{{boundary}}}{{2}}-1="
            rf"{format_number(analysis.area, latex=True)}",
        )

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return the two illustrated trapezoid solutions in a fixed order."""

        rectangle = BoundingRectangleTrapezoidStrategy().build_solution_html(
            analysis,
            replace(profile, strategy_key="bounding-rectangle-trapezoid"),
        )
        return (
            '<section data-content-kind="solution" data-solution-title="Решение">'
            f"{rectangle}</section>"
            '<section data-content-kind="solution" '
            'data-solution-title="Приведём другое решение.">'
            f"{self._pick_solution(analysis)}</section>"
        )

    def render_solution_diagrams(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> tuple[SolutionDiagramSpec, ...]:
        """Return separate rectangle and lattice-point illustrations."""

        del profile
        return (
            SolutionDiagramSpec(
                asset_key="generated_solution_diagram",
                solution_variant_index=0,
                svg_bytes=self.render_solution_svg(prepared, analysis),
                alt_text=f"Обводка прямоугольником: {list(prepared.coordinates)}",
            ),
            SolutionDiagramSpec(
                asset_key="generated_pick_diagram",
                solution_variant_index=1,
                svg_bytes=self._render_pick_svg(prepared, analysis),
                alt_text=f"Метод Пика: {list(prepared.coordinates)}",
            ),
        )
