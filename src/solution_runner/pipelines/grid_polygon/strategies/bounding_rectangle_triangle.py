"""Render triangle area as a bounding-rectangle complement."""

from __future__ import annotations

from fractions import Fraction

from ..geometry.quadrilateral import convex_hull, quadrilateral_coordinate_area
from ..geometry.triangle import triangle_coordinate_area
from ..models import GeometryAnalysis, GroupProfile, PreparedGridPolygon
from .protocol import (
    append_solution_construction,
    build_answer_html,
    centered_formula_html,
    format_number,
    svg_coordinate_mapper,
    svg_number,
)


def _analyze_complement(points: tuple[tuple[int, int], ...]) -> GeometryAnalysis:
    """Calculate a three/four-point bounding complement and verify by shoelace."""

    hull = convex_hull(points)
    if len(hull) not in {3, 4}:
        raise ValueError("bounding strategy requires three or four hull vertices")
    coordinate_area = (
        triangle_coordinate_area(points)
        if len(points) == 3
        else quadrilateral_coordinate_area(hull)
    )
    return _analyze_ordered_complement(hull, coordinate_area)


def _analyze_ordered_complement(
    points: tuple[tuple[int, int], ...],
    coordinate_area: Fraction,
) -> GeometryAnalysis:
    """Subtract non-overlapping edge projections for one axis-monotone polygon."""

    xmin, xmax = min(x for x, _ in points), max(x for x, _ in points)
    ymin, ymax = min(y for _, y in points), max(y for _, y in points)
    rectangle_width = Fraction(xmax - xmin)
    rectangle_height = Fraction(ymax - ymin)
    terms: list[tuple[str, Fraction, Fraction, Fraction]] = []
    projections: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    decomposition: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        dx = end[0] - start[0]
        if dx == 0:
            continue
        width = Fraction(abs(dx))
        if dx > 0:
            boundary_y = ymin
            first_height = Fraction(start[1] - ymin)
            second_height = Fraction(end[1] - ymin)
        else:
            boundary_y = ymax
            first_height = Fraction(ymax - start[1])
            second_height = Fraction(ymax - end[1])
        minimum = min(first_height, second_height)
        difference = abs(first_height - second_height)
        if minimum:
            terms.append(("rectangle", width, minimum, width * minimum))
        if difference:
            terms.append(("triangle", width, difference, width * difference / 2))
        if minimum:
            separator_y = ymin + int(minimum) if dx > 0 else ymax - int(minimum)
            left, right = sorted((start[0], end[0]))
            decomposition.add(((left, separator_y), (right, separator_y)))
        for point, height in ((start, first_height), (end, second_height)):
            if xmin < point[0] < xmax and height:
                projections.add((point, (point[0], boundary_y)))
    terms.sort(key=lambda term: (0 if term[0] == "rectangle" else 1, -term[3], -term[1], -term[2]))
    area = rectangle_width * rectangle_height - sum((term[3] for term in terms), Fraction())
    if area != coordinate_area:
        raise ValueError("complement and coordinate area calculations disagree")
    return GeometryAnalysis(
        area=area,
        area_by_coordinates=coordinate_area,
        details={
            "points": points,
            "bounds": (xmin, ymin, xmax, ymax),
            "rectangle_width": rectangle_width,
            "rectangle_height": rectangle_height,
            "exterior_terms": tuple(terms),
            "projections": tuple(sorted(projections)),
            "decomposition_lines": tuple(sorted(decomposition)),
        },
    )


class BoundingRectangleTriangleStrategy:
    """Subtract exterior pieces from one visible bounding rectangle."""

    key = "bounding-rectangle-triangle"
    requires_solution_diagram = True

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Calculate and independently verify the complement area."""

        if profile.strategy_key != self.key or prepared.vertex_count != 3:
            raise ValueError("bounding triangle strategy/profile mismatch")
        return _analyze_complement(prepared.coordinates)

    def render_solution_svg(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Overlay all four bounding sides and internal decomposition lines."""

        source = prepared.condition_svg_path.read_bytes()
        points = tuple(analysis.details["points"])
        mapper, _ = svg_coordinate_mapper(source, points)
        xmin, ymin, xmax, ymax = analysis.details["bounds"]
        corners = ((xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax))
        specs = [
            ("bounding-side", start, corners[(index + 1) % 4])
            for index, start in enumerate(corners)
        ]
        specs.extend(("projection", start, end) for start, end in analysis.details["projections"])
        specs.extend(("decomposition", start, end) for start, end in analysis.details["decomposition_lines"])
        lines = []
        for kind, start, end in specs:
            x1, y1 = mapper(start)
            x2, y2 = mapper(end)
            lines.append(
                f'  <line data-kind="{kind}" x1="{svg_number(x1)}" y1="{svg_number(y1)}" '
                f'x2="{svg_number(x2)}" y2="{svg_number(y2)}" />'
            )
        return append_solution_construction(source, lines)

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the deterministic rectangle-minus-pieces formula."""

        parts = [
            rf"S={format_number(analysis.details['rectangle_width'], latex=True)}\cdot "
            rf"{format_number(analysis.details['rectangle_height'], latex=True)}"
        ]
        for kind, width, height, _ in analysis.details["exterior_terms"]:
            if kind == "rectangle":
                parts.append(rf"-{format_number(width, latex=True)}\cdot {format_number(height, latex=True)}")
            else:
                parts.append(
                    rf"-\frac{{1}}{{2}}\cdot {format_number(width, latex=True)}\cdot "
                    rf"{format_number(height, latex=True)}"
                )
        parts.append(f"={format_number(analysis.area, latex=True)}")
        return "".join(parts)

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return the selected reusable complement explanation."""

        terms = analysis.details["exterior_terms"]
        rectangles = sum(term[0] == "rectangle" for term in terms)
        triangles = sum(term[0] == "triangle" for term in terms)
        if profile.solution_text_profile == "triangle-three-exterior":
            count = {1: "одного", 2: "двух", 3: "трех"}.get(triangles)
            if rectangles or count is None:
                raise ValueError("triangle-three-exterior profile has incompatible pieces")
            prose = (
                "Площадь треугольника равна разности площади прямоугольника и "
                f"площадей {count} прямоугольных треугольников, гипотенузы которых "
                "являются сторонами исходного треугольника. Поэтому"
            )
        else:
            prose = (
                "Площадь треугольника равна разности площади большого "
                "прямоугольника и площадей внешних фигур. Поэтому"
            )
        return centered_formula_html(prose, self.build_formula(analysis, profile))

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the exact numeric answer."""

        return build_answer_html(analysis)
