"""Build verified content repairs from one schema-v3 right-triangle problem."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from html import unescape
import math
import re
from typing import Any
import unicodedata

from solution_runner.pipelines.core.errors import ContentPlanError as RightTrianglePlanError

from .altitude_solver import (
    AltitudeSolveError,
    answer_matches as altitude_answer_matches,
    solve_altitude_condition,
)


_ALTITUDE_CONTENT_VERSION = "10"


@dataclass(frozen=True)
class RepairPlan:
    """Describe the minimal durable transformations for one source problem."""

    answer: str
    transformations: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class UniversalRightTriangleValues:
    """Hold one condition normalized to side roles around an acute angle."""

    right_angle: str
    trig_name: str
    trig_angle: str
    trig_latex: str
    known_side: str
    known_latex: str
    requested_side: str
    hypotenuse: str
    numerator_side: str
    denominator_side: str


@dataclass(frozen=True)
class UniversalTrigRequestValues:
    """Hold a condition that asks for a trig value from two known sides."""

    right_angle: str
    trig_name: str
    trig_angle: str
    known_sides: tuple[tuple[str, str], tuple[str, str]]
    hypotenuse: str
    numerator_side: str
    denominator_side: str


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Return the unique normalized section with the canonical key."""

    matches = [
        section
        for section in content.get("sections", [])
        if isinstance(section, dict) and section.get("key") == key
    ]
    if len(matches) > 1:
        raise RightTrianglePlanError(f"multiple {key} sections")
    return matches[0] if matches else None


def _plain_html(value: str) -> str:
    """Return Unicode-normalized visible text for deterministic rule matching."""

    normalized = unicodedata.normalize("NFKC", unescape(value)).replace("\u00ad", "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", normalized)).strip()


def _latin_triangle_labels(value: str) -> str:
    """Normalize visually identical Cyrillic triangle labels to Latin names."""

    return value.translate(str.maketrans({"А": "A", "В": "B", "С": "C"}))


def _opposite_side(vertex: str) -> str:
    """Return the side opposite one ABC vertex."""

    return {"A": "BC", "B": "AC", "C": "AB"}[vertex]


def _normalized_trig_formula(value: str) -> str:
    """Normalize supported source aliases to the project's sin/cos/tg/ctg names."""

    normalized = _latin_triangle_labels(value).replace(" ", "")
    return (
        normalized.replace(r"\operatorname{tg}", r"\tg")
        .replace(r"\operatorname{ctg}", r"\ctg")
        .replace(r"\tan", r"\tg")
        .replace(r"\cot", r"\ctg")
    )


def _right_angle_labels(visible: str, values: list[str]) -> list[str]:
    """Return the declared right-angle label across supported source layouts."""

    direct = re.findall(r"угол\s+([ABC])\s+равен\s+90", visible, re.IGNORECASE)
    if direct:
        return [label.upper() for label in direct]
    if any(re.fullmatch(r"90(?:\^\{?\\circ\}?)?", value) for value in values):
        split = re.findall(r"угол\s+([ABC])\s+равен\b", visible, re.IGNORECASE)
        if split:
            return [label.upper() for label in split]
    return [
        match.group(1).upper()
        for value in values
        if (
            match := re.fullmatch(
                r"(?:\\angle)?([ABC])=90(?:\^\{?\\circ\}?)?",
                value,
            )
        )
        is not None
    ]


def _universal_values(condition_html: str) -> UniversalRightTriangleValues:
    """Extract and normalize one right-angle, trig value, side, and request."""

    values = [
        _normalized_trig_formula(value)
        for value in re.findall(
            r'data-inline-latex="([^"]+)"',
            unescape(condition_html),
        )
    ]
    trig_values: list[tuple[str, str, str]] = []
    known_values: list[tuple[str, str]] = []
    for value in values:
        trig = re.fullmatch(r"\\(sin|cos|tg|ctg)([ABC])=(.+)", value)
        if trig is not None:
            trig_values.append((trig.group(1), trig.group(2), trig.group(3)))
            continue
        known = re.fullmatch(r"(AB|AC|BC)=(.+)", value)
        if known is not None:
            known_values.append((known.group(1), known.group(2)))

    visible = _latin_triangle_labels(_plain_html(condition_html))
    if not known_values:
        plain_known = re.search(
            r"\b(AB|AC|BC)\s*=\s*(\d+(?:[,.]\d+)?)",
            visible,
        )
        if plain_known is not None:
            known_values.append(
                (
                    plain_known.group(1),
                    plain_known.group(2).replace(",", "{,}"),
                )
            )
    right = _right_angle_labels(visible, values)
    requested_match = re.search(r"Найдите\s+(AB|AC|BC)\b", visible, re.IGNORECASE)
    latex_requested = next((value for value in values if value in {"AB", "AC", "BC"}), None)
    requested = requested_match.group(1) if requested_match is not None else latex_requested
    if len(right) != 1:
        raise RightTrianglePlanError("condition must declare one right angle")
    if len(trig_values) != 1:
        raise RightTrianglePlanError("condition must declare one sin, cos, tg, or ctg value")
    if len(known_values) != 1:
        raise RightTrianglePlanError("condition must declare one known side")
    if requested is None:
        raise RightTrianglePlanError("condition must request AB, AC, or BC")

    right_angle = right[0].upper()
    trig_name, trig_angle, trig_latex = trig_values[0]
    known_side, known_latex = known_values[0]
    requested = requested.upper()
    if trig_angle == right_angle:
        raise RightTrianglePlanError("trigonometric angle must be acute")
    if known_side == requested:
        raise RightTrianglePlanError("known and requested sides must differ")

    hypotenuse = _opposite_side(right_angle)
    opposite = _opposite_side(trig_angle)
    if opposite == hypotenuse:
        raise RightTrianglePlanError("trigonometric angle must be acute")
    adjacent_candidates = {"AB", "AC", "BC"} - {hypotenuse, opposite}
    if len(adjacent_candidates) != 1:
        raise RightTrianglePlanError("right-triangle side roles are ambiguous")
    adjacent = adjacent_candidates.pop()
    numerator_side, denominator_side = {
        "sin": (opposite, hypotenuse),
        "cos": (adjacent, hypotenuse),
        "tg": (opposite, adjacent),
        "ctg": (adjacent, opposite),
    }[trig_name]
    return UniversalRightTriangleValues(
        right_angle=right_angle,
        trig_name=trig_name,
        trig_angle=trig_angle,
        trig_latex=trig_latex,
        known_side=known_side,
        known_latex=known_latex,
        requested_side=requested,
        hypotenuse=hypotenuse,
        numerator_side=numerator_side,
        denominator_side=denominator_side,
    )


def _universal_trig_request_values(
    condition_html: str,
) -> UniversalTrigRequestValues | None:
    """Extract a request for one trig value from exactly two known sides."""

    values = [
        _normalized_trig_formula(value)
        for value in re.findall(
            r'data-inline-latex="([^"]+)"',
            unescape(condition_html),
        )
    ]
    requested = [
        (match.group(1), match.group(2))
        for value in values
        if (match := re.fullmatch(r"\\(sin|cos|tg|ctg)([ABC])", value))
        is not None
    ]
    if not requested:
        return None
    known = [
        (match.group(1), match.group(2))
        for value in values
        if (match := re.fullmatch(r"(AB|AC|BC)=(.+)", value)) is not None
    ]
    visible = _latin_triangle_labels(_plain_html(condition_html))
    right = _right_angle_labels(visible, values)
    if len(right) != 1:
        raise RightTrianglePlanError("condition must declare one right angle")
    if len(requested) != 1:
        raise RightTrianglePlanError("condition must request one sin, cos, tg, or ctg value")
    if len(known) != 2 or len({side for side, _ in known}) != 2:
        raise RightTrianglePlanError("trig request must declare two distinct known sides")

    right_angle = right[0].upper()
    trig_name, trig_angle = requested[0]
    if trig_angle == right_angle:
        raise RightTrianglePlanError("trigonometric angle must be acute")
    hypotenuse = _opposite_side(right_angle)
    opposite = _opposite_side(trig_angle)
    if opposite == hypotenuse:
        raise RightTrianglePlanError("trigonometric angle must be acute")
    adjacent = ({"AB", "AC", "BC"} - {hypotenuse, opposite}).pop()
    numerator_side, denominator_side = {
        "sin": (opposite, hypotenuse),
        "cos": (adjacent, hypotenuse),
        "tg": (opposite, adjacent),
        "ctg": (adjacent, opposite),
    }[trig_name]
    return UniversalTrigRequestValues(
        right_angle=right_angle,
        trig_name=trig_name,
        trig_angle=trig_angle,
        known_sides=(known[0], known[1]),
        hypotenuse=hypotenuse,
        numerator_side=numerator_side,
        denominator_side=denominator_side,
    )


