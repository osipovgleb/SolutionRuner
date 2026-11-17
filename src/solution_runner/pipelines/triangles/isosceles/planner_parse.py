"""Parse and format exact values in isosceles-triangle conditions."""

from __future__ import annotations

import math
import re
from html import unescape

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError


def _formula_text(value: str) -> str:
    """Restore inline LaTeX attributes into their visible source positions."""

    value = value.replace("\u00ad", "")
    restored = re.sub(
        r'<[^>]*\bdata-inline-latex=["\']([^"\']*)["\'][^>]*>.*?</[^>]+>',
        lambda match: " " + unescape(match.group(1)) + " ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", restored))).strip()


def _split_braced(value: str, start: int) -> tuple[str, int]:
    """Return one balanced braced token and the first following position."""

    if start >= len(value) or value[start] != "{":
        raise IsoscelesTrianglePlanError("unsupported exact value")
    depth = 0
    for index in range(start, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                return value[start + 1 : index], index + 1
    raise IsoscelesTrianglePlanError("unbalanced exact value")


def _parse_positive_value(value: str) -> sp.Expr:
    """Parse a positive rational or one quadratic-radical LaTeX value."""

    compact = (
        value.replace(r"\left", "")
        .replace(r"\right", "")
        .replace(" ", "")
        .replace("{,}", ".")
        .replace(",", ".")
    )
    if compact.startswith(r"\frac"):
        numerator, next_index = _split_braced(compact, len(r"\frac"))
        denominator, final_index = _split_braced(compact, next_index)
        if final_index != len(compact):
            raise IsoscelesTrianglePlanError(f"unsupported exact value: {value}")
        parsed = _parse_positive_value(numerator) / _parse_positive_value(denominator)
    else:
        radical = re.fullmatch(r"(\d+(?:\.\d+)?)?\\sqrt\{(\d+)\}", compact)
        if radical is not None:
            parsed = sp.Rational(radical.group(1) or "1") * sp.sqrt(
                int(radical.group(2))
            )
        elif re.fullmatch(r"\d+(?:\.\d+)?", compact):
            parsed = sp.Rational(compact)
        else:
            raise IsoscelesTrianglePlanError(f"unsupported exact value: {value}")
    parsed = sp.simplify(parsed)
    if parsed.is_real is not True or parsed.is_positive is not True:
        raise IsoscelesTrianglePlanError("condition values must be positive")
    return parsed


def _latex_number(value: sp.Expr) -> str:
    """Render one exact positive expression in compact LaTeX form."""

    return sp.latex(sp.simplify(value)).replace(r" \sqrt", r"\sqrt")


def _answer_text(value: sp.Expr) -> str:
    """Render one finite result with the source's decimal-comma convention."""

    numeric = float(sp.N(value, 15))
    if not math.isfinite(numeric):
        raise IsoscelesTrianglePlanError("computed answer is not finite")
    rounded = round(numeric, 10)
    if math.isclose(rounded, round(rounded), abs_tol=1e-9):
        return str(round(rounded))
    return f"{rounded:.10f}".rstrip("0").rstrip(".").replace(".", ",")


def _parse_base_from_sine(condition_html: str) -> tuple[sp.Expr, str, sp.Expr, str]:
    """Return equal side, base angle, sine value, and its source LaTeX."""

    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    requested = formula.split("Найд", 1)[-1] if "Найд" in formula else ""
    if not re.search(r"\bAB\b", requested) or re.search(
        r"\b(?:AC|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AB")
    side_match = re.search(r"(?:AC\s*=\s*BC|BC\s*=\s*AC)\s*=\s*([^,;.]+)", formula)
    sine_match = re.search(r"\\sin\s*([AB])\s*=\s*([^,;.]+)", formula)
    if side_match is None or sine_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and sin A or sin B")
    side_latex = side_match.group(1).strip()
    sine_latex = sine_match.group(2).strip()
    side = _parse_positive_value(side_latex)
    sine = _parse_positive_value(sine_latex)
    if sp.simplify(1 - sine**2).is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    return side, sine_match.group(1), sine, sine_latex


def _inline_formulas(value: str) -> tuple[str, ...]:
    """Return decoded inline LaTeX values in document order."""

    return tuple(
        unescape(match)
        for match in re.findall(
            r'\bdata-inline-latex=["\']([^"\']*)["\']',
            value,
            flags=re.IGNORECASE,
        )
    )


def _parse_equal_side_from_base_and_sine(
    condition_html: str,
) -> tuple[sp.Expr, sp.Expr, str]:
    """Return the known base and sine for the strict group-27285 contract."""

    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    requested = formula.split("Найд", 1)[-1] if "Найд" in formula else ""
    if not re.search(r"\bAC\b", requested) or re.search(
        r"\b(?:AB|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AC")
    if re.search(r"(?:AC\s*=\s*BC|BC\s*=\s*AC)", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    inline = _inline_formulas(condition_html)
    base_latex = next(
        (item.split("=", 1)[1].strip() for item in inline if item.startswith("AB=")),
        "",
    )
    if not base_latex:
        base_match = re.search(
            r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
            r"\d+(?:\{,\}\d+|[.,]\d+)?)",
            formula,
        )
        base_latex = base_match.group(1) if base_match is not None else ""
    sine_latex = next(
        (
            item.split("=", 1)[1].strip()
            for item in inline
            if re.match(r"\\sin\s*A\s*=", item)
        ),
        "",
    )
    if not base_latex or not sine_latex:
        raise IsoscelesTrianglePlanError("condition must give AB and sin A")
    base = _parse_positive_value(base_latex)
    sine = _parse_positive_value(sine_latex)
    if sp.simplify(1 - sine**2).is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    return base, sine, sine_latex


def _request_text(condition_html: str) -> str:
    """Return the normalized tail beginning at the source's request verb."""

    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    return formula.split("Найд", 1)[-1] if "Найд" in formula else ""


def _inline_assignment(condition_html: str, pattern: str) -> str:
    """Return the right-hand side of one uniquely matched inline assignment."""

    matches = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(pattern, item)
    ]
    if len(matches) != 1:
        raise IsoscelesTrianglePlanError("condition assignment is missing or ambiguous")
    return matches[0]
