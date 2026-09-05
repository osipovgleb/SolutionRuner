"""Define the pure solution-strategy contract and shared rendering helpers."""

from __future__ import annotations

from fractions import Fraction
from html import escape
from itertools import permutations
from typing import Callable, Protocol
import re
from xml.etree import ElementTree

from ..models import GeometryAnalysis, GroupProfile, PreparedFigure, StrategyKey
from ..geometry.grid_polygon import GridPolygonError, raw_outline_points_from_svg


RED_STROKE = "#e22"
LEGACY_GRID_RENDER_TOLERANCE = 0.12


class StrategyError(ValueError):
    """Report strategy input or rendering that cannot be applied safely."""


class SolutionStrategy(Protocol):
    """Describe group-independent solution behavior over a prepared polygon."""

    key: StrategyKey
    requires_solution_diagram: bool

    def analyze(
        self,
        prepared: PreparedFigure,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Return exact strategy analysis verified by coordinates."""

    def render_solution_svg(
        self,
        prepared: PreparedFigure,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Return a solution diagram without changing the source polygon."""

    def build_formula(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return the exact display formula."""

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return deterministic solution prose and formula HTML."""

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the exact audited answer HTML."""


def format_number(value: Fraction, *, latex: bool = False) -> str:
    """Format an integer or half-integer using the source decimal comma."""

    if value.denominator == 1:
        return str(value.numerator)
    if value.denominator != 2:
        raise StrategyError("solution value is not an integer or half-integer")
    sign = "-" if value < 0 else ""
    whole, remainder = divmod(abs(value.numerator), 2)
    separator = "{,}" if latex else ","
    return f"{sign}{whole}{separator}{5 if remainder else 0}"


def build_answer_html(analysis: GeometryAnalysis) -> str:
    """Return the canonical numeric answer section body."""

    return f'<p><span data-effect="spaced">{format_number(analysis.area)}</span></p>'


def centered_formula_html(prose: str, formula: str) -> str:
    """Return one source-compatible paragraph and centered LaTeX formula."""

    return (
        f"<p>{prose}</p>"
        f'<center><p><span data-inline-latex="{escape(formula, quote=True)}"></span> '
        "см<sup>2</sup>.</p></center>"
    )


def svg_number(value: float) -> str:
    """Serialize one stable compact SVG coordinate."""

    rounded = round(value)
    if abs(value - rounded) < 1e-8:
        return str(rounded)
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _candidate_polygons(
    source_svg: bytes,
    *,
    vertex_count: int,
) -> tuple[ElementTree.Element, list[list[tuple[float, float]]]]:
    """Return visible SVG polygons with the required vertex count."""

    try:
        root = ElementTree.fromstring(source_svg)
    except ElementTree.ParseError as exc:
        raise StrategyError("condition SVG is not valid XML") from exc
    candidates: list[list[tuple[float, float]]] = []
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        if local_name not in {"polygon", "polyline"}:
            continue
        values = [
            float(value)
            for value in re.findall(
                r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?",
                str(element.get("points") or ""),
            )
        ]
        if len(values) % 2:
            continue
        points = list(zip(values[::2], values[1::2], strict=True))
        deduped: list[tuple[float, float]] = []
        for point in points:
            if not deduped or point != deduped[-1]:
                deduped.append(point)
        is_closed = (
            len(deduped) > 3
            and max(
                abs(deduped[0][0] - deduped[-1][0]),
                abs(deduped[0][1] - deduped[-1][1]),
            ) <= 1.0
        )
        if local_name == "polyline" and not is_closed:
            continue
        if is_closed:
            deduped.pop()
        if len(deduped) == vertex_count:
            candidates.append(deduped)
    if not candidates:
        try:
            outline = list(
                raw_outline_points_from_svg(
                    source_svg,
                    expected_vertices=vertex_count,
                )
            )
        except GridPolygonError as exc:
            raise StrategyError(
                f"condition SVG has no {vertex_count}-point polygon"
            ) from exc
        if len(outline) == vertex_count:
            candidates.append(outline)
    if not candidates:
        raise StrategyError(f"condition SVG has no {vertex_count}-point polygon")
    view_box = [
        float(value)
        for value in re.findall(r"[-+]?\d+(?:\.\d+)?", str(root.get("viewBox") or ""))
    ]
    if len(view_box) == 4:
        x, y, width, height = view_box
        candidates = [
            points
            for points in candidates
            if all(x <= px <= x + width and y <= py <= y + height for px, py in points)
        ]
    if not candidates:
        raise StrategyError("condition SVG has no visible matching polygon")
    return root, candidates


def svg_coordinate_mapper(
    source_svg: bytes,
    logical_points: tuple[tuple[int, int], ...],
) -> tuple[Callable[[tuple[int, int]], tuple[float, float]], float]:
    """Return a verified logical-grid to SVG coordinate mapper."""

    _, candidates = _candidate_polygons(source_svg, vertex_count=len(logical_points))
    logical_xmin = min(point[0] for point in logical_points)
    logical_xmax = max(point[0] for point in logical_points)
    logical_ymin = min(point[1] for point in logical_points)
    logical_ymax = max(point[1] for point in logical_points)
    if logical_xmin == logical_xmax or logical_ymin == logical_ymax:
        raise StrategyError("polygon has degenerate coordinate bounds")
    matches: list[
        tuple[float, Callable[[tuple[int, int]], tuple[float, float]], float]
    ] = []
    for candidate in candidates:
        svg_xmin = min(point[0] for point in candidate)
        svg_xmax = max(point[0] for point in candidate)
        svg_ymin = min(point[1] for point in candidate)
        svg_ymax = max(point[1] for point in candidate)
        scale_x = (svg_xmax - svg_xmin) / (logical_xmax - logical_xmin)
        scale_y = (svg_ymax - svg_ymin) / (logical_ymax - logical_ymin)
        if scale_x <= 0 or scale_y <= 0 or max(scale_x, scale_y) / min(scale_x, scale_y) > 1.08:
            continue
        tolerance = max(scale_x, scale_y) * LEGACY_GRID_RENDER_TOLERANCE
        for invert_y in (False, True):
            def mapper(
                point: tuple[int, int],
                *,
                invert: bool = invert_y,
                sxmin: float = svg_xmin,
                symin: float = svg_ymin,
                symax: float = svg_ymax,
                sx: float = scale_x,
                sy: float = scale_y,
            ) -> tuple[float, float]:
                """Map one logical point for the candidate orientation."""

                y_offset = point[1] - logical_ymin
                return (
                    sxmin + (point[0] - logical_xmin) * sx,
                    symax - y_offset * sy if invert else symin + y_offset * sy,
                )

            expected = tuple(mapper(point) for point in logical_points)
            if not any(
                all(
                    max(abs(ex - ax), abs(ey - ay)) <= tolerance
                    for (ex, ey), (ax, ay) in zip(expected, ordering, strict=True)
                )
                for ordering in permutations(candidate)
            ):
                continue
            area = (svg_xmax - svg_xmin) * (svg_ymax - svg_ymin)
            matches.append((area, mapper, min(scale_x, scale_y)))
    if not matches:
        raise StrategyError("condition SVG polygon and prepared coordinates disagree")
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1], matches[0][2]


def append_solution_construction(source_svg: bytes, lines: list[str]) -> bytes:
    """Append one red construction group to an otherwise unchanged SVG."""

    text = source_svg.decode("utf-8")
    if 'id="solution-construction"' in text:
        raise StrategyError("condition SVG already contains a generated construction")
    group = (
        f'<g id="solution-construction" fill="none" stroke="{RED_STROKE}" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">\n'
        + "\n".join(lines)
        + "\n</g>"
    )
    closing = text.rfind("</svg>")
    if closing < 0:
        raise StrategyError("condition SVG has no closing svg tag")
    result = (text[:closing].rstrip() + "\n" + group + "\n</svg>\n").encode()
    ElementTree.fromstring(result)
    return result