def _latex_values(condition_html: str) -> tuple[str, str, str, str, str]:
    """Extract one trig value plus the exact known/requested side rule."""

    values = re.findall(r'data-inline-latex="([^"]+)"', unescape(condition_html))
    trig_values = [
        (name, value.removeprefix(prefix))
        for name, prefix in (
            ("sin", r"\sin A="),
            ("cos", r"\cos A="),
            ("tg", r"\tg A="),
        )
        for value in values
        if value.startswith(prefix)
    ]
    known = next(
        (value for value in values if value.startswith("AC=") or value.startswith("AB=")),
        None,
    )
    visible = _plain_html(condition_html)
    visible = re.sub(r"\bАС\b", "AC", visible)
    visible = re.sub(r"\bАВ\b", "AB", visible)
    if known is None:
        plain_side = re.search(r"\b(AC|AB)\s*=\s*(\d+(?:[,.]\d+)?)", visible)
        if plain_side is not None:
            known = f"{plain_side.group(1)}={plain_side.group(2).replace(',', '{,}')}"
    requested_match = re.search(r"Найдите\s+(AC|AB|BC)\b", visible)
    latex_requested = next(
        (value for value in values if value in {"AC", "AB", "BC"}),
        None,
    )
    if len(trig_values) != 1 or known is None:
        raise RightTrianglePlanError(
            "condition must declare one sin A, cos A, or tg A and a known side"
        )
    requested = requested_match.group(1) if requested_match is not None else latex_requested
    if requested is None:
        raise RightTrianglePlanError("condition must request AC, AB, or BC")
    known_side = known[:2]
    return (
        trig_values[0][0],
        trig_values[0][1],
        known_side,
        known.removeprefix("AC=").removeprefix("AB="),
        requested,
    )


def _trig_square(value: str) -> Fraction:
    """Parse one squared trig value from supported exact LaTeX forms."""

    fraction = re.fullmatch(r"\\frac\{(\d+)\}\{(\d+)\}", value)
    if fraction is not None:
        parsed = Fraction(int(fraction.group(1)), int(fraction.group(2)))
        return parsed * parsed
    decimal = re.fullmatch(r"(\d+)\{,\}(\d+)", value)
    if decimal is not None:
        parsed = Fraction(f"{decimal.group(1)}.{decimal.group(2)}")
        return parsed * parsed
    denominator_radical = re.fullmatch(
        r"\\frac\{(\d+)\}\{(?:(\d+))?\\sqrt\{(\d+)\}\}",
        value,
    )
    if denominator_radical is not None:
        numerator = int(denominator_radical.group(1))
        coefficient = int(denominator_radical.group(2) or "1")
        radicand = int(denominator_radical.group(3))
        return Fraction(
            numerator * numerator,
            coefficient * coefficient * radicand,
        )
    radical = re.fullmatch(
        r"\\frac\{(?:(\d+))?\\sqrt\{(\d+)\}\}\{(\d+)\}",
        value,
    )
    if radical is not None:
        coefficient = int(radical.group(1) or "1")
        return Fraction(
            coefficient * coefficient * int(radical.group(2)),
            int(radical.group(3)) ** 2,
        )
    raise RightTrianglePlanError(
        "sin A or cos A must be rational or a square-root fraction"
    )


def _fraction_latex(value: Fraction) -> str:
    """Render one reduced rational value as an ordinary LaTeX fraction."""

    return rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def _positive_root_latex(square: Fraction) -> str:
    """Render the positive root of one exact rational square."""

    numerator = square.numerator
    denominator = square.denominator
    root_numerator = math.isqrt(numerator)
    root_denominator = math.isqrt(denominator)
    if root_numerator * root_numerator == numerator and root_denominator * root_denominator == denominator:
        reduced = Fraction(root_numerator, root_denominator)
        return rf"\frac{{{reduced.numerator}}}{{{reduced.denominator}}}"
    if root_denominator * root_denominator == denominator:
        square_factor = math.isqrt(numerator)
        while square_factor > 1 and numerator % (square_factor * square_factor):
            square_factor -= 1
        remainder = numerator // (square_factor * square_factor)
        radical = (
            str(square_factor)
            if remainder == 1
            else ("" if square_factor == 1 else str(square_factor))
            + rf"\sqrt{{{remainder}}}"
        )
        return (
            radical
            if root_denominator == 1
            else rf"\frac{{{radical}}}{{{root_denominator}}}"
        )
    radicand = numerator * denominator
    root = math.isqrt(radicand)
    if root * root == radicand:
        reduced = Fraction(root, denominator)
        return rf"\frac{{{reduced.numerator}}}{{{reduced.denominator}}}"
    square_factor = root
    while square_factor > 1 and radicand % (square_factor * square_factor):
        square_factor -= 1
    remainder = radicand // (square_factor * square_factor)
    common = math.gcd(square_factor, denominator)
    coefficient = square_factor // common
    reduced_denominator = denominator // common
    radical = ("" if coefficient == 1 else str(coefficient)) + rf"\sqrt{{{remainder}}}"
    return (
        radical
        if reduced_denominator == 1
        else rf"\frac{{{radical}}}{{{reduced_denominator}}}"
    )


def _canonical_trig_latex(value: str) -> str:
    """Return a reduced fraction for rational trig values and preserve radicals."""

    fraction = re.fullmatch(r"\\frac\{(\d+)\}\{(\d+)\}", value)
    if fraction is not None:
        return _fraction_latex(Fraction(int(fraction.group(1)), int(fraction.group(2))))
    decimal = re.fullmatch(r"(\d+)\{,\}(\d+)", value)
    if decimal is not None:
        return _fraction_latex(
            Fraction(
                int(decimal.group(1) + decimal.group(2)),
                10 ** len(decimal.group(2)),
            )
        )
    return value


def _decimal_reduction_latex(trig_name: str, value: str) -> str | None:
    """Render the required decimal-to-reduced-fraction row when applicable."""

    decimal = re.fullmatch(r"(\d+)\{,\}(\d+)", value)
    if decimal is None:
        return None
    numerator = int(decimal.group(1) + decimal.group(2))
    denominator = 10 ** len(decimal.group(2))
    reduced = _fraction_latex(Fraction(numerator, denominator))
    return (
        rf"\{trig_name} A={value}="
        rf"\frac{{{numerator}}}{{{denominator}}}={reduced}"
    )


def _is_pipeline_verbose_solution(value: str) -> bool:
    """Recognize only the mechanical multi-row solution emitted by this runner."""

    if 'data-content-kind="solution"' not in value:
        return False
    formulas = re.findall(r'data-inline-latex="([^"]+)"', unescape(value))
    if r"\cos^2 A=1-\sin^2 A" in formulas:
        return True
    return (
        len(formulas) >= 4
        and r"\cos A=\frac{AC}{AB}" in formulas
        and any(
            formula in {r"AB=\frac{AC}{\cos A}", r"AC=AB\cdot\cos A"}
            for formula in formulas
        )
    )


def _is_pipeline_unsimplified_root_solution(value: str) -> bool:
    """Recognize the runner's former sqrt(n*d)/d rationalization shape."""

    if 'data-content-kind="solution"' not in value:
        return False
    for radicand, denominator in re.findall(
        r"\\frac\{\\sqrt\{(\d+)\}\}\{(\d+)\}",
        unescape(value),
    ):
        parsed_radicand = int(radicand)
        parsed_denominator = int(denominator)
        root = math.isqrt(parsed_denominator)
        if (
            root * root == parsed_denominator
            and parsed_radicand % parsed_denominator == 0
        ):
            return True
    return False


def _numeric_latex(value: str) -> float:
    """Evaluate the limited positive-number LaTeX subset used for AC."""

    compact = value.replace(" ", "")
    root = re.fullmatch(r"(?:(\d+(?:\{,\}\d+)?)?)\\sqrt\{(\d+)\}", compact)
    if root is not None:
        coefficient = root.group(1) or "1"
        return float(coefficient.replace("{,}", ".")) * math.sqrt(int(root.group(2)))
    return float(compact.replace("{,}", "."))


def _numeric_square_latex(value: str) -> Fraction:
    """Evaluate the exact square of one supported positive side length."""

    compact = value.replace(" ", "")
    radical = re.fullmatch(r"(?:(\d+(?:\{,\}\d+)?)?)\\sqrt\{(\d+)\}", compact)
    if radical is not None:
        coefficient = Fraction((radical.group(1) or "1").replace("{,}", "."))
        return coefficient * coefficient * int(radical.group(2))
    parsed = Fraction(compact.replace("{,}", "."))
    return parsed * parsed


def _answer_text(value: float) -> str:
    """Format a finite deterministic result for the Russian answer field."""

    rounded = round(value, 10)
    if math.isclose(rounded, round(rounded), abs_tol=1e-9):
        return str(round(rounded))
    return f"{rounded:.10f}".rstrip("0").rstrip(".").replace(".", ",")


def _number_latex(value: Fraction) -> str:
    """Render one exact nonnegative rational without an unnecessary denominator."""

    if value.denominator == 1:
        return str(value.numerator)
    return _fraction_latex(value)


def _positive_root_number_latex(square: Fraction) -> str:
    """Render a positive root and collapse the legacy integer-over-one form."""

    rendered = _positive_root_latex(square)
    unit_fraction = re.fullmatch(r"\\frac\{(\d+)\}\{1\}", rendered)
    return unit_fraction.group(1) if unit_fraction is not None else rendered


def _asset_transformation(parent_asset_id: str) -> dict[str, Any]:
    """Attach the parent condition image at the canonical first position."""

    return {
        "transformation_target_id": "asset:image_1",
        "operation": "add",
        "value": {
            "parent_target_id": "section:condition:1",
            "position": 0,
            "asset_key": "image_1",
            "asset_id": parent_asset_id,
            "url": f"/assets/{parent_asset_id}",
            "kind": "ordinary_image",
            "alt": "",
        },
    }


