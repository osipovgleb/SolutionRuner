"""Solve lattice annulus area tasks from verified squared radii."""

from __future__ import annotations

from fractions import Fraction
from html import escape
from math import hypot

from ..models import GeometryAnalysis, GroupProfile, PreparedGridRing, SolutionDiagramSpec
from .protocol import (
    StrategyError,
    append_solution_construction,
    build_answer_html,
    svg_number,
)


SOLUTION_ASSET_KEY = "generated_solution_diagram"


def _radius_legs(
    center: tuple[int, int],
    point: tuple[int, int],
    radius_squared: int,
) -> tuple[int, int]:
    """Return the non-negative lattice legs represented by one circle point."""

    legs = abs(point[0] - center[0]), abs(point[1] - center[1])
    if legs[0] * legs[0] + legs[1] * legs[1] != radius_squared:
        raise StrategyError("ring lattice point disagrees with its squared radius")
    return legs


def _formula_html(formula: str) -> str:
    """Return one source-compatible centered formula without an added unit."""

    return (
        '<center><p><span data-inline-latex="'
        + escape(formula, quote=True)
        + '"></span>.</p></center>'
    )


def _radius_explanation_html(
    *,
    radius_index: int,
    circle_name: str,
    legs: tuple[int, int],
    radius_squared: int,
) -> str:
    """Explain one direct or Pythagorean lattice-radius calculation."""

    horizontal, vertical = legs
    if horizontal and vertical:
        prose = (
            "По теореме Пифагора квадрат радиуса "
            f"{circle_name} круга равен"
        )
        formula = (
            rf"R_{radius_index}^2={horizontal}^2+{vertical}^2="
            f"{radius_squared}"
        )
    else:
        radius = max(horizontal, vertical)
        prose = f"Радиус {circle_name} круга равен {radius}, поэтому"
        formula = rf"R_{radius_index}^2={radius}^2={radius_squared}"
    return f"<p>{prose}</p>" + _formula_html(formula)


