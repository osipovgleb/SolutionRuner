"""Solve annulus area from one task-local known circle area and radius ratio."""

from __future__ import annotations

from fractions import Fraction

from ..models import GeometryAnalysis, GroupProfile, PreparedGridRing
from .protocol import (
    StrategyError,
    centered_formula_html,
)


def _format_ratio(value: Fraction) -> str:
    """Render one exact radius ratio without restricting its denominator."""

    if value.denominator == 1:
        return str(value.numerator)
    return rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def _format_area(value: Fraction, *, latex: bool = False) -> str:
    """Render one exact terminating decimal using the source decimal comma."""

    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise StrategyError("solution area is not a terminating decimal")
    places = max(twos, fives)
    scaled = abs(value.numerator) * (10**places // value.denominator)
    sign = "-" if value < 0 else ""
    if places == 0:
        return f"{sign}{scaled}"
    power = 10**places
    whole, remainder = divmod(scaled, power)
    digits = f"{remainder:0{places}d}".rstrip("0")
    separator = "{,}" if latex else ","
    return f"{sign}{whole}{separator}{digits}"


class AnnulusFromKnownAreaStrategy:
    """Derive the shaded area from the detected known circle and exact radii."""

    key = "annulus-from-known-area"
    requires_solution_diagram = False

    def analyze(
        self,
        prepared: PreparedGridRing,
        profile: GroupProfile,
    ) -> GeometryAnalysis:
        """Calculate the ring area after validating all task-local evidence."""

        if (
            not isinstance(prepared, PreparedGridRing)
            or profile.geometry_kind != "ring"
            or profile.strategy_key != self.key
        ):
            raise StrategyError("known-area annulus strategy/profile mismatch")
        if prepared.known_circle_area not in {"inner", "outer"}:
            raise StrategyError("known circle area was not detected")
        if prepared.given_circle_area is None or prepared.given_circle_area <= 0:
            raise StrategyError("known circle area value is invalid")
        outer_squared = prepared.outer_radius_squared
        inner_squared = prepared.inner_radius_squared
        if not 0 < inner_squared < outer_squared:
            raise StrategyError("annulus radii are invalid")
        ratio = Fraction(outer_squared, inner_squared)
        given = prepared.given_circle_area
        if prepared.known_circle_area == "inner":
            inner_area = given
            outer_area = given * ratio
        else:
            outer_area = given
            inner_area = given / ratio
        area = outer_area - inner_area
        if area <= 0:
            raise StrategyError("derived annulus area is invalid")
        return GeometryAnalysis(
            area=area,
            area_by_coordinates=area,
            details={
                "outer_radius_squared": outer_squared,
                "inner_radius_squared": inner_squared,
                "radius_area_ratio": ratio,
                "known_circle_area": prepared.known_circle_area,
                "given_circle_area": given,
                "outer_circle_area": outer_area,
                "inner_circle_area": inner_area,
                "ring_alignment": prepared.ring_alignment,
            },
        )

    def render_solution_svg(
        self,
        prepared: PreparedGridRing,
        analysis: GeometryAnalysis,
    ) -> bytes:
        """Return original bytes because the parent-style solution has no diagram."""

        return prepared.condition_svg_path.read_bytes()

    def build_formula(self, analysis: GeometryAnalysis, profile: GroupProfile) -> str:
        """Return the final subtraction formula for the detected known side."""

        outer_area = _format_area(analysis.details["outer_circle_area"], latex=True)
        inner_area = _format_area(analysis.details["inner_circle_area"], latex=True)
        area = _format_area(analysis.area, latex=True)
        return rf"S={outer_area}-{inner_area}={area}"

    def build_solution_html(
        self,
        analysis: GeometryAnalysis,
        profile: GroupProfile,
    ) -> str:
        """Return concise parent-style ratio, derived circle area, and subtraction."""

        outer_squared = int(analysis.details["outer_radius_squared"])
        inner_squared = int(analysis.details["inner_radius_squared"])
        ratio = analysis.details["radius_area_ratio"]
        ratio_formula = (
            rf"\frac{{R^2}}{{r^2}}=\frac{{{outer_squared}}}{{{inner_squared}}}="
            f"{_format_ratio(ratio)}"
        )
        known_side = analysis.details["known_circle_area"]
        given = _format_area(analysis.details["given_circle_area"], latex=True)
        if known_side == "inner":
            derived = _format_area(analysis.details["outer_circle_area"], latex=True)
            derived_prose = "Поэтому площадь внешнего круга равна"
            derived_formula = rf"S_{{\text{{внеш.}}}}={given}\cdot {_format_ratio(ratio)}={derived}"
        else:
            derived = _format_area(analysis.details["inner_circle_area"], latex=True)
            derived_prose = "Поэтому площадь внутреннего круга равна"
            derived_formula = rf"S_{{\text{{внутр.}}}}={given}:{_format_ratio(ratio)}={derived}"
        return (
            centered_formula_html(
                "Площади кругов относятся как квадраты их радиусов.",
                ratio_formula,
            )
            + centered_formula_html(derived_prose, derived_formula)
            + centered_formula_html(
                "Площадь кольца равна разности площадей внешнего и внутреннего кругов. Поэтому",
                self.build_formula(analysis, profile),
            )
        )

    def build_answer_html(self, analysis: GeometryAnalysis) -> str:
        """Return the exact shaded annulus area."""

        return f'<p><span data-effect="spaced">{_format_area(analysis.area)}</span></p>'
