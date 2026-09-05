"""Render parallelograms by height, rectangle complement, and Pick's formula."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from ..models import (
    GeometryAnalysis,
    GroupProfile,
    PreparedGridPolygon,
    SolutionDiagramSpec,
)
from .bounding_rectangle_quadrilateral import (
    QUADRILATERAL_PICK_PROFILE,
    BoundingRectangleQuadrilateralStrategy,
)
from .protocol import (
    append_solution_construction,
    build_answer_html,
    centered_formula_html,
    format_number,
    svg_coordinate_mapper,
    svg_number,
)


def _edge(
    start: tuple[int, int],
    end: tuple[int, int],
) -> tuple[int, int]:
    """Return one directed polygon-edge vector."""

    return end[0] - start[0], end[1] - start[1]


def _base_height_details(
    points: tuple[tuple[int, int], ...],
) -> dict[str, object]:
    """Return one axis-aligned parallelogram base and its perpendicular height."""

    if len(points) != 4 or len(set(points)) != 4:
        raise ValueError("parallelogram must contain four distinct vertices")
    edges = tuple(
        _edge(points[index], points[(index + 1) % 4])
        for index in range(4)
    )
    if edges[0] != (-edges[2][0], -edges[2][1]) or edges[1] != (
        -edges[3][0],
        -edges[3][1],
    ):
        raise ValueError("parallelogram opposite edges do not match")
    candidates = [
        index
        for index in (0, 1)
        if (edges[index][0] == 0) != (edges[index][1] == 0)
    ]
    if not candidates:
        raise ValueError("parallelogram requires a horizontal or vertical base")
    base_index = max(
        candidates,
        key=lambda index: abs(edges[index][0] or edges[index][1]),
    )
    base_start = points[base_index]
    base_end = points[(base_index + 1) % 4]
    apex = points[(base_index + 2) % 4]
    horizontal = edges[base_index][1] == 0
    altitude_foot = (
        (apex[0], base_start[1])
        if horizontal
        else (base_start[0], apex[1])
    )
    base_length = Fraction(abs(edges[base_index][0] or edges[base_index][1]))
    height = Fraction(
        abs(apex[1] - base_start[1])
        if horizontal
        else abs(apex[0] - base_start[0])
    )
    return {
        "base_start": base_start,
        "base_end": base_end,
        "apex": apex,
        "altitude_foot": altitude_foot,
        "base_length": base_length,
        "height": height,
        "orientation": "horizontal" if horizontal else "vertical",
        "base_height_area": base_length * height,
    }


class ParallelogramThreeMethodsStrategy(BoundingRectangleQuadrilateralStrategy):
    """Combine three child-facing methods over one verified parallelogram."""

    key = "parallelogram-three-methods"
    requires_solution_diagram = True

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Require height, complement, Pick, and shoelace areas to agree."""

        if profile.strategy_key != self.key or prepared.vertex_count != 4:
            raise ValueError("parallelogram strategy/profile mismatch")
        base_height = _base_height_details(prepared.geometry_coordinates)
        rectangle_profile = replace(
            profile,
            strategy_key="bounding-rectangle-quadrilateral",
            solution_text_profile=QUADRILATERAL_PICK_PROFILE,
        )
        rectangle = BoundingRectangleQuadrilateralStrategy().analyze(
            prepared,
            rectangle_profile,
        )
        base_height_area = base_height["base_height_area"]
        pick_area = (
            Fraction(rectangle.details["pick_interior"])
            + Fraction(rectangle.details["pick_boundary"], 2)
            - 1
        )
        if base_height_area != rectangle.area or pick_area != rectangle.area:
            raise ValueError("parallelogram area calculations disagree")
        return GeometryAnalysis(
            area=rectangle.area,
            area_by_coordinates=rectangle.area_by_coordinates,
            details={
                **rectangle.details,
                **base_height,
                "rectangle_area": rectangle.area,
                "pick_area": pick_area,
            },
        )

    def _render_base_height_svg(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Overlay the selected base, perpendicular height, and right-angle mark."""

        source = prepared.condition_svg_path.read_bytes()
        mapper, cell_size = svg_coordinate_mapper(
            source,
            prepared.geometry_coordinates,
        )
        logical_start = analysis.details["base_start"]
        logical_end = analysis.details["base_end"]
        logical_apex = analysis.details["apex"]
        logical_foot = analysis.details["altitude_foot"]
        start, end = mapper(logical_start), mapper(logical_end)
        apex, foot = mapper(logical_apex), mapper(logical_foot)
        lines = [
            f'  <line data-kind="base" x1="{svg_number(start[0])}" '
            f'y1="{svg_number(start[1])}" x2="{svg_number(end[0])}" '
            f'y2="{svg_number(end[1])}" />',
            f'  <line data-kind="height" x1="{svg_number(apex[0])}" '
            f'y1="{svg_number(apex[1])}" x2="{svg_number(foot[0])}" '
            f'y2="{svg_number(foot[1])}" />',
        ]
        horizontal = analysis.details["orientation"] == "horizontal"
        if horizontal:
            minimum, maximum, foot_value = sorted((logical_start[0], logical_end[0])) + [logical_foot[0]]
        else:
            minimum, maximum, foot_value = sorted((logical_start[1], logical_end[1])) + [logical_foot[1]]
        if foot_value < minimum or foot_value > maximum:
            endpoint = start if foot_value < minimum else end
            lines.append(
                f'  <line data-kind="base-extension" x1="{svg_number(endpoint[0])}" '
                f'y1="{svg_number(endpoint[1])}" x2="{svg_number(foot[0])}" '
                f'y2="{svg_number(foot[1])}" stroke-dasharray="5 4" />'
            )
        marker = cell_size * 0.28
        if horizontal:
            x_direction = 1 if end[0] >= foot[0] else -1
            y_direction = -1 if apex[1] < foot[1] else 1
            marker_path = (
                f"M {svg_number(foot[0] + x_direction * marker)} {svg_number(foot[1])} "
                f"L {svg_number(foot[0] + x_direction * marker)} "
                f"{svg_number(foot[1] + y_direction * marker)} "
                f"L {svg_number(foot[0])} {svg_number(foot[1] + y_direction * marker)}"
            )
        else:
            x_direction = -1 if apex[0] < foot[0] else 1
            y_direction = 1 if end[1] >= foot[1] else -1
            marker_path = (
                f"M {svg_number(foot[0])} {svg_number(foot[1] + y_direction * marker)} "
                f"L {svg_number(foot[0] + x_direction * marker)} "
                f"{svg_number(foot[1] + y_direction * marker)} "
                f"L {svg_number(foot[0] + x_direction * marker)} {svg_number(foot[1])}"
            )
        lines.append(f'  <path data-kind="right-angle-marker" d="{marker_path}" />')
        return append_solution_construction(source, lines)

    def render_solution_diagrams(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> tuple[SolutionDiagramSpec, ...]:
        """Return one diagram for each of the three ordered solution variants."""

        del profile
        return (
            SolutionDiagramSpec(
                asset_key="generated_solution_diagram",
                solution_variant_index=0,
                svg_bytes=self._render_base_height_svg(prepared, analysis),
                alt_text=f"Основание и высота: {list(prepared.coordinates)}",
            ),
            SolutionDiagramSpec(
                asset_key="generated_rectangle_diagram",
                solution_variant_index=1,
                svg_bytes=super().render_solution_svg(prepared, analysis),
                alt_text=f"Обводка прямоугольником: {list(prepared.coordinates)}",
            ),
            SolutionDiagramSpec(
                asset_key="generated_pick_diagram",
                solution_variant_index=2,
                svg_bytes=super()._render_pick_svg(prepared, analysis),
                alt_text=f"Метод Пика: {list(prepared.coordinates)}",
            ),
        )

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the parallelogram base-height formula with measured values."""

        del profile
        return (
            rf"S=ah={format_number(analysis.details['base_length'], latex=True)}\cdot "
            rf"{format_number(analysis.details['height'], latex=True)}="
            rf"{format_number(analysis.area, latex=True)}"
        )

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return height, rectangle-complement, and Pick solution sections."""

        height = centered_formula_html(
            "Площадь параллелограмма равна произведению основания на высоту. Поэтому",
            self.build_formula(analysis, profile),
        )
        rectangle_profile = replace(
            profile,
            strategy_key="bounding-rectangle-quadrilateral",
            solution_text_profile=None,
        )
        rectangle = BoundingRectangleQuadrilateralStrategy()._build_rectangle_solution(
            analysis,
            rectangle_profile,
        )
        interior = analysis.details["pick_interior"]
        boundary = analysis.details["pick_boundary"]
        pick = centered_formula_html(
            f"Внутри параллелограмма находится {interior} узлов квадратной решётки, "
            f"а на его границе — {boundary} узлов. По формуле Пика",
            rf"S=\mathrm{{В}}+\frac{{\mathrm{{Г}}}}{{2}}-1="
            rf"{interior}+\frac{{{boundary}}}{{2}}-1="
            rf"{format_number(analysis.area, latex=True)}",
        )
        return (
            '<section data-content-kind="solution" data-solution-title="Решение">'
            f"{height}</section>"
            '<section data-content-kind="solution" '
            'data-solution-title="Приведём другое решение.">'
            f"{rectangle}</section>"
            '<section data-content-kind="solution" '
            'data-solution-title="Ещё одно решение.">'
            f"{pick}</section>"
        )

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the exact numeric area answer."""

        return build_answer_html(analysis)