def _solution_transformation(
    trig_name: str,
    trig_latex: str,
    trig_squared: Fraction,
    cosine_latex: str,
    known: str,
    requested: str,
    answer: str,
    hypotenuse_latex: str | None,
) -> dict[str, Any]:
    """Build the compact prototype-shaped solution for the selected side rule."""

    answer_latex = answer.replace(",", "{,}")
    canonical_trig = _canonical_trig_latex(trig_latex)
    lead_rows: list[str] = []
    decimal_row = _decimal_reduction_latex(trig_name, trig_latex)
    if decimal_row is not None:
        lead_rows.append(decimal_row)
    if trig_name == "sin":
        intro = (
            '<p>Найдём косинус угла '
            '<var data-math-identifier="A">A</var>:</p>'
        )
        lead_rows.append(
            rf"\cos A=\sqrt{{1-\sin^2 A}}="
            rf"\sqrt{{1-\left({canonical_trig}\right)^2}}={cosine_latex}"
        )
    else:
        intro = (
            "<p>Запишем значение косинуса в виде обыкновенной дроби:</p>"
            if decimal_row is not None
            else '<p>По условию задан косинус угла '
            '<var data-math-identifier="A">A</var>:</p>'
        )
        if decimal_row is None:
            lead_rows.append(rf"\cos A={canonical_trig}")
    if requested == "AB":
        result_formula = (
            rf"AB=\frac{{AC}}{{\cos A}}="
            rf"\frac{{{known}}}{{{cosine_latex}}}={answer_latex}"
        )
    elif requested == "AC":
        result_formula = (
            rf"AC=AB\cdot\cos A={known}\cdot {cosine_latex}={answer_latex}"
        )
    else:
        if hypotenuse_latex is None:
            raise RightTrianglePlanError("AC-to-BC rule requires an exact hypotenuse")
        cosine_formula = (
            rf"\cos A=\sqrt{{1-\sin^{{2}} A}}="
            rf"\sqrt{{1-({canonical_trig})^{{2}}}}={cosine_latex}"
        )
        hypotenuse_formula = (
            rf"AB=\frac{{AC}}{{\cos A}}="
            rf"\frac{{{known}}}{{{cosine_latex}}}={hypotenuse_latex}"
        )
        result_formula = (
            rf"BC=\sqrt{{AB^{{2}}-AC^{{2}}}}="
            rf"\sqrt{{({hypotenuse_latex})^{{2}}-{known}^{{2}}}}="
            rf"{answer_latex}"
        )
        html = (
            '<section data-content-kind="solution" '
            'data-solution-title="Альтернативное решение.">'
            '<p><b>Альтернативное решение.</b></p>'
            '<p>Най\u00adдем ко\u00adси\u00adнус угла <i>А</i>:</p>'
            '<center><p> <span data-inline-latex="'
            + cosine_formula
            + '"></span> . </p></center>'
            '<p>Най\u00adдем длину ги\u00adпо\u00adте\u00adну\u00adзы '
            '<var data-math-identifier="AB">AB</var>:</p>'
            '<center><p> <span data-inline-latex="'
            + hypotenuse_formula
            + '"></span> . </p></center>'
            '<p>По те\u00adо\u00adре\u00adме Пи\u00adфа\u00adго\u00adра най\u00adдем длину ка\u00adте\u00adта '
            '<var data-math-identifier="BC">BC</var>:</p>'
            '<center><p> <span data-inline-latex="'
            + result_formula
            + '"></span>. </p></center></section>'
        )
        return {
            "transformation_target_id": "section:solution",
            "operation": "add",
            "value": {"title": "Решение", "html": html, "asset_keys": []},
        }
    html = (
        '<section data-content-kind="solution" data-solution-title="Решение">'
        + intro
        + "".join(
            '<center><p><span data-inline-latex="'
            + row
            + '"></span>.</p></center>'
            for row in lead_rows
        )
        + "<p>Следовательно,</p>"
        + '<center><p><span data-inline-latex="'
        + result_formula
        + '"></span>.</p></center>'
        + "</section>"
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": "add",
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _tangent_solution_transformation(
    trig_latex: str,
    known: str,
    known_squared: Fraction,
    bc_latex: str,
    bc_squared: Fraction,
    hypotenuse_squared: Fraction,
    answer: str,
) -> dict[str, Any]:
    """Copy the approved tangent-definition and Pythagoras solution HTML."""

    answer_latex = answer.replace(",", "{,}")
    hypotenuse_latex = _positive_root_number_latex(hypotenuse_squared)
    exact_answer = (
        hypotenuse_latex
        if hypotenuse_latex == answer_latex
        else hypotenuse_latex + "=" + answer_latex
    )
    definition_formula = r"\tg A=\frac{BC}{AC}"
    bc_formula = (
        rf"BC=AC\cdot\tg A={known}\cdot {trig_latex}={bc_latex}"
    )
    ab_formula = (
        rf"AB=\sqrt{{AC^{{2}}+BC^{{2}}}}="
        rf"\sqrt{{{_number_latex(known_squared)}+{_number_latex(bc_squared)}}}="
        rf"\sqrt{{{_number_latex(hypotenuse_squared)}}}={exact_answer}"
    )
    html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-tangent-hypotenuse" '
        'data-solution-title="Приведем другое решение:">'
        '<center><p><span data-inline-latex="'
        + definition_formula
        + '"></span>.</p></center>'
        '<p>Най\u00adдем <var data-math-identifier="BC">BC</var>:</p>'
        '<center><p><span data-inline-latex="'
        + bc_formula
        + '"></span>.</p></center>'
        '<p>По те\u00adо\u00adре\u00adме Пи\u00adфа\u00adго\u00adра най\u00adдем '
        '<var data-math-identifier="AB">AB</var>:</p>'
        '<center><p><span data-inline-latex="'
        + ab_formula
        + '"></span>.</p></center></section>'
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": "add",
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _tangent_bc_solution_transformation(
    trig_latex: str,
    known: str,
    bc_latex: str,
    answer: str,
    *,
    operation: str = "add",
) -> dict[str, Any]:
    """Build the 27243 parent calculation as one equivalence chain."""

    answer_latex = answer.replace(",", "{,}")
    exact_answer = bc_latex if bc_latex == answer_latex else bc_latex + "=" + answer_latex
    html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-tangent-opposite-cathetus" '
        'data-solution-title="Решение">'
        '<p>По опре\u00adде\u00adле\u00adнию тан\u00adген\u00adса:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\tg A=\frac{{BC}}{{AC}}\iff BC=AC\tg A={known}\cdot {trig_latex}={exact_answer}"
        + '"></span>.</p></center></section>'
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": operation,
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _answer_transformation(answer: str) -> dict[str, Any]:
    """Build the canonical answer-section rewrite for one verified value."""

    return {
        "transformation_target_id": "section:answer:1",
        "operation": "rewrite",
        "value": {
            "title": "Ответ",
            "html": f'<p><span data-effect="spaced">{answer}</span></p>',
            "asset_keys": [],
        },
    }


def _elementary_solution_transformation(
    content_rule_key: str,
    intro: str,
    rows: list[str],
    *,
    operation: str = "add",
) -> dict[str, Any]:
    """Wrap one elementary right-triangle derivation without formula punctuation."""

    rendered_rows = []
    for index, row in enumerate(rows):
        rendered_rows.append(
            '<center><p><span data-inline-latex="'
            + row
            + '"></span></p></center>'
        )
        if content_rule_key == "right-triangle-median-angle" and index == 0:
            rendered_rows.append(
                '<p>Значит, <span data-inline-latex="\\triangle ACD"></span> '
                "равнобедренный, поэтому его углы при основании равны:</p>"
            )
    html = (
        '<section data-content-kind="solution" data-content-rule="'
        + content_rule_key
        + '" data-solution-title="Решение">'
        + intro
        + "".join(rendered_rows)
        + "</section>"
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": operation,
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _integer_match(pattern: str, value: str, error: str) -> int:
    """Return one positive integer captured from visible condition text."""

    match = re.search(pattern, value, re.IGNORECASE)
    if match is None:
        raise RightTrianglePlanError(error)
    parsed = int(match.group(1))
    if parsed <= 0:
        raise RightTrianglePlanError(error)
    return parsed


def _leg_hypotenuse_area_rows(condition_html: str) -> tuple[str, list[str]]:
    """Solve an area request from one leg and the hypotenuse."""

    visible = _plain_html(condition_html)
    match = re.search(
        r"катет\s+и\s+гипотенуза\s+равны\s+соответственно\s+(\d+)\s+и\s+(\d+)",
        visible,
        re.IGNORECASE,
    )
    if match is None or "найдите площадь" not in visible.lower():
        raise RightTrianglePlanError(
            "condition must give one leg and the hypotenuse and request area"
        )
    leg, hypotenuse = map(int, match.groups())
    other_square = hypotenuse * hypotenuse - leg * leg
    other_leg = math.isqrt(other_square)
    if leg <= 0 or hypotenuse <= leg or other_leg * other_leg != other_square:
        raise RightTrianglePlanError("condition must determine an integer second leg")
    area = Fraction(leg * other_leg, 2)
    answer = _answer_text(float(area))
    return answer, [
        rf"b=\sqrt{{{hypotenuse}^{{2}}-{leg}^{{2}}}}={other_leg}",
        rf"S=\frac{{1}}{{2}}\cdot{leg}\cdot{other_leg}={answer.replace(',', '{,}')}",
    ]


def _area_leg_difference_rows(condition_html: str) -> tuple[str, list[str]]:
    """Solve the smaller-leg request from area and an integer leg difference."""

    visible = _plain_html(condition_html)
    if "найдите меньший катет" not in visible.lower():
        raise RightTrianglePlanError("condition must request the smaller leg")
    area = _integer_match(
        r"площадь\s+прямоугольного\s+треугольника\s+равна\s+(\d+)",
        visible,
        "condition must give an integer area",
    )
    difference = _integer_match(
        r"катетов\s+на\s+(\d+)\s+больше",
        visible,
        "condition must give an integer leg difference",
    )
    discriminant = difference * difference + 8 * area
    root = math.isqrt(discriminant)
    if root * root != discriminant or (root - difference) % 2:
        raise RightTrianglePlanError("condition must determine an integer smaller leg")
    positive = (root - difference) // 2
    negative = -(root + difference) // 2
    if positive <= 0:
        raise RightTrianglePlanError("condition must determine a positive smaller leg")
    formula = (
        rf"\frac{{1}}{{2}}x(x+{difference})={area}"
        rf"\iff x(x+{difference})={2 * area}"
        rf"\iff x^{{2}}+{difference}x-{2 * area}=0"
        rf"\iff \begin{{cases}}\left[\begin{{aligned}}x={positive}\\x={negative}"
        rf"\end{{aligned}}\right.\\x\gt 0\end{{cases}}\iff x={positive}"
    )
    return str(positive), [formula]


def _acute_angle_difference_rows(condition_html: str) -> tuple[str, list[str]]:
    """Solve the larger acute angle from the stated integer difference."""

    visible = _plain_html(condition_html)
    if "найдите больший острый угол" not in visible.lower():
        raise RightTrianglePlanError("condition must request the larger acute angle")
    visible_difference = re.search(
        r"на\s+(\d+)°\s+больше",
        visible,
        re.IGNORECASE,
    )
    formula_differences = [
        int(match.group(1))
        for value in re.findall(
            r'data-inline-latex="([^"]+)"',
            unescape(condition_html),
        )
        if (match := re.fullmatch(r"(\d+)\^\{\\circ\}", value)) is not None
    ]
    candidates = (
        [int(visible_difference.group(1))]
        if visible_difference is not None
        else formula_differences
    )
    if len(candidates) != 1:
        raise RightTrianglePlanError(
            "condition must give an integer acute-angle difference"
        )
    difference = candidates[0]
    if difference >= 90:
        raise RightTrianglePlanError("acute-angle difference must be less than 90 degrees")
    larger = Fraction(90 + difference, 2)
    smaller = Fraction(90 - difference, 2)
    answer = _answer_text(float(larger))
    larger_latex = answer.replace(",", "{,}")
    smaller_latex = _answer_text(float(smaller)).replace(",", "{,}")
    formula = (
        rf"\begin{{cases}}\angle A-\angle B={difference}^{{\circ}}\\"
        rf"\angle A+\angle B=90^{{\circ}}\end{{cases}}"
        rf"\iff \begin{{cases}}\angle A={larger_latex}^{{\circ}}\\"
        rf"\angle B={smaller_latex}^{{\circ}}\end{{cases}}"
    )
    return answer, [formula]


def _acute_angle_ratio(condition_html: str) -> Fraction:
    """Extract the exact larger-to-smaller acute-angle ratio."""

    formulas = re.findall(r'data-inline-latex="([^"]+)"', unescape(condition_html))
    fractions = [
        Fraction(int(match.group(1)), int(match.group(2)))
        for value in formulas
        if (match := re.fullmatch(r"\\frac\{(\d+)\}\{(\d+)\}", value))
        is not None
    ]
    if len(fractions) > 1:
        raise RightTrianglePlanError("condition must give one acute-angle ratio")
    if fractions:
        return fractions[0]
    visible = _plain_html(condition_html)
    return Fraction(
        _integer_match(
            r"\bв\s+(\d+)\s+раз(?:а)?\s+больше",
            visible,
            "condition must give one acute-angle ratio",
        ),
        1,
    )


def _acute_angle_ratio_rows(condition_html: str) -> tuple[str, list[str]]:
    """Solve the larger acute angle from its exact ratio to the smaller one."""

    visible = _plain_html(condition_html)
    if "найдите больший острый угол" not in visible.lower():
        raise RightTrianglePlanError("condition must request the larger acute angle")
    ratio = _acute_angle_ratio(condition_html)
    if ratio <= 1:
        raise RightTrianglePlanError("larger-to-smaller angle ratio must exceed one")
    larger_coefficient = ratio.numerator
    smaller_coefficient = ratio.denominator
    unit = Fraction(90, larger_coefficient + smaller_coefficient)
    larger = larger_coefficient * unit
    if unit.denominator != 1 or larger.denominator != 1:
        raise RightTrianglePlanError("condition must determine integer acute angles")
    unit_value = unit.numerator
    larger_value = larger.numerator
    return str(larger_value), [
        rf"{smaller_coefficient}x+{larger_coefficient}x=90^{{\circ}}"
        rf"\iff{smaller_coefficient + larger_coefficient}x=90^{{\circ}}"
        rf"\iff x={unit_value}^{{\circ}}",
        rf"{larger_coefficient}x={larger_coefficient}\cdot{unit_value}^{{\circ}}="
        rf"{larger_value}^{{\circ}}",
    ]


def _condition_degree_values(condition_html: str) -> list[int]:
    """Return stated degree values in source order across text and formula spans."""

    return [
        int(value)
        for value in re.findall(
            r"(\d+)(?:\s*°|\^\{?\\circ\}?)",
            _math_aware_html(condition_html),
        )
    ]


def _math_aware_html(value: str) -> str:
    """Return visible text with inline formula attributes restored in place."""

    normalized = unicodedata.normalize("NFKC", unescape(value)).replace("\u00ad", "")
    normalized = re.sub(
        r'<span[^>]*data-inline-latex="([^"]*)"[^>]*>.*?</span>',
        lambda match: match.group(1),
        normalized,
        flags=re.DOTALL,
    )
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", normalized)).strip()


def _acute_condition_angles(condition_html: str) -> list[int]:
    """Return the positive non-right degree values declared by one condition."""

    angles = [value for value in _condition_degree_values(condition_html) if value != 90]
    if not angles or any(value <= 0 or value >= 90 for value in angles):
        raise RightTrianglePlanError("condition must give acute angle values")
    return angles


def _require_condition_terms(condition_html: str, *terms: str) -> str:
    """Return visible text after validating every required Russian word stem."""

    visible = _math_aware_html(condition_html)
    lowered = visible.lower()
    if any(term not in lowered for term in terms):
        raise RightTrianglePlanError("condition does not match the registered angle rule")
    return visible


def _single_acute_angle(condition_html: str) -> int:
    """Return the only non-right degree value in one strict condition."""

    angles = _acute_condition_angles(condition_html)
    if len(angles) != 1:
        raise RightTrianglePlanError("condition must give exactly one acute angle value")
    return angles[0]


def _single_line_angle(condition_html: str) -> int:
    """Return one stated angle between lines, allowing the coincident case zero."""

    angles = [value for value in _condition_degree_values(condition_html) if value != 90]
    if len(angles) != 1 or angles[0] < 0 or angles[0] >= 45:
        raise RightTrianglePlanError("condition must give one line angle below 45 degrees")
    return angles[0]


def _median_angle_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find ACD from angle B and the hypotenuse median CD."""

    visible = _require_condition_terms(condition_html, "медиан", "найдите", "acd")
    if "cd" not in visible.lower() or "угол b" not in visible.lower():
        raise RightTrianglePlanError("condition must give angle B and median CD")
    angle = _single_acute_angle(condition_html)
    answer = 90 - angle
    return str(answer), [
        "CD=AD=BD",
        rf"\angle ACD=\angle A=90^{{\circ}}-\angle B="
        rf"90^{{\circ}}-{angle}^{{\circ}}={answer}^{{\circ}}",
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
        rf"\varphi=45^{{\circ}}+\frac{{{angle}^{{\circ}}}}{{2}}="
        rf"{answer_latex}^{{\circ}}"
    ]


def _altitude_bisector_angle_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find the angle between a right-vertex altitude and bisector."""

    visible = _plain_html(condition_html).lower()
    if "высот" not in visible or "биссектрис" not in visible or "медиан" in visible:
        raise RightTrianglePlanError("condition must request the altitude and bisector angle")
    angle = _single_acute_angle(condition_html)
    answer = abs(angle - 45)
    return str(answer), [
        rf"\varphi=\left|{angle}^{{\circ}}-45^{{\circ}}\right|="
        rf"{answer}^{{\circ}}"
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
        rf"\alpha_{{\min}}=45^{{\circ}}-{line_angle}^{{\circ}}="
        rf"{answer}^{{\circ}}"
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
            rf"\varphi=\left|{larger}^{{\circ}}-{smaller}^{{\circ}}\right|="
            rf"{answer}^{{\circ}}"
        ]
    if "биссектрис" in lowered and "медиан" not in lowered:
        angle = max(angles)
        answer = abs(angle - 45)
        return str(answer), [
            rf"\varphi=\left|{angle}^{{\circ}}-45^{{\circ}}\right|="
            rf"{answer}^{{\circ}}"
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
        rf"\alpha_{{\max}}=\frac{{90^{{\circ}}+{line_angle}^{{\circ}}}}{{2}}="
        rf"{answer_latex}^{{\circ}}"
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
        rf"\varphi=\left|{angle}^{{\circ}}-45^{{\circ}}\right|="
        rf"{answer}^{{\circ}}"
    ]


def _bisector_median_inverse_rows(condition_html: str) -> tuple[str, list[str]]:
    """Recover the smaller acute angle from bisector-median separation."""

    return _inverse_45_degree_rows(
        condition_html,
        first_term="биссектрис",
        second_term="медиан",
    )


def _angle_a_and_hypotenuse(condition_html: str) -> tuple[int, int, bool, str]:
    """Extract angle A and a restricted exact AB value from an altitude task."""

    visible = _latin_triangle_labels(_math_aware_html(condition_html))
    lowered = visible.lower()
    combined = (
        visible.replace(" ", "")
        .replace(r"\quad", "")
        .replace(r"\,", "")
    )
    if "уголcравен90" not in lowered.replace(" ", "") and "90" not in combined:
        raise RightTrianglePlanError("condition must declare right angle C")
    angles = _acute_condition_angles(condition_html)
    if len(angles) != 1 or angles[0] not in {30, 60}:
        raise RightTrianglePlanError("condition must give angle A equal to 30 or 60 degrees")
    radical = re.search(r"AB=(\d*)\\sqrt\{?3\}?", combined)
    if radical is not None:
        coefficient = int(radical.group(1) or "1")
        return angles[0], coefficient, True, (
            ("" if coefficient == 1 else str(coefficient)) + r"\sqrt{3}"
        )
    plain = re.search(r"AB=(\d+)(?:[,.](\d+))?", combined)
    if plain is None or plain.group(2) is not None:
        raise RightTrianglePlanError("condition must give an exact supported AB value")
    value = int(plain.group(1))
    return angles[0], value, False, str(value)


def _altitude_length_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find CH from AB and a 30- or 60-degree acute angle."""

    visible = _require_condition_terms(condition_html, "найдите", "высот", "ch")
    if "ah" in visible.lower() or "bh" in visible.lower():
        raise RightTrianglePlanError("condition must request CH")
    angle, coefficient, radical, ab_latex = _angle_a_and_hypotenuse(condition_html)
    if not radical:
        raise RightTrianglePlanError("altitude-length condition must give AB as k sqrt(3)")
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

    visible = _require_condition_terms(condition_html, "высот", "найдите", requested.lower())
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
        rf"{requested}=AB\{trig_name}^{{2}}A={ab_latex}\cdot"
        rf"\left({trig_latex}\right)^{{2}}={_number_latex(answer)}"
    ]


def _hypotenuse_projection_ah_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find projection AH on the hypotenuse."""

    return _projection_rows(condition_html, requested="AH")


def _hypotenuse_projection_bh_rows(condition_html: str) -> tuple[str, list[str]]:
    """Find projection BH on the hypotenuse."""

    return _projection_rows(condition_html, requested="BH")


_ELEMENTARY_RULES = {
    "right-triangle-leg-hypotenuse-area": _leg_hypotenuse_area_rows,
    "right-triangle-area-leg-difference": _area_leg_difference_rows,
    "right-triangle-acute-angle-difference": _acute_angle_difference_rows,
    "right-triangle-acute-angle-ratio": _acute_angle_ratio_rows,
    "right-triangle-median-angle": _median_angle_rows,
    "right-triangle-bisector-intersection-angle": _bisector_intersection_angle_rows,
    "right-triangle-altitude-bisector-angle": _altitude_bisector_angle_rows,
    "right-triangle-altitude-bisector-inverse": _altitude_bisector_inverse_rows,
    "right-triangle-altitude-line-angle": _altitude_line_angle_rows,
    "right-triangle-altitude-median-inverse": _altitude_median_inverse_rows,
    "right-triangle-bisector-median-angle": _bisector_median_angle_rows,
    "right-triangle-bisector-median-inverse": _bisector_median_inverse_rows,
    "right-triangle-altitude-length": _altitude_length_rows,
    "right-triangle-hypotenuse-projection-ah": _hypotenuse_projection_ah_rows,
    "right-triangle-hypotenuse-projection-bh": _hypotenuse_projection_bh_rows,
}


def _elementary_intro(content_rule_key: str, condition_html: str) -> str:
    """Return the concise prose that introduces one elementary derivation."""

    if content_rule_key == "right-triangle-area-leg-difference":
        difference = _integer_match(
            r"катетов\s+на\s+(\d+)\s+больше",
            _plain_html(condition_html),
            "condition must give an integer leg difference",
        )
        return (
            '<p>Пусть <span data-inline-latex="x"></span> — меньший катет, '
            'тогда второй <span data-inline-latex="x+'
            + str(difference)
            + '"></span>:</p>'
        )
    if content_rule_key == "right-triangle-bisector-intersection-angle":
        return (
            '<p>Пусть данный острый угол равен '
            '<span data-inline-latex="\\alpha"></span>. Тогда второй острый угол '
            'равен <span data-inline-latex="90^{\\circ}-\\alpha"></span>.</p>'
            '<p>Обозначим точку пересечения биссектрис через '
            '<span data-inline-latex="O"></span>. Биссектриса данного острого '
            'угла делит его пополам, поэтому '
            '<span data-inline-latex="\\angle OAC=\\frac{\\alpha}{2}"></span>.</p>'
            '<p>Биссектриса прямого угла также делит его пополам, следовательно, '
            '<span data-inline-latex="\\angle ACO=45^{\\circ}"></span>. Тогда по '
            'сумме углов треугольника <span data-inline-latex="AOC"></span> '
            '<span data-inline-latex="\\angle AOC=135^{\\circ}-\\frac{\\alpha}{2}"></span>.</p>'
            '<p>Полученный угол тупой; смежный с ним острый угол является '
            'искомым и равен '
            '<span data-inline-latex="45^{\\circ}+\\frac{\\alpha}{2}"></span>:</p>'
        )
    if content_rule_key == "right-triangle-altitude-bisector-angle":
        return (
            '<p>Пусть <span data-inline-latex="\\angle B=\\alpha"></span>. '
            'Так как <span data-inline-latex="CH\\perp AB"></span>, треугольник '
            '<span data-inline-latex="BCH"></span> прямоугольный, поэтому '
            '<span data-inline-latex="\\angle BCH=90^{\\circ}-\\alpha"></span>.</p>'
            '<p>Отрезок <span data-inline-latex="CD"></span> — биссектриса '
            'прямого угла, следовательно, '
            '<span data-inline-latex="\\angle ACD=45^{\\circ}"></span>.</p>'
            '<p>Искомый угол равен модулю разности полученных углов: '
            '<span data-inline-latex="\\varphi=|\\angle BCH-\\angle ACD|"></span>. '
            "Подставим данное значение:</p>"
        )
    if content_rule_key == "right-triangle-altitude-bisector-inverse":
        return (
            '<p>Пусть <span data-inline-latex="\\varphi"></span> — данный угол '
            'между высотой и биссектрисой. Так как '
            '<span data-inline-latex="CD"></span> — биссектриса прямого угла, '
            '<span data-inline-latex="\\angle ACD=45^{\\circ}"></span>.</p>'
            '<p>Поэтому <span data-inline-latex="\\angle ACH=45^{\\circ}+\\varphi"></span>. '
            'Треугольник <span data-inline-latex="ACH"></span> прямоугольный при '
            '<span data-inline-latex="H"></span>, поэтому сумма его острых углов '
            'равна <span data-inline-latex="90^{\\circ}"></span>.</p>'
            '<p>Следовательно, '
            '<span data-inline-latex="\\angle A=90^{\\circ}-\\angle ACH"></span>, '
            "откуда найдём меньший острый угол:</p>"
        )
    if content_rule_key == "right-triangle-altitude-line-angle":
        visible = _math_aware_html(condition_html).lower()
        if "медиан" in visible and "биссектрис" not in visible:
            return (
                '<p>Медиана к гипотенузе равна её половине. Поэтому '
                '<span data-inline-latex="CM=BM"></span>, и треугольник '
                '<span data-inline-latex="CMB"></span> равнобедренный.</p>'
                '<p>Его углы при основании равны: '
                '<span data-inline-latex="\\angle BCM=\\angle CBM=\\angle B"></span>.</p>'
                '<p>Так как <span data-inline-latex="CH\\perp AB"></span>, '
                'треугольник <span data-inline-latex="BCH"></span> прямоугольный. '
                'Поэтому <span data-inline-latex="\\angle BCH=90^{\\circ}-\\angle B"></span>. '
                'Но <span data-inline-latex="\\angle A=90^{\\circ}-\\angle B"></span>, '
                'следовательно, <span data-inline-latex="\\angle BCH=\\angle A"></span>.</p>'
                '<p>Угол между высотой и медианой равен разности '
                '<span data-inline-latex="\\angle BCM"></span> и '
                '<span data-inline-latex="\\angle BCH"></span>:</p>'
            )
        return (
            '<p>Биссектриса прямого угла образует угол '
            '<span data-inline-latex="45^{\\circ}"></span>. Высота, проведённая '
            "из вершины прямого угла, делит исходный треугольник на два "
            "подобных ему прямоугольных треугольника.</p>"
            "<p>Поэтому угол между высотой и биссектрисой равен разности "
            "соответствующего острого угла и половины прямого угла:</p>"
        )
    if content_rule_key == "right-triangle-altitude-median-inverse":
        return (
            '<p>Пусть <span data-inline-latex="\\varphi"></span> — угол между '
            'высотой <span data-inline-latex="CH"></span> и медианой '
            '<span data-inline-latex="CM"></span>. В прямоугольном треугольнике '
            '<span data-inline-latex="CHM"></span> получаем '
            '<span data-inline-latex="\\angle CMB=90^{\\circ}-\\varphi"></span>.</p>'
            '<p>Медиана к гипотенузе равна её половине, поэтому '
            '<span data-inline-latex="CM=MB"></span> и треугольник '
            '<span data-inline-latex="CMB"></span> равнобедренный.</p>'
            '<p>Его углы при основании равны, а их сумма равна разности между '
            '<span data-inline-latex="180^{\\circ}"></span> и углом при вершине: '
            '<span data-inline-latex="\\angle CBM=\\angle BCM=\\frac{180^{\\circ}-\\angle CMB}{2}"></span>.</p>'
            '<p>Угол <span data-inline-latex="\\angle CBM"></span> совпадает с '
            "большим острым углом исходного треугольника, поэтому:</p>"
        )
    if content_rule_key == "right-triangle-bisector-median-angle":
        return (
            '<p>Медиана к гипотенузе равна её половине, поэтому '
            '<span data-inline-latex="CM=BM"></span>. Значит, треугольник '
            '<span data-inline-latex="CMB"></span> равнобедренный и '
            '<span data-inline-latex="\\angle BCM=\\angle B"></span>.</p>'
            '<p>Биссектриса <span data-inline-latex="CD"></span> делит прямой '
            'угол пополам, поэтому '
            '<span data-inline-latex="\\angle ACD=45^{\\circ}"></span> и '
            '<span data-inline-latex="\\angle DCB=45^{\\circ}"></span>.</p>'
            '<p>Искомый угол равен модулю разности углов '
            '<span data-inline-latex="\\angle BCM"></span> и '
            '<span data-inline-latex="\\angle DCB"></span>:</p>'
        )
    if content_rule_key == "right-triangle-bisector-median-inverse":
        return (
            '<p>Так как <span data-inline-latex="CM"></span> — медиана к '
            'гипотенузе, <span data-inline-latex="AM=CM"></span>. Поэтому '
            'треугольник <span data-inline-latex="AMC"></span> равнобедренный и '
            '<span data-inline-latex="\\angle ACM=\\angle A"></span>.</p>'
            '<p>Биссектриса <span data-inline-latex="CD"></span> делит прямой '
            'угол пополам, поэтому '
            '<span data-inline-latex="\\angle ACD=45^{\\circ}"></span>.</p>'
            '<p>Поскольку данный угол между биссектрисой и медианой равен '
            '<span data-inline-latex="\\varphi=45^{\\circ}-\\angle A"></span>, '
            "меньший острый угол получаем вычитанием:</p>"
        )
    if content_rule_key == "right-triangle-altitude-length":
        return (
            '<p>Так как <span data-inline-latex="CH"></span> — высота, '
            '<span data-inline-latex="CH\\perp AB"></span>, и треугольник '
            '<span data-inline-latex="ACH"></span> прямоугольный.</p>'
            '<p>В треугольнике <span data-inline-latex="ABC"></span> по '
            'определению косинуса '
            '<span data-inline-latex="\\cos A=\\frac{AC}{AB}"></span>, откуда '
            '<span data-inline-latex="AC=AB\\cos A"></span>.</p>'
            '<p>В треугольнике <span data-inline-latex="ACH"></span> по '
            'определению синуса '
            '<span data-inline-latex="\\sin A=\\frac{CH}{AC}"></span>, откуда '
            '<span data-inline-latex="CH=AC\\sin A"></span>.</p>'
            "<p>Подставим первое равенство во второе и вычислим высоту:</p>"
        )
    if content_rule_key == "right-triangle-hypotenuse-projection-ah":
        return (
            '<p>Так как <span data-inline-latex="CH\\perp AB"></span>, '
            'треугольник <span data-inline-latex="ACH"></span> прямоугольный, '
            'причём <span data-inline-latex="\\angle CAH=\\angle A"></span>.</p>'
            '<p>В треугольнике <span data-inline-latex="ABC"></span> '
            '<span data-inline-latex="\\cos A=\\frac{AC}{AB}"></span>, поэтому '
            '<span data-inline-latex="AC=AB\\cos A"></span>.</p>'
            '<p>В треугольнике <span data-inline-latex="ACH"></span> '
            '<span data-inline-latex="\\cos A=\\frac{AH}{AC}"></span>, поэтому '
            '<span data-inline-latex="AH=AC\\cos A"></span>.</p>'
            "<p>Последовательно подставим найденные выражения:</p>"
        )
    if content_rule_key == "right-triangle-hypotenuse-projection-bh":
        return (
            '<p>В треугольнике <span data-inline-latex="ABC"></span> по '
            'определению синуса '
            '<span data-inline-latex="\\sin A=\\frac{BC}{AB}"></span>, откуда '
            '<span data-inline-latex="BC=AB\\sin A"></span>.</p>'
            '<p>Так как <span data-inline-latex="CH\\perp AB"></span>, '
            'треугольник <span data-inline-latex="BCH"></span> прямоугольный. '
            'Его угол <span data-inline-latex="\\angle BCH=90^{\\circ}-\\angle B"></span>. '
            'Так как <span data-inline-latex="\\angle A=90^{\\circ}-\\angle B"></span>, '
            '<span data-inline-latex="\\angle BCH=\\angle A"></span>.</p>'
            '<p>По определению синуса в треугольнике '
            '<span data-inline-latex="BCH"></span> '
            '<span data-inline-latex="\\sin A=\\frac{BH}{BC}"></span>, поэтому '
            '<span data-inline-latex="BH=BC\\sin A"></span>.</p>'
            "<p>Подставим первое равенство во второе:</p>"
        )
    return {
        "right-triangle-leg-hypotenuse-area": (
            "<p>По теореме Пифагора найдём второй катет:</p>"
        ),
        "right-triangle-acute-angle-difference": (
            "<p>Сумма острых углов прямоугольного треугольника равна 90°:</p>"
        ),
        "right-triangle-acute-angle-ratio": (
            "<p>Пусть углы пропорциональны данным числам:</p>"
        ),
        "right-triangle-median-angle": (
            '<p>Так как <span data-inline-latex="CD"></span> — медиана, точка '
            '<span data-inline-latex="D"></span> — середина гипотенузы '
            '<span data-inline-latex="AB"></span>, поэтому '
            '<span data-inline-latex="AD=BD"></span>.</p>'
            '<p>Медиана, проведённая из вершины прямого угла к гипотенузе, '
            "равна половине гипотенузы:</p>"
        ),
    }[content_rule_key]


def build_elementary_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
    content_rule_key: str,
) -> RepairPlan:
    """Return a strict image, solution, and answer repair for one elementary rule."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    try:
        solver = _ELEMENTARY_RULES[content_rule_key]
    except KeyError as exc:
        raise RightTrianglePlanError("unsupported elementary content rule") from exc
    condition_html = str(condition.get("html") or "")
    answer, rows = solver(condition_html)
    intro = _elementary_intro(content_rule_key, condition_html)
    desired_solution = _elementary_solution_transformation(
        content_rule_key,
        intro,
        rows,
    )
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if not isinstance(current_asset, dict) or current_asset.get("asset_id") != parent_asset_id:
        transformations.append(_asset_transformation(parent_asset_id))
    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    if solution is None or not _plain_html(solution_html):
        transformations.append(desired_solution)
    elif (
        f'data-content-rule="{content_rule_key}"' in solution_html
        and solution_html != desired_solution["value"]["html"]
    ):
        transformations.append(
            _elementary_solution_transformation(
                content_rule_key,
                intro,
                rows,
                operation="rewrite",
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
    required_trig_name: str | None = None,
    required_requested: str | None = None,
) -> RepairPlan:
    """Return minimal image, solution, and answer transformations for one task."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    trig_name, trig_latex, _known_side, known, requested = _latex_values(
        str(condition.get("html") or "")
    )
    if required_trig_name is not None and trig_name != required_trig_name:
        raise RightTrianglePlanError(
            f"condition must use {required_trig_name} A"
        )
    if required_requested is not None and requested != required_requested:
        raise RightTrianglePlanError(
            f"condition must request {required_requested}"
        )
    if (_known_side, requested) not in {
        ("AC", "AB"),
        ("AB", "AC"),
        ("AC", "BC"),
    }:
        raise RightTrianglePlanError("condition is outside the supported side rules")
    if requested == "BC" and trig_name != "sin":
        raise RightTrianglePlanError("AC-to-BC rule requires sin A")
    trig_squared = _trig_square(trig_latex)
    if trig_name == "tg" and trig_squared <= 0:
        raise RightTrianglePlanError("tg A must be positive")
    if trig_name != "tg" and not 0 < trig_squared < 1:
        raise RightTrianglePlanError("sin A or cos A must be between zero and one")
    known_value = _numeric_latex(known)
    known_squared = _numeric_square_latex(known)
    cosine_latex = ""
    hypotenuse_latex = None
    bc_squared = Fraction(0)
    hypotenuse_squared = Fraction(0)
    bc_latex = ""
    if trig_name == "tg":
        bc_squared = known_squared * trig_squared
        hypotenuse_squared = known_squared + bc_squared
        bc_latex = _positive_root_number_latex(bc_squared)
        answer_value = math.sqrt(float(hypotenuse_squared))
    else:
        cosine_squared = 1 - trig_squared if trig_name == "sin" else trig_squared
        cosine_latex = _positive_root_latex(cosine_squared)
        cosine = math.sqrt(float(cosine_squared))
    if trig_name != "tg" and requested == "AB":
        answer_value = known_value / cosine
    elif trig_name != "tg" and requested == "AC":
        answer_value = known_value * cosine
    elif trig_name != "tg":
        hypotenuse_squared = known_squared / cosine_squared
        hypotenuse_latex = _positive_root_latex(hypotenuse_squared)
        answer_value = math.sqrt(float(hypotenuse_squared - known_squared))
    answer = _answer_text(answer_value)
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if not isinstance(current_asset, dict) or current_asset.get("asset_id") != parent_asset_id:
        transformations.append(_asset_transformation(parent_asset_id))
    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    if (
        solution is None
        or not _plain_html(solution_html)
        or _is_pipeline_verbose_solution(solution_html)
        or _is_pipeline_unsimplified_root_solution(solution_html)
        or (requested == "BC" and "<img" in solution_html)
        or (
            trig_name == "tg"
            and 'data-content-rule="right-triangle-tangent-hypotenuse"'
            not in solution_html
        )
    ):
        if trig_name == "tg":
            transformations.append(
                _tangent_solution_transformation(
                    trig_latex,
                    known,
                    known_squared,
                    bc_latex,
                    bc_squared,
                    hypotenuse_squared,
                    answer,
                )
            )
        else:
            transformations.append(
                _solution_transformation(
                    trig_name,
                    trig_latex,
                    trig_squared,
                    cosine_latex,
                    known,
                    requested,
                    answer,
                    hypotenuse_latex,
                )
            )
    if (
        answer_section is None
        or _plain_html(str(answer_section.get("html") or "")) != answer
    ):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_universal_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
) -> RepairPlan:
    """Return a role-normalized repair for any supported right triangle."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    trig_request = _universal_trig_request_values(condition_html)
    if trig_request is not None:
        return _build_universal_trig_request_plan(
            content,
            answer_section=answer_section,
            values=trig_request,
            parent_asset_id=parent_asset_id,
        )
    values = _universal_values(condition_html)
    trig_squared = _trig_square(values.trig_latex)
    if values.trig_name in {"sin", "cos"}:
        if not 0 < trig_squared < 1:
            raise RightTrianglePlanError("sin or cos of an acute angle must be between zero and one")
    elif trig_squared <= 0:
        raise RightTrianglePlanError("tg or ctg of an acute angle must be positive")

    sides = {"AB", "AC", "BC"}
    third_side = (sides - {values.numerator_side, values.denominator_side}).pop()
    if values.denominator_side == values.hypotenuse:
        coefficients = {
            values.hypotenuse: Fraction(1),
            values.numerator_side: trig_squared,
            third_side: 1 - trig_squared,
        }
    else:
        coefficients = {
            values.denominator_side: Fraction(1),
            values.numerator_side: trig_squared,
            values.hypotenuse: 1 + trig_squared,
        }
    known_squared = _numeric_square_latex(values.known_latex)
    if known_squared <= 0:
        raise RightTrianglePlanError("known side must be positive")
    scale_squared = known_squared / coefficients[values.known_side]
    side_squares = {
        side: scale_squared * coefficient
        for side, coefficient in coefficients.items()
    }
    side_latex = {
        side: _positive_root_number_latex(square)
        for side, square in side_squares.items()
    }
    answer = _answer_text(math.sqrt(float(side_squares[values.requested_side])))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if not isinstance(current_asset, dict) or current_asset.get("asset_id") != parent_asset_id:
        transformations.append(_asset_transformation(parent_asset_id))

    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    runner_solution_needs_refresh = (
        'data-content-rule="right-triangle-universal"' in solution_html
        and (
            "</span>.</p>" in solution_html
            or r"\iff" not in unescape(solution_html)
        )
    )
    if solution is None or not _plain_html(solution_html) or runner_solution_needs_refresh:
        transformations.append(
            _universal_solution_transformation(
                values,
                side_latex=side_latex,
                third_side=third_side,
            )
        )
    if not _answer_matches(answer_section, answer):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_altitude_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
) -> RepairPlan:
    """Return a fail-closed repair for right triangles split by altitude CH."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    try:
        solved = solve_altitude_condition(str(condition.get("html") or ""))
    except AltitudeSolveError as exc:
        raise RightTrianglePlanError(str(exc)) from exc

    answer_needs_repair = answer_section is None
    if answer_section is not None:
        try:
            answer_needs_repair = not altitude_answer_matches(
                str(answer_section.get("html") or ""),
                solved.exact_value,
            )
        except AltitudeSolveError:
            answer_needs_repair = True

    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if not isinstance(current_asset, dict) or current_asset.get("asset_id") != parent_asset_id:
        transformations.append(_asset_transformation(parent_asset_id))

    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    solution_has_content = bool(_plain_html(solution_html)) or (
        'data-inline-latex="' in solution_html
    )
    stale_runner_solution = (
        'data-content-rule="right-triangle-altitude-universal"' in solution_html
        and f'data-content-version="{_ALTITUDE_CONTENT_VERSION}"' not in solution_html
    )
    if solution is None or not solution_has_content or stale_runner_solution:
        rendered_steps: list[str] = []
        for row in solved.rows:
            intro = _altitude_step_intro(row)
            if intro:
                rendered_steps.append(f"<p>{intro}</p>")
            rendered_steps.append(
                '<center><p><span data-inline-latex="'
                + row
                + '"></span></p></center>'
            )
        html = (
            '<section data-content-kind="solution" '
            'data-content-rule="right-triangle-altitude-universal" '
            f'data-content-version="{_ALTITUDE_CONTENT_VERSION}" '
            'data-solution-title="Решение">'
            + "".join(rendered_steps)
            + "</section>"
        )
        transformations.append(
            {
                "transformation_target_id": "section:solution",
                "operation": "add" if solution is None else "rewrite",
                "value": {"title": "Решение", "html": html, "asset_keys": []},
            }
        )
    if answer_needs_repair:
        transformations.append(_answer_transformation(solved.answer))
    return RepairPlan(answer=solved.answer, transformations=tuple(transformations))