class AnnulusAreaStrategy:
    """Compute S/pi and render two labelled radii without changing the ring."""

    key = "annulus-area"
    requires_solution_diagram = True

    def analyze(
        self,
        prepared: PreparedGridRing,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Verify both squared radii from their independent lattice points."""

        if not isinstance(prepared, PreparedGridRing) or profile.geometry_kind != "ring":
            raise StrategyError("annulus strategy requires a prepared grid ring")
        cx, cy = prepared.center
        outer_legs = _radius_legs(
            prepared.center,
            prepared.outer_point,
            prepared.outer_radius_squared,
        )
        inner_legs = _radius_legs(
            prepared.center,
            prepared.inner_point,
            prepared.inner_radius_squared,
        )
        outer_by_point = outer_legs[0] ** 2 + outer_legs[1] ** 2
        inner_by_point = inner_legs[0] ** 2 + inner_legs[1] ** 2
        if outer_by_point != prepared.outer_radius_squared:
            raise StrategyError("outer lattice point disagrees with squared radius")
        if inner_by_point != prepared.inner_radius_squared:
            raise StrategyError("inner lattice point disagrees with squared radius")
        if inner_by_point >= outer_by_point:
            raise StrategyError("annulus radii are invalid")
        area = Fraction(outer_by_point - inner_by_point)
        return GeometryAnalysis(
            area=area,
            area_by_coordinates=area,
            details={
                "outer_radius_squared": outer_by_point,
                "inner_radius_squared": inner_by_point,
                "outer_radius_legs": outer_legs,
                "inner_radius_legs": inner_legs,
            },
        )

    def render_solution_svg(
        self,
        prepared: PreparedGridRing,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Append two labelled radius segments to the unchanged condition SVG."""

        source = prepared.condition_svg_path.read_bytes()
        try:
            center_x, center_y = (
                float(value) for value in prepared.converter_diagnostics["svg_center"]
            )
            outer_radius = float(prepared.converter_diagnostics["svg_outer_radius"])
            inner_radius = float(prepared.converter_diagnostics["svg_inner_radius"])
            cell_size = float(prepared.converter_diagnostics["grid_cell_size"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StrategyError("prepared ring has no SVG-space radius evidence") from exc
        outer_legs = tuple(int(value) for value in analysis.details["outer_radius_legs"])
        inner_legs = tuple(int(value) for value in analysis.details["inner_radius_legs"])
        for name, legs, svg_radius in (
            ("outer", outer_legs, outer_radius),
            ("inner", inner_legs, inner_radius),
        ):
            measured = hypot(*legs) * cell_size
            if abs(measured - svg_radius) > max(0.5, cell_size * 0.05):
                raise StrategyError(f"{name} radius point disagrees with SVG geometry")

        lines: list[str] = []
        for name, legs, x_sign, y_sign in (
            ("outer", outer_legs, 1, -1),
            ("inner", inner_legs, -1, 1),
        ):
            endpoint_x = center_x + x_sign * legs[0] * cell_size
            endpoint_y = center_y + y_sign * legs[1] * cell_size
            lines.append(
                f'  <line data-kind="radius" data-radius="{name}" '
                f'x1="{svg_number(center_x)}" y1="{svg_number(center_y)}" '
                f'x2="{svg_number(endpoint_x)}" y2="{svg_number(endpoint_y)}" />'
            )
            if legs[0] and legs[1]:
                projection_x = endpoint_x
                projection_y = center_y
                lines.extend(
                    (
                        f'  <line data-kind="pythagorean-leg" data-radius="{name}" '
                        f'x1="{svg_number(center_x)}" y1="{svg_number(center_y)}" '
                        f'x2="{svg_number(projection_x)}" y2="{svg_number(projection_y)}" '
                        'stroke-dasharray="5 4" />',
                        f'  <line data-kind="pythagorean-leg" data-radius="{name}" '
                        f'x1="{svg_number(projection_x)}" y1="{svg_number(projection_y)}" '
                        f'x2="{svg_number(endpoint_x)}" y2="{svg_number(endpoint_y)}" '
                        'stroke-dasharray="5 4" />',
                    )
                )
        return append_solution_construction(source, lines)

    def render_solution_diagrams(
        self,
        prepared: PreparedGridRing,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> tuple[SolutionDiagramSpec, ...]:
        """Return one explicitly labelled solution diagram."""

        outer = int(analysis.details["outer_radius_squared"])
        inner = int(analysis.details["inner_radius_squared"])
        return (
            SolutionDiagramSpec(
                asset_key=SOLUTION_ASSET_KEY,
                solution_variant_index=0,
                svg_bytes=self.render_solution_svg(prepared, analysis),
                alt_text=f"Кольцо: R₁²={outer}, R₂²={inner}",
            ),
        )

    def build_formula(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return the parent-style annulus formula and requested quotient."""

        outer = int(analysis.details["outer_radius_squared"])
        inner = int(analysis.details["inner_radius_squared"])
        area = int(analysis.area)
        return rf"S=\pi R_1^2-\pi R_2^2=\pi({outer}-{inner})={area}\pi"

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return concise prose and the exact annulus-area calculation."""

        return (
            _radius_explanation_html(
                radius_index=1,
                circle_name="большого",
                legs=tuple(int(value) for value in analysis.details["outer_radius_legs"]),
                radius_squared=int(analysis.details["outer_radius_squared"]),
            )
            + _radius_explanation_html(
                radius_index=2,
                circle_name="малого",
                legs=tuple(int(value) for value in analysis.details["inner_radius_legs"]),
                radius_squared=int(analysis.details["inner_radius_squared"]),
            )
            + "<p>Площадь кольца равна разности площадей большого и малого кругов, откуда</p>"
            + _formula_html(self.build_formula(analysis, profile))
            + "<p>Поэтому</p>"
            + _formula_html(rf"\frac{{S}}{{\pi}}={int(analysis.area)}")
        )

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the exact value of S divided by pi."""

        return build_answer_html(analysis)
