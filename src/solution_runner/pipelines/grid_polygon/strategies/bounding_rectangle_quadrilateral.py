"""Render convex and concave quadrilaterals with two child-facing methods."""

from __future__ import annotations

from fractions import Fraction
from xml.etree import ElementTree

from ..geometry.quadrilateral import (
    convex_hull,
    enumerate_lattice_points,
    quadrilateral_coordinate_area,
)
from ..models import (
    GeometryAnalysis,
    GroupProfile,
    PreparedGridPolygon,
    SolutionDiagramSpec,
)
from .bounding_rectangle_triangle import (
    BoundingRectangleTriangleStrategy,
    _analyze_complement,
    _analyze_ordered_complement,
)
from .protocol import (
    append_solution_construction,
    centered_formula_html,
    format_number,
    svg_coordinate_mapper,
    svg_number,
)


RHOMBUS_TWO_METHODS_PROFILE = "rhombus-two-methods"
QUADRILATERAL_PICK_PROFILE = "quadrilateral-pick"
QUADRILATERAL_PICK_FIRST_PROFILE = "quadrilateral-pick-first"
QUADRILATERAL_PICK_PROFILES = frozenset(
    {QUADRILATERAL_PICK_PROFILE, QUADRILATERAL_PICK_FIRST_PROFILE}
)


def _signed_doubled_area(points: tuple[tuple[int, int], ...]) -> int:
    """Return ordered signed doubled area."""

    return sum(
        start[0] * end[1] - start[1] * end[0]
        for start, end in zip(points, points[1:] + points[:1], strict=True)
    )