def _altitude_step_intro(row: str) -> str:
    """Return one concise geometric transition before a formula block."""

    pythagorean_triangles = {
        "AB^2=AC^2+BC^2": "ABC",
        "AC^2=AH^2+CH^2": "ACH",
        "BC^2=BH^2+CH^2": "BCH",
    }
    triangle = pythagorean_triangles.get(row)
    if triangle is not None:
        return (
            "По теореме Пифагора для "
            f'<span data-inline-latex="\\triangle {triangle}"></span>:'
        )

    function_name = next(
        (
            label
            for prefix, label in (
                (r"\sin A=", "синуса"),
                (r"\cos A=", "косинуса"),
                (r"\tg A=", "тангенса"),
            )
            if row.startswith(prefix)
        ),
        None,
    )
    if function_name is None:
        return ""
    ratio_triangles = (
        ("ABC", (r"\frac{BC}{AB}", r"\frac{AC}{AB}", r"\frac{BC}{AC}")),
        ("ACH", (r"\frac{CH}{AC}", r"\frac{AH}{AC}", r"\frac{CH}{AH}")),
        ("BCH", (r"\frac{BH}{BC}", r"\frac{CH}{BC}", r"\frac{BH}{CH}")),
    )
    triangle = next(
        (
            name
            for name, ratios in ratio_triangles
            if any(ratio in row for ratio in ratios)
        ),
        None,
    )
    if triangle == "BCH":
        return (
            'Так как <span data-inline-latex="\\angle BCH=\\angle A"></span>, '
            f"по определению {function_name} в "
            '<span data-inline-latex="\\triangle BCH"></span>:'
        )
    return (
        f"По определению {function_name} в "
        f'<span data-inline-latex="\\triangle {triangle}"></span>:'
        if triangle is not None
        else ""
    )


