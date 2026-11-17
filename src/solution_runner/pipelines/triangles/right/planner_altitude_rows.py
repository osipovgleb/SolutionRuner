"""Build exact solution rows for right-triangle problems."""

from __future__ import annotations

from fractions import Fraction

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .planner_conditions import (
    _angle_a_and_hypotenuse,
    _latin_triangle_labels,
    _require_condition_terms,
)
from .planner_notation import _answer_text, _number_latex


def _altitude_length_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find CH from AB and a 30- or 60-degree acute angle."""

    visible = _require_condition_terms(condition_html, "найдите", "высот", "ch")
    if "ah" in visible.lower() or "bh" in visible.lower():
        raise RightTrianglePlanError("condition must request CH")
    angle, coefficient, radical, ab_latex = _angle_a_and_hypotenuse(condition_html)
    if not radical:
        raise RightTrianglePlanError(
            "altitude-length condition must give AB as k sqrt(3)"
        )
    answer = Fraction(3 * coefficient, 4)
    sin_latex = r"\frac{1}{2}" if angle == 30 else r"\frac{\sqrt{3}}{2}"
    cos_latex = r"\frac{\sqrt{3}}{2}" if angle == 30 else r"\frac{1}{2}"
    return _answer_text(float(answer)), [
        rf"CH=AB\sin A\cos A={ab_latex}\cdot{sin_latex}\cdot{cos_latex}="
        + _number_latex(answer)
    ]


def _projection_rows(
    condition_html: str,
    *,
    requested: str,
) -> tuple[str, list[str]]:
    """Find one hypotenuse projection from AB and angle A."""

    visible = _require_condition_terms(
        condition_html, "высот", "найдите", requested.lower()
    )
    if requested not in _latin_triangle_labels(visible).upper():
        raise RightTrianglePlanError(f"condition must request {requested}")
    angle, ab, radical, ab_latex = _angle_a_and_hypotenuse(condition_html)
    if radical:
        raise RightTrianglePlanError("projection condition must give integer AB")
    if requested == "AH":
        factor = Fraction(3, 4) if angle == 30 else Fraction(1, 4)
        trig_latex = r"\frac{\sqrt{3}}{2}" if angle == 30 else r"\frac{1}{2}"
        trig_name = "cos"
    else:
        factor = Fraction(1, 4) if angle == 30 else Fraction(3, 4)
        trig_latex = r"\frac{1}{2}" if angle == 30 else r"\frac{\sqrt{3}}{2}"
        trig_name = "sin"
    answer = ab * factor
    return _answer_text(float(answer)), [
        (
            rf"{requested}=AB\{trig_name}^{{2}}A={ab_latex}\cdot"
            rf"\left({trig_latex}\right)^{{2}}={_number_latex(answer)}"
        )
    ]


def _hypotenuse_projection_ah_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find projection AH on the hypotenuse."""

    return _projection_rows(condition_html, requested="AH")


def _hypotenuse_projection_bh_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find projection BH on the hypotenuse."""

    return _projection_rows(condition_html, requested="BH")
