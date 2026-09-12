"""Render reusable trapezoid solutions from parallel bases and height."""

from __future__ import annotations

from dataclasses import replace

from ..geometry.quadrilateral import analyze_parallel_bases_trapezoid, convex_hull
from ..models import GeometryAnalysis, GroupProfile, PreparedGridPolygon, SolutionDiagramSpec
from .bounding_rectangle_trapezoid import (
    BoundingRectangleTrapezoidStrategy,
    TrapezoidPickStrategy,
)
from .protocol import build_answer_html, centered_formula_html, format_number


def _orientation(points: tuple[tuple[int, int], ...]) -> str:
    """Return the audited orientation of the unique parallel-base pair."""

    hull = convex_hull(points)
    edges = [
        (
            hull[(index + 1) % 4][0] - hull[index][0],
            hull[(index + 1) % 4][1] - hull[index][1],
        )
        for index in range(4)
    ]
    pair = next(
        pair
        for pair in ((0, 2), (1, 3))
        if edges[pair[0]][0] * edges[pair[1]][1]
        == edges[pair[0]][1] * edges[pair[1]][0]
    )
    edge = edges[pair[0]]
    if edge[0] == 0:
        return "vertical"
    if edge[1] == 0:
        return "horizontal"
    return "slanted"


class ParallelBasesTrapezoidStrategy:
    """Use one exact base-height formula for every base orientation."""

    key = "parallel-bases-trapezoid"
    requires_solution_diagram = False

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Calculate base-height area and verify it by shoelace."""

        if profile.strategy_key != self.key or prepared.vertex_count != 4:
            raise ValueError("parallel-bases strategy/profile mismatch")
        result = analyze_parallel_bases_trapezoid(prepared.coordinates)
        return GeometryAnalysis(
            area=result.area,
            area_by_coordinates=result.area_by_coordinates,
            details={
                "points": prepared.coordinates,
                "base_lengths": result.base_lengths,
                "height": result.height,
                "orientation": _orientation(prepared.coordinates),
            },
        )

    def render_solution_svg(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Return original bytes because this formula needs no diagram."""

        return prepared.condition_svg_path.read_bytes()

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the symbolic rule followed by measured substitution."""

        first, second = analysis.details["base_lengths"]
        height = analysis.details["height"]
        return (
            r"S=\frac{a+b}{2}\cdot h="
            rf"\frac{{{format_number(first, latex=True)}+"
            rf"{format_number(second, latex=True)}}}{{2}}\cdot "
            rf"{format_number(height, latex=True)}="
            f"{format_number(analysis.area, latex=True)}"
        )

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return one clear reusable trapezoid explanation."""

        return centered_formula_html(
            "Площадь трапеции равна произведению полусуммы оснований на высоту. "
            "Поэтому",
            self.build_formula(analysis, profile),
        )

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the exact numeric answer."""

        return build_answer_html(analysis)


class ParallelBasesTrapezoidThreeMethodsStrategy(TrapezoidPickStrategy):
    """Keep the base-height solution and append rectangle and Pick variants."""

    key = "parallel-bases-trapezoid-three-methods"

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Require all three independently calculated areas to match."""

        if profile.strategy_key != self.key or prepared.vertex_count != 4:
            raise ValueError("three-method trapezoid strategy/profile mismatch")
        base = ParallelBasesTrapezoidStrategy().analyze(
            prepared,
            replace(profile, strategy_key="parallel-bases-trapezoid"),
        )
        visual = TrapezoidPickStrategy().analyze(
            prepared,
            replace(profile, strategy_key="trapezoid-pick"),
        )
        if base.area != visual.area or base.area_by_coordinates != visual.area_by_coordinates:
            raise ValueError("trapezoid area calculations disagree")
        return GeometryAnalysis(
            area=visual.area,
            area_by_coordinates=visual.area_by_coordinates,
            details={**visual.details, **base.details},
        )

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the original base-height formula as the first method."""

        return ParallelBasesTrapezoidStrategy().build_formula(analysis, profile)

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return formula first, then the requested illustrated alternatives."""

        base = ParallelBasesTrapezoidStrategy().build_solution_html(analysis, profile)
        rectangle = BoundingRectangleTrapezoidStrategy().build_solution_html(
            analysis,
            replace(profile, strategy_key="bounding-rectangle-trapezoid"),
        )
        return (
            '<section data-content-kind="solution" data-solution-title="Решение">'
            f"{base}</section>"
            '<section data-content-kind="solution" '
            'data-solution-title="Приведём другое решение.">'
            f"{rectangle}</section>"
            '<section data-content-kind="solution" data-solution-title="Ещё одно решение.">'
            f"{self._pick_solution(analysis)}</section>"
        )

    def render_solution_diagrams(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> tuple[SolutionDiagramSpec, ...]:
        """Attach diagrams only to the two newly added solution sections."""

        del profile
        return (
            SolutionDiagramSpec(
                asset_key="generated_solution_diagram",
                solution_variant_index=1,
                svg_bytes=self.render_solution_svg(prepared, analysis),
                alt_text=f"Обводка прямоугольником: {list(prepared.coordinates)}",
            ),
            SolutionDiagramSpec(
                asset_key="generated_pick_diagram",
                solution_variant_index=2,
                svg_bytes=self._render_pick_svg(prepared, analysis),
                alt_text=f"Метод Пика: {list(prepared.coordinates)}",
            ),
        )