def _build_universal_trig_request_plan(
    content: dict[str, Any],
    *,
    answer_section: dict[str, Any] | None,
    values: UniversalTrigRequestValues,
    parent_asset_id: str,
) -> RepairPlan:
    """Build a repair when two sides are given and a trig value is requested."""

    side_squares = {
        side: _numeric_square_latex(latex)
        for side, latex in values.known_sides
    }
    if any(square <= 0 for square in side_squares.values()):
        raise RightTrianglePlanError("known sides must be positive")
    all_sides = {"AB", "AC", "BC"}
    missing_side = (all_sides - set(side_squares)).pop()
    if missing_side == values.hypotenuse:
        side_squares[missing_side] = sum(side_squares.values(), Fraction())
    else:
        if values.hypotenuse not in side_squares:
            raise RightTrianglePlanError("two legs or the hypotenuse and one leg are required")
        other_leg = (all_sides - {values.hypotenuse, missing_side}).pop()
        missing_square = side_squares[values.hypotenuse] - side_squares[other_leg]
        if missing_square <= 0:
            raise RightTrianglePlanError("hypotenuse must be longer than a known leg")
        side_squares[missing_side] = missing_square

    side_latex = dict(values.known_sides)
    side_latex[missing_side] = _positive_root_number_latex(side_squares[missing_side])
    trig_square = (
        side_squares[values.numerator_side]
        / side_squares[values.denominator_side]
    )
    answer = _answer_text(math.sqrt(float(trig_square)))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if not isinstance(current_asset, dict) or current_asset.get("asset_id") != parent_asset_id:
        transformations.append(_asset_transformation(parent_asset_id))

    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    runner_solution_needs_refresh = (
        'data-content-rule="right-triangle-universal"' in solution_html
        and "</span>.</p>" in solution_html
    )
    if solution is None or not _plain_html(solution_html) or runner_solution_needs_refresh:
        transformations.append(
            _universal_trig_request_solution_transformation(
                values,
                side_latex=side_latex,
                missing_side=missing_side,
                answer=answer,
            )
        )
    if not _answer_matches(answer_section, answer):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    """Return whether one answer section equals the computed numeric value."""

    if section is None:
        return False
    current = _plain_html(str(section.get("html") or "")).replace(" ", "")
    if current == expected:
        return True
    try:
        return Fraction(current.replace(",", ".")) == Fraction(
            expected.replace(",", ".")
        )
    except (ValueError, ZeroDivisionError):
        return False