def _counterclockwise(
    points: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    """Return one stable positive-area traversal without changing adjacency."""

    return points if _signed_doubled_area(points) > 0 else tuple(reversed(points))


def _is_x_monotone(points: tuple[tuple[int, int], ...]) -> bool:
    """Return whether every open vertical slice meets one connected interval."""

    xs = sorted({point[0] for point in points})
    for left, right in zip(xs, xs[1:]):
        probe = Fraction(left + right, 2)
        intersections = 0
        for start, end in zip(points, points[1:] + points[:1], strict=True):
            low, high = sorted((start[0], end[0]))
            if low < probe < high:
                intersections += 1
        if intersections != 2:
            return False
    return True


def _unswap_point(point: tuple[int, int]) -> tuple[int, int]:
    """Return one point from transposed analysis coordinates."""

    return point[1], point[0]


def _unswap_analysis(
    analysis: GeometryAnalysis,
    points: tuple[tuple[int, int], ...],
) -> GeometryAnalysis:
    """Map transposed construction lines back to condition coordinates."""

    xmin, ymin, xmax, ymax = analysis.details["bounds"]
    return GeometryAnalysis(
        area=analysis.area,
        area_by_coordinates=analysis.area_by_coordinates,
        details={
            **analysis.details,
            "points": points,
            "bounds": (ymin, xmin, ymax, xmax),
            "rectangle_width": analysis.details["rectangle_height"],
            "rectangle_height": analysis.details["rectangle_width"],
            "projections": tuple(
                (_unswap_point(start), _unswap_point(end))
                for start, end in analysis.details["projections"]
            ),
            "decomposition_lines": tuple(
                (_unswap_point(start), _unswap_point(end))
                for start, end in analysis.details["decomposition_lines"]
            ),
        },
    )


def _direct_concave_complement(
    points: tuple[tuple[int, int], ...],
    area: Fraction,
) -> GeometryAnalysis | None:
    """Return one exact monotone rectangle complement, trying both grid axes."""

    for swapped in (False, True):
        transformed = (
            tuple((y, x) for x, y in points)
            if swapped
            else points
        )
        ordered = _counterclockwise(transformed)
        if not _is_x_monotone(ordered):
            continue
        try:
            analysis = _analyze_ordered_complement(ordered, area)
        except ValueError:
            continue
        if swapped:
            analysis = _unswap_analysis(analysis, points)
        else:
            analysis = GeometryAnalysis(
                area=analysis.area,
                area_by_coordinates=analysis.area_by_coordinates,
                details={**analysis.details, "points": points},
            )
        return GeometryAnalysis(
            area=analysis.area,
            area_by_coordinates=analysis.area_by_coordinates,
            details={**analysis.details, "construction_mode": "rectangle-complement"},
        )
    return None


def _concave_triangle_fallback(
    points: tuple[tuple[int, int], ...],
    area: Fraction,
) -> GeometryAnalysis:
    """Represent one non-monotone concave quadrilateral as hull minus notch."""

    ordered = _counterclockwise(points)
    turns = tuple(
        (current[0] - previous[0]) * (following[1] - current[1])
        - (current[1] - previous[1]) * (following[0] - current[0])
        for previous, current, following in (
            (ordered[index - 1], ordered[index], ordered[(index + 1) % 4])
            for index in range(4)
        )
    )
    reflex = [index for index, turn in enumerate(turns) if turn < 0]
    if len(reflex) != 1:
        raise ValueError("concave quadrilateral must have one reflex vertex")
    reflex_index = reflex[0]
    outer_points = tuple(
        point for index, point in enumerate(ordered) if index != reflex_index
    )
    notch_points = (
        ordered[reflex_index - 1],
        ordered[reflex_index],
        ordered[(reflex_index + 1) % 4],
    )
    outer = _analyze_complement(outer_points)
    notch = _analyze_complement(notch_points)
    if outer.area - notch.area != area:
        raise ValueError("outer triangle and notch areas disagree")
    return GeometryAnalysis(
        area=area,
        area_by_coordinates=area,
        details={
            "points": points,
            "construction_mode": "outer-triangle-minus-notch",
            "outer_analysis": outer,
            "notch_analysis": notch,
            "notch_edge": (notch_points[0], notch_points[2]),
        },
    )


def _with_pick_details(
    analysis: GeometryAnalysis,
    points: tuple[tuple[int, int], ...],
) -> GeometryAnalysis:
    """Attach independently enumerated values displayed by Pick's formula."""

    nodes = enumerate_lattice_points(points)
    interior, boundary = len(nodes.interior), len(nodes.boundary)
    pick_area = Fraction(interior) + Fraction(boundary, 2) - 1
    if pick_area != analysis.area:
        raise ValueError("Pick and rectangle areas disagree")
    return GeometryAnalysis(
        area=analysis.area,
        area_by_coordinates=analysis.area_by_coordinates,
        details={
            **analysis.details,
            "pick_interior": interior,
            "pick_boundary": boundary,
            "pick_interior_points": nodes.interior,
            "pick_boundary_points": nodes.boundary,
        },
    )


def _rhombus_diagonal_lengths(
    points: tuple[tuple[int, int], ...],
) -> tuple[Fraction, Fraction]:
    """Return axis-aligned rhombus diagonals after checking all four sides."""

    hull = convex_hull(points)
    side_lengths_squared = {
        (hull[(index + 1) % 4][0] - point[0]) ** 2
        + (hull[(index + 1) % 4][1] - point[1]) ** 2
        for index, point in enumerate(hull)
    }
    if len(side_lengths_squared) != 1:
        raise ValueError("rhombus solution requires four equal sides")
    diagonals = ((hull[0], hull[2]), (hull[1], hull[3]))
    vectors = tuple(
        (end[0] - start[0], end[1] - start[1])
        for start, end in diagonals
    )
    if not all((dx == 0) != (dy == 0) for dx, dy in vectors):
        raise ValueError("rhombus solution requires grid-axis diagonals")
    if vectors[0][0] * vectors[1][0] + vectors[0][1] * vectors[1][1] != 0:
        raise ValueError("rhombus solution requires perpendicular diagonals")
    lengths = tuple(Fraction(abs(dx or dy)) for dx, dy in vectors)
    return tuple(sorted(lengths, reverse=True))


def _rhombus_rectangle_formula(analysis: GeometryAnalysis) -> str:
    """Compress four equal exterior triangles into the prototype formula."""

    terms = analysis.details["exterior_terms"]
    if (
        len(terms) != 4
        or any(kind != "triangle" for kind, _, _, _ in terms)
        or len(set(terms)) != 1
    ):
        raise ValueError("rhombus solution requires four equal exterior triangles")
    _, width, height, _ = terms[0]
    return (
        rf"S={format_number(analysis.details['rectangle_width'], latex=True)}\cdot "
        rf"{format_number(analysis.details['rectangle_height'], latex=True)}"
        rf"-4\cdot \frac{{1}}{{2}}\cdot {format_number(width, latex=True)}\cdot "
        rf"{format_number(height, latex=True)}={format_number(analysis.area, latex=True)}"
    )


def _piece_names(analysis: GeometryAnalysis) -> list[str]:
    """Return concise genitive names for exterior rectangles and triangles."""

    terms = analysis.details["exterior_terms"]
    squares = sum(
        kind == "rectangle" and width == height
        for kind, width, height, _ in terms
    )
    rectangles = sum(
        kind == "rectangle" and width != height
        for kind, width, height, _ in terms
    )
    triangles = sum(kind == "triangle" for kind, _, _, _ in terms)
    pieces: list[str] = []
    if squares == 1:
        pieces.append("квадрата")
    elif squares:
        pieces.append(f"{squares} квадратов")
    if rectangles == 1:
        pieces.append("прямоугольника")
    elif rectangles:
        pieces.append(f"{rectangles} прямоугольников")
    if triangles == 1:
        pieces.append("прямоугольного треугольника")
    elif triangles:
        pieces.append(f"{triangles} прямоугольных треугольников")
    return pieces


class BoundingRectangleQuadrilateralStrategy(BoundingRectangleTriangleStrategy):
    """Reuse rectangle primitives for ordered convex and concave quadrilaterals."""

    key = "bounding-rectangle-quadrilateral"

    def analyze(
        self,
        prepared: PreparedGridPolygon,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Calculate and independently verify one four-vertex complement area."""

        if profile.strategy_key != self.key or prepared.vertex_count != 4:
            raise ValueError("bounding quadrilateral strategy/profile mismatch")
        points = prepared.geometry_coordinates
        try:
            convex_hull(points)
        except ValueError:
            area = quadrilateral_coordinate_area(points)
            analysis = _direct_concave_complement(points, area)
            if analysis is None:
                analysis = _concave_triangle_fallback(points, area)
        else:
            base = _analyze_complement(points)
            analysis = GeometryAnalysis(
                area=base.area,
                area_by_coordinates=base.area_by_coordinates,
                details={**base.details, "construction_mode": "rectangle-complement"},
            )
        if profile.solution_text_profile in QUADRILATERAL_PICK_PROFILES:
            return _with_pick_details(analysis, points)
        if profile.solution_text_profile != RHOMBUS_TWO_METHODS_PROFILE:
            return analysis
        diagonal_lengths = _rhombus_diagonal_lengths(points)
        if diagonal_lengths[0] * diagonal_lengths[1] / 2 != analysis.area:
            raise ValueError("rhombus diagonal and coordinate areas disagree")
        return GeometryAnalysis(
            area=analysis.area,
            area_by_coordinates=analysis.area_by_coordinates,
            details={**analysis.details, "diagonal_lengths": diagonal_lengths},
        )

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the generic complement or the grouped prototype formula."""

        if profile.solution_text_profile == RHOMBUS_TWO_METHODS_PROFILE:
            return _rhombus_rectangle_formula(analysis)
        if analysis.details.get("construction_mode") == "outer-triangle-minus-notch":
            outer = analysis.details["outer_analysis"]
            notch = analysis.details["notch_analysis"]
            return (
                rf"S={format_number(outer.area, latex=True)}"
                rf"-{format_number(notch.area, latex=True)}"
                rf"={format_number(analysis.area, latex=True)}"
            )
        return super().build_formula(analysis, profile)

    def render_solution_svg(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Render either one rectangle complement or the safe notch fallback."""

        if analysis.details.get("construction_mode") != "outer-triangle-minus-notch":
            return super().render_solution_svg(prepared, analysis)
        source = prepared.condition_svg_path.read_bytes()
        mapper, _ = svg_coordinate_mapper(source, prepared.coordinates)
        outer = analysis.details["outer_analysis"]
        notch = analysis.details["notch_analysis"]
        specs: list[tuple[str, tuple[int, int], tuple[int, int]]] = []
        for prefix, child in (("outer", outer), ("notch", notch)):
            xmin, ymin, xmax, ymax = child.details["bounds"]
            corners = ((xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax))
            specs.extend(
                (f"{prefix}-bounding-side", start, corners[(index + 1) % 4])
                for index, start in enumerate(corners)
            )
            specs.extend(
                (f"{prefix}-projection", start, end)
                for start, end in child.details["projections"]
            )
            specs.extend(
                (f"{prefix}-decomposition", start, end)
                for start, end in child.details["decomposition_lines"]
            )
        specs.append(("notch-side", *analysis.details["notch_edge"]))
        unique: list[tuple[str, tuple[int, int], tuple[int, int]]] = []
        seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()
        for kind, start, end in specs:
            identity = tuple(sorted((start, end)))
            if start == end or identity in seen:
                continue
            seen.add(identity)
            unique.append((kind, start, end))
        lines = []
        for kind, start, end in unique:
            x1, y1 = mapper(start)
            x2, y2 = mapper(end)
            lines.append(
                f'  <line data-kind="{kind}" x1="{svg_number(x1)}" y1="{svg_number(y1)}" '
                f'x2="{svg_number(x2)}" y2="{svg_number(y2)}" />'
            )
        return append_solution_construction(source, lines)

    def render_solution_diagrams(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> tuple[SolutionDiagramSpec, ...]:
        """Return the construction and optional separate Pick-node diagram."""

        construction = SolutionDiagramSpec(
            asset_key="generated_solution_diagram",
            solution_variant_index=0,
            svg_bytes=self.render_solution_svg(prepared, analysis),
            alt_text=str(list(prepared.coordinates)),
        )
        if profile.solution_text_profile not in QUADRILATERAL_PICK_PROFILES:
            return (construction,)
        pick = SolutionDiagramSpec(
            asset_key="generated_pick_diagram",
            solution_variant_index=1,
            svg_bytes=self._render_pick_svg(prepared, analysis),
            alt_text=f"Метод Пика: {list(prepared.coordinates)}",
        )
        if profile.solution_text_profile == QUADRILATERAL_PICK_FIRST_PROFILE:
            return (
                SolutionDiagramSpec(
                    asset_key=pick.asset_key,
                    solution_variant_index=0,
                    svg_bytes=pick.svg_bytes,
                    alt_text=pick.alt_text,
                ),
                SolutionDiagramSpec(
                    asset_key=construction.asset_key,
                    solution_variant_index=1,
                    svg_bytes=construction.svg_bytes,
                    alt_text=construction.alt_text,
                ),
            )
        return (construction, pick)

    def _render_pick_svg(
        self,
        prepared: PreparedGridPolygon,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Overlay exact yellow interior and green boundary lattice nodes."""

        source = prepared.condition_svg_path.read_bytes()
        mapper, grid_step = svg_coordinate_mapper(
            source,
            prepared.geometry_coordinates,
        )
        radius = max(2.5, grid_step * 0.14)
        circles: list[str] = []
        for kind, fill, points in (
            ("pick-interior", "#F5C518", analysis.details["pick_interior_points"]),
            ("pick-boundary", "#22A06B", analysis.details["pick_boundary_points"]),
        ):
            for point in points:
                cx, cy = mapper(point)
                circles.append(
                    f'  <circle data-kind="{kind}" cx="{svg_number(cx)}" '
                    f'cy="{svg_number(cy)}" r="{svg_number(radius)}" '
                    f'fill="{fill}" />'
                )
        text = source.decode("utf-8")
        closing = text.rfind("</svg>")
        if closing < 0:
            raise ValueError("condition SVG has no closing svg tag")
        group = (
            '<g id="pick-lattice-points" stroke="#0D0F0F" stroke-width="0.75">\n'
            + "\n".join(circles)
            + "\n</g>"
        )
        rendered = (text[:closing].rstrip() + "\n" + group + "\n</svg>\n").encode()
        ElementTree.fromstring(rendered)
        return rendered

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return quadrilateral wording over the shared exact formula."""

        if profile.solution_text_profile == RHOMBUS_TWO_METHODS_PROFILE:
            diagonal_lengths = analysis.details.get("diagonal_lengths")
            if not diagonal_lengths:
                raise ValueError("rhombus solution has no verified diagonals")
            first = centered_formula_html(
                "Площадь ромба равна разности площади прямоугольника и площадей "
                "четырёх равных прямоугольных треугольников, гипотенузы которых "
                "являются сторонами исходного ромба. Поэтому",
                self.build_formula(analysis, profile),
            )
            diagonal_formula = (
                rf"S=\frac{{1}}{{2}}\cdot "
                rf"{format_number(diagonal_lengths[0], latex=True)}\cdot "
                rf"{format_number(diagonal_lengths[1], latex=True)}="
                rf"{format_number(analysis.area, latex=True)}"
            )
            second = centered_formula_html(
                "Заданный четырёхугольник — ромб. Его площадь равна половине "
                "произведения диагоналей. Поэтому",
                diagonal_formula,
            )
            return (
                '<section data-content-kind="solution" data-solution-title="Решение">'
                f"{first}</section>"
                '<section data-content-kind="solution" '
                'data-solution-title="Приведем другое решение.">'
                f"{second}</section>"
            )

        if profile.solution_text_profile in QUADRILATERAL_PICK_PROFILES:
            rectangle = self._build_rectangle_solution(analysis, profile)
            interior = analysis.details["pick_interior"]
            boundary = analysis.details["pick_boundary"]
            pick_formula = (
                rf"S=\mathrm{{В}}+\frac{{\mathrm{{Г}}}}{{2}}-1="
                rf"{interior}+\frac{{{boundary}}}{{2}}-1="
                rf"{format_number(analysis.area, latex=True)}"
            )
            pick = centered_formula_html(
                f"Внутри четырёхугольника находится {interior} узлов квадратной "
                f"решётки, а на его границе — {boundary} узлов. По формуле Пика",
                pick_formula,
            )
            first, second = (
                (pick, rectangle)
                if profile.solution_text_profile == QUADRILATERAL_PICK_FIRST_PROFILE
                else (rectangle, pick)
            )
            return (
                '<section data-content-kind="solution" data-solution-title="Решение">'
                f"{first}</section>"
                '<section data-content-kind="solution" '
                'data-solution-title="Приведём другое решение.">'
                f"{second}</section>"
            )

        return self._build_rectangle_solution(analysis, profile)

    def _build_rectangle_solution(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return the first child-facing rectangle or triangle-complement method."""

        if analysis.details.get("construction_mode") == "outer-triangle-minus-notch":
            outer = analysis.details["outer_analysis"]
            notch = analysis.details["notch_analysis"]
            outer_formula = BoundingRectangleTriangleStrategy.build_formula(
                self,
                outer,
                profile,
            ).replace("S=", "S_1=", 1)
            notch_formula = BoundingRectangleTriangleStrategy.build_formula(
                self,
                notch,
                profile,
            ).replace("S=", "S_2=", 1)
            return (
                centered_formula_html(
                    "Дополним фигуру до внешнего треугольника. Его площадь равна",
                    outer_formula,
                )
                + centered_formula_html(
                    "Площадь треугольного выреза равна",
                    notch_formula,
                )
                + centered_formula_html(
                    "Вычтем площадь треугольного выреза из площади внешнего "
                    "треугольника:",
                    self.build_formula(analysis, profile),
                )
            )

        width = analysis.details["rectangle_width"]
        height = analysis.details["rectangle_height"]
        shape = "квадрата" if width == height else "прямоугольника"
        pieces = _piece_names(analysis)
        if pieces:
            prose = (
                f"Площадь четырёхугольника равна разности площади большого {shape} "
                f"и площадей внешних фигур: {' и '.join(pieces)}. Поэтому"
            )
        else:
            prose = (
                f"Четырёхугольник совпадает с границами {shape}, поэтому его "
                "площадь равна произведению длины и ширины."
            )
        return centered_formula_html(prose, self.build_formula(analysis, profile))
