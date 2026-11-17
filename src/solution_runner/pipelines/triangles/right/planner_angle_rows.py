"""Build exact solution rows for right-triangle problems."""

from __future__ import annotations

from fractions import Fraction

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .planner_conditions import (
    _acute_condition_angles,
    _plain_html,
    _require_condition_terms,
    _single_acute_angle,
    _single_line_angle,
)
from .planner_notation import _answer_text, _number_latex


def _median_angle_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find ACD from angle B and the hypotenuse median CD."""

    visible = _require_condition_terms(condition_html, "медиан", "найдите", "acd")
    if "cd" not in visible.lower() or "угол b" not in visible.lower():
        raise RightTrianglePlanError("condition must give angle B and median CD")
    angle = _single_acute_angle(condition_html)
    answer = 90 - angle
    return str(answer), [
        "CD=AD=BD",
        (
            rf"\angle ACD=\angle A=90^{{\circ}}-\angle B="
            rf"90^{{\circ}}-{angle}^{{\circ}}={answer}^{{\circ}}"
        ),
    ]


def _bisector_intersection_angle_rows(
    condition_html: str,
) -> tuple[str, list[str]]:
    """Find the acute angle between the acute- and right-angle bisectors."""

    _require_condition_terms(condition_html, "биссектрис", "прям", "образован")
    angle = _single_acute_angle(condition_html)
    answer = Fraction(90 + angle, 2)
    answer_text = _answer_text(float(answer))
    answer_latex = _number_latex(answer)
    return answer_text, [
        (
            rf"\varphi=45^{{\circ}}+\frac{{{angle}^{{\circ}}}}{{2}}="
            rf"{answer_latex}^{{\circ}}"
        )
    ]


def _altitude_bisector_angle_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find the angle between a right-vertex altitude and bisector."""

    visible = _plain_html(condition_html).lower()
    if "высот" not in visible or "биссектрис" not in visible or "медиан" in visible:
        raise RightTrianglePlanError(
            "condition must request the altitude and bisector angle"
        )
    angle = _single_acute_angle(condition_html)
    answer = abs(angle - 45)
    return str(answer), [
        (
            rf"\varphi=\left|{angle}^{{\circ}}-45^{{\circ}}\right|="
            rf"{answer}^{{\circ}}"
        )
    ]


def _inverse_45_degree_rows(
    condition_html: str,
    *,
    first_term: str,
    second_term: str,
) -> tuple[str, list[str]]:
    """Recover the smaller acute angle from a bisector-based line angle."""

    visible = _require_condition_terms(
        condition_html,
        first_term,
        second_term,
        "меньш",
    )
    if "между" not in visible.lower():
        raise RightTrianglePlanError("condition must give an angle between two lines")
    line_angle = _single_line_angle(condition_html)
    answer = 45 - line_angle
    if answer <= 0:
        raise RightTrianglePlanError("line angle must be less than 45 degrees")
    return str(answer), [
        (
            rf"\alpha_{{\min}}=45^{{\circ}}-{line_angle}^{{\circ}}="
            rf"{answer}^{{\circ}}"
        )
    ]


def _altitude_bisector_inverse_rows(condition_html: str) -> tuple[str, list[str]]:
    """Recover the smaller acute angle from altitude-bisector separation."""

    return _inverse_45_degree_rows(
        condition_html,
        first_term="высот",
        second_term="биссектрис",
    )


def _altitude_line_angle_rows(condition_html: str) -> tuple[str, list[str]]:
    """Handle the audited altitude-median or altitude-bisector forward branch."""

    visible = _require_condition_terms(condition_html, "высот")
    lowered = visible.lower()
    angles = _acute_condition_angles(condition_html)
    if "медиан" in lowered and "биссектрис" not in lowered:
        if len(angles) == 1:
            larger = max(angles[0], 90 - angles[0])
            smaller = min(angles[0], 90 - angles[0])
        elif len(angles) == 2 and sum(angles) == 90:
            larger, smaller = max(angles), min(angles)
        else:
            raise RightTrianglePlanError(
                "altitude-median condition must determine both acute angles"
            )
        answer = larger - smaller
        return str(answer), [
            (
                rf"\varphi=\left|{larger}^{{\circ}}-{smaller}^{{\circ}}\right|="
                rf"{answer}^{{\circ}}"
            )
        ]
    if "биссектрис" in lowered and "медиан" not in lowered:
        angle = max(angles)
        answer = abs(angle - 45)
        return str(answer), [
            (
                rf"\varphi=\left|{angle}^{{\circ}}-45^{{\circ}}\right|="
                rf"{answer}^{{\circ}}"
            )
        ]
    raise RightTrianglePlanError(
        "condition must request altitude with either median or bisector"
    )


def _altitude_median_inverse_rows(condition_html: str) -> tuple[str, list[str]]:
    """Recover the larger acute angle from altitude-median separation."""

    _require_condition_terms(condition_html, "высот", "медиан", "больш")
    line_angle = _single_line_angle(condition_html)
    answer = Fraction(90 + line_angle, 2)
    answer_text = _answer_text(float(answer))
    answer_latex = _number_latex(answer)
    return answer_text, [
        (
            rf"\alpha_{{\max}}=\frac{{90^{{\circ}}+{line_angle}^{{\circ}}}}{{2}}="
            rf"{answer_latex}^{{\circ}}"
        )
    ]


def _bisector_median_angle_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find the angle between a right-vertex bisector and median."""

    _require_condition_terms(condition_html, "биссектрис", "медиан")
    angles = _acute_condition_angles(condition_html)
    if len(angles) == 1:
        angle = angles[0]
    elif len(angles) == 2 and sum(angles) == 90:
        angle = max(angles)
    else:
        raise RightTrianglePlanError("condition must determine one acute angle")
    answer = abs(angle - 45)
    return str(answer), [
        (
            rf"\varphi=\left|{angle}^{{\circ}}-45^{{\circ}}\right|="
            rf"{answer}^{{\circ}}"
        )
    ]


def _bisector_median_inverse_rows(condition_html: str) -> tuple[str, list[str]]:
    """Recover the smaller acute angle from bisector-median separation."""

    return _inverse_45_degree_rows(
        condition_html,
        first_term="биссектрис",
        second_term="медиан",
    )