def _universal_solution_transformation(
    values: UniversalRightTriangleValues,
    *,
    side_latex: dict[str, str],
    third_side: str,
) -> dict[str, Any]:
    """Build two or three concise rows from normalized right-triangle roles."""

    function = rf"\{values.trig_name} {values.trig_angle}"
    numerator = values.numerator_side
    denominator = values.denominator_side
    known = values.known_side
    requested = values.requested_side
    trig = values.trig_latex
    definition = rf"{function}=\frac{{{numerator}}}{{{denominator}}}"
    rows: list[str] = []
    if {known, requested} == {numerator, denominator}:
        if known == numerator:
            rows.append(
                definition
                + rf"\iff {denominator}=\frac{{{numerator}}}{{{function}}}="
                rf"\frac{{{values.known_latex}}}{{{trig}}}={side_latex[denominator]}"
            )
        else:
            rows.append(
                definition
                + rf"\iff {numerator}={denominator}\cdot{function}="
                rf"{values.known_latex}\cdot {trig}={side_latex[numerator]}"
            )
    elif known in {numerator, denominator}:
        if known == numerator:
            calculated = denominator
            rows.append(
                definition
                + rf"\iff {denominator}=\frac{{{numerator}}}{{{function}}}="
                rf"\frac{{{values.known_latex}}}{{{trig}}}={side_latex[denominator]}"
            )
        else:
            calculated = numerator
            rows.append(
                definition
                + rf"\iff {numerator}={denominator}\cdot{function}="
                rf"{values.known_latex}\cdot {trig}={side_latex[numerator]}"
            )
        if requested == values.hypotenuse:
            legs = sorted({"AB", "AC", "BC"} - {values.hypotenuse})
            rows.append(
                rf"{requested}=\sqrt{{{legs[0]}^{{2}}+{legs[1]}^{{2}}}}="
                rf"\sqrt{{{side_latex[legs[0]]}^{{2}}+{side_latex[legs[1]]}^{{2}}}}="
                rf"{side_latex[requested]}"
            )
        else:
            other_leg = (
                {"AB", "AC", "BC"}
                - {values.hypotenuse, requested}
            ).pop()
            rows.append(
                rf"{requested}=\sqrt{{{values.hypotenuse}^{{2}}-{other_leg}^{{2}}}}="
                rf"\sqrt{{{side_latex[values.hypotenuse]}^{{2}}-{side_latex[other_leg]}^{{2}}}}="
                rf"{side_latex[requested]}"
            )
        if calculated == requested:
            raise RightTrianglePlanError("universal solution selected a redundant third row")
    else:
        if known != third_side:
            raise RightTrianglePlanError("known side is outside normalized triangle roles")
        if values.trig_name in {"sin", "cos"}:
            complement_name = "cos" if values.trig_name == "sin" else "sin"
            complement = rf"\{complement_name} {values.trig_angle}"
            complement_latex = _positive_root_latex(Fraction(1) - _trig_square(trig))
            rows.extend(
                [
                    rf"{complement}=\sqrt{{1-{function}^2}}="
                    rf"\sqrt{{1-({trig})^2}}={complement_latex}",
                    rf"{complement}=\frac{{{known}}}{{{denominator}}}"
                    rf"\iff {denominator}=\frac{{{known}}}{{{complement}}}="
                    rf"\frac{{{values.known_latex}}}{{{complement_latex}}}="
                    rf"{side_latex[denominator]}",
                ]
            )
            if requested == numerator:
                rows.append(
                    definition
                    + rf"\iff {numerator}={denominator}\cdot{function}="
                    rf"{side_latex[denominator]}\cdot {trig}={side_latex[numerator]}"
                )
            elif requested != denominator:
                raise RightTrianglePlanError("requested side is outside normalized triangle roles")
            return _universal_solution_rows_transformation(rows)
        rows.append(definition)
        sign = "-" if denominator == values.hypotenuse else "+"
        rows.append(
            rf"{denominator}=\frac{{{known}}}{{\sqrt{{1{sign}({function})^2}}}}="
            rf"\frac{{{values.known_latex}}}{{\sqrt{{1{sign}({trig})^2}}}}="
            rf"{side_latex[denominator]}"
        )
        if requested == numerator:
            rows.append(
                rf"{numerator}={denominator}\cdot{function}="
                rf"{side_latex[denominator]}\cdot {trig}={side_latex[numerator]}"
            )
        elif requested != denominator:
            raise RightTrianglePlanError("requested side is outside normalized triangle roles")
    return _universal_solution_rows_transformation(rows)


def _universal_solution_rows_transformation(rows: list[str]) -> dict[str, Any]:
    """Wrap verified universal formula rows in one solution transformation."""

    html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-universal" '
        'data-solution-title="Решение">'
        '<p>По определению тригонометрической функции:</p>'
        + "".join(
            '<center><p><span data-inline-latex="'
            + row
            + '"></span></p></center>'
            for row in rows
        )
        + "</section>"
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": "add",
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _universal_trig_request_solution_transformation(
    values: UniversalTrigRequestValues,
    *,
    side_latex: dict[str, str],
    missing_side: str,
    answer: str,
) -> dict[str, Any]:
    """Build two or three concise rows for a requested trig value."""

    rows: list[str] = []
    if (
        missing_side == values.hypotenuse
        and missing_side in {values.numerator_side, values.denominator_side}
    ):
        legs = sorted({"AB", "AC", "BC"} - {values.hypotenuse})
        rows.append(
            rf"{values.hypotenuse}=\sqrt{{{legs[0]}^{{2}}+{legs[1]}^{{2}}}}="
            rf"\sqrt{{({side_latex[legs[0]]})^{{2}}+({side_latex[legs[1]]})^{{2}}}}="
            rf"{side_latex[values.hypotenuse]}"
        )
    elif missing_side in {values.numerator_side, values.denominator_side}:
        other_leg = ({"AB", "AC", "BC"} - {values.hypotenuse, missing_side}).pop()
        rows.append(
            rf"{missing_side}=\sqrt{{{values.hypotenuse}^{{2}}-{other_leg}^{{2}}}}="
            rf"\sqrt{{({side_latex[values.hypotenuse]})^{{2}}-({side_latex[other_leg]})^{{2}}}}="
            rf"{side_latex[missing_side]}"
        )
    function = rf"\{values.trig_name} {values.trig_angle}"
    rows.append(
        rf"{function}=\frac{{{values.numerator_side}}}{{{values.denominator_side}}}="
        rf"\frac{{{side_latex[values.numerator_side]}}}"
        rf"{{{side_latex[values.denominator_side]}}}="
        + answer.replace(",", "{,}")
    )
    html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-universal" '
        'data-solution-title="Решение">'
        '<p>Используем соотношения сторон прямоугольного треугольника:</p>'
        + "".join(
            '<center><p><span data-inline-latex="'
            + row
            + '"></span></p></center>'
            for row in rows
        )
        + "</section>"
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": "add",
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def build_tangent_bc_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
) -> RepairPlan:
    """Return strict AC-and-tangent repairs for tasks requesting BC."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    trig_name, trig_latex, known_side, known, requested = _latex_values(
        str(condition.get("html") or "")
    )
    if trig_name != "tg":
        raise RightTrianglePlanError("condition must use tg A")
    if requested != "BC":
        raise RightTrianglePlanError("condition must request BC")
    if known_side != "AC":
        raise RightTrianglePlanError("condition must give AC")
    tangent_squared = _trig_square(trig_latex)
    if tangent_squared <= 0:
        raise RightTrianglePlanError("tg A must be positive")
    known_squared = _numeric_square_latex(known)
    bc_squared = known_squared * tangent_squared
    bc_latex = _positive_root_number_latex(bc_squared)
    answer = _answer_text(math.sqrt(float(bc_squared)))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if not isinstance(current_asset, dict) or current_asset.get("asset_id") != parent_asset_id:
        transformations.append(_asset_transformation(parent_asset_id))
    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    desired_solution = _tangent_bc_solution_transformation(
        trig_latex,
        known,
        bc_latex,
        answer,
    )
    if solution is None or not _plain_html(solution_html):
        transformations.append(desired_solution)
    elif (
        'data-content-rule="right-triangle-tangent-opposite-cathetus"'
        in solution_html
        and solution_html != desired_solution["value"]["html"]
    ):
        transformations.append(
            _tangent_bc_solution_transformation(
                trig_latex,
                known,
                bc_latex,
                answer,
                operation="rewrite",
            )
        )
    if (
        answer_section is None
        or _plain_html(str(answer_section.get("html") or "")) != answer
    ):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))
