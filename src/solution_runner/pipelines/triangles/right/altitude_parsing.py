"""Parse supported right-triangle altitude conditions and exact values."""

from __future__ import annotations

import re
import unicodedata
from html import unescape

import sympy as sp

from .altitude_types import _LENGTHS, AltitudeSolveError, _Fact


def _visible_text(value: str) -> str:
    """Return normalized visible text with visually identical labels unified."""

    decoded = unicodedata.normalize("NFKC", unescape(value)).replace("\u00ad", "")
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", decoded)).strip()

    def latin_label(match: re.Match[str]) -> str:
        return match.group(0).translate(
            str.maketrans({"А": "A", "В": "B", "С": "C", "Н": "H"})
        )

    return re.sub(r"\b[АВСН]{1,3}\b", latin_label, plain)


def _normalized_formula(value: str) -> str:
    """Normalize source aliases while preserving the displayable exact value."""

    normalized = (
        unescape(value)
        .strip()
        .translate(str.maketrans({"А": "A", "В": "B", "С": "C", "Н": "H"}))
    )
    return (
        normalized.replace(r"\operatorname{tg}", r"\tg")
        .replace(r"\mathrm{tg}\,", r"\tg ")
        .replace(r"\tan", r"\tg")
        .replace(r"\left", "")
        .replace(r"\right", "")
    )


def _split_braced(value: str, start: int) -> tuple[str, int]:
    """Return one balanced braced token and the first index after it."""

    if start >= len(value) or value[start] != "{":
        raise AltitudeSolveError("unsupported exact value")
    depth = 0
    for index in range(start, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                return value[start + 1 : index], index + 1
    raise AltitudeSolveError("unbalanced exact value")


def _parse_positive_value(value: str) -> sp.Expr:
    """Parse one supported positive rational or quadratic-radical LaTeX value."""

    compact = (
        _normalized_formula(value)
        .replace(" ", "")
        .replace("{,}", ".")
        .replace(",", ".")
    )
    if compact.startswith(r"\frac"):
        numerator, next_index = _split_braced(compact, len(r"\frac"))
        denominator, final_index = _split_braced(compact, next_index)
        if final_index != len(compact):
            raise AltitudeSolveError(f"unsupported exact value: {value}")
        parsed = _parse_positive_value(numerator) / _parse_positive_value(denominator)
    else:
        radical = re.fullmatch(r"(\d+(?:\.\d+)?)?\\sqrt\{(\d+)\}", compact)
        if radical is not None:
            coefficient = sp.Rational(radical.group(1) or "1")
            parsed = coefficient * sp.sqrt(int(radical.group(2)))
        elif re.fullmatch(r"\d+(?:\.\d+)?", compact):
            parsed = sp.Rational(compact)
        else:
            raise AltitudeSolveError(f"unsupported exact value: {value}")
    parsed = sp.simplify(parsed)
    if parsed.is_real is not True or parsed.is_positive is not True:
        raise AltitudeSolveError("condition values must be positive real numbers")
    return parsed


def _extract_condition(condition_html: str) -> tuple[dict[str, _Fact], str]:
    """Extract all exact known quantities and exactly one requested quantity."""

    visible = _visible_text(condition_html)
    formula_cells = [
        _normalized_formula(value)
        for value in re.findall(
            r'data-inline-latex="([^"]+)"', unescape(condition_html)
        )
    ]
    formulas = [
        part.strip(" ,")
        for cell in formula_cells
        for part in re.split(r"\\quad", cell)
        if part.strip(" ,")
    ]
    formula_declares_right_angle = any(
        re.fullmatch(
            r"(?:\\angleC=)?90(?:\^\{?\\circ\}?)?",
            value.replace(" ", ""),
        )
        for value in formulas
    )
    if not re.search(r"угол\s+C\s+равен\s+90", visible, re.IGNORECASE) and not (
        formula_declares_right_angle
        and (
            re.search(r"угол\s+C\s+равен", visible, re.IGNORECASE)
            or any(value.replace(" ", "").startswith(r"\angleC=") for value in formulas)
        )
    ):
        raise AltitudeSolveError("condition must declare angle C equal to 90 degrees")

    facts, bare_requests = _formula_facts(formulas)
    _merge_text_facts(condition_html, visible, facts)
    requested = _requested_quantity(visible, facts, bare_requests)
    return facts, requested


def _formula_facts(formulas: list[str]) -> tuple[dict[str, _Fact], list[str]]:
    """Read known values and bare requests from normalized formula cells."""

    facts: dict[str, _Fact] = {}
    bare_requests: list[str] = []
    for formula in formulas:
        compact = formula.replace(" ", "")
        known = re.fullmatch(r"(AB|AC|BC|AH|BH|CH)=(.+)", compact)
        if known is not None:
            quantity, raw = known.groups()
            value = _parse_positive_value(raw)
            if quantity in facts and sp.simplify(facts[quantity].value - value) != 0:
                raise AltitudeSolveError(f"inconsistent {quantity}")
            facts[quantity] = _Fact(value=value, latex=raw, derivation=None)
            continue
        trig = re.fullmatch(r"\\(sin|cos|tg)(A|B)=(.+)", compact)
        if trig is not None:
            quantity = trig.group(1) + trig.group(2)
            raw = trig.group(3)
            value = _parse_positive_value(raw)
            if quantity.startswith(("sin", "cos")) and not value < 1:
                raise AltitudeSolveError(f"{quantity} must be between zero and one")
            facts[quantity] = _Fact(value=value, latex=raw, derivation=None)
            continue
        if compact in _LENGTHS:
            bare_requests.append(compact)
            continue
        request = re.fullmatch(r"\\(sin|cos|tg)(A|B)", compact)
        if request is not None:
            bare_requests.append(request.group(1) + request.group(2))

    return facts, bare_requests


def _merge_text_facts(
    condition_html: str, visible: str, facts: dict[str, _Fact]
) -> None:
    """Add known segment values represented in supported HTML and prose forms."""

    for quantity, raw in re.findall(
        r'data-math-identifier="(AB|AC|BC|AH|BH|CH)"[^>]*>[^<]*</var>'
        r'\s*(?:=|равн[ао])\s*<span\s+data-inline-latex="([^"]+)"',
        condition_html,
        re.IGNORECASE,
    ):
        quantity = quantity.upper()
        if quantity in facts:
            continue
        normalized = _normalized_formula(raw)
        facts[quantity] = _Fact(
            value=_parse_positive_value(normalized),
            latex=normalized,
            derivation=None,
        )

    for quantity, raw in re.findall(
        r'data-inline-latex="[^"]*\b(AB|AC|BC|AH|BH|CH)='
        r'\s*"></span>\s*(\d+(?:[,.]\d+)?)',
        condition_html,
        re.IGNORECASE,
    ):
        quantity = quantity.upper()
        if quantity in facts:
            continue
        normalized = raw.replace(",", "{,}")
        facts[quantity] = _Fact(
            value=_parse_positive_value(normalized),
            latex=normalized,
            derivation=None,
        )

    for quantity, raw in re.findall(
        r"\b(AB|AC|BC|AH|BH|CH)\s*(?:=|равн[ао])\s*(\d+(?:[,.]\d+)?)",
        visible,
        re.IGNORECASE,
    ):
        if quantity in facts:
            continue
        normalized = raw.replace(",", "{,}")
        facts[quantity] = _Fact(
            value=_parse_positive_value(normalized),
            latex=normalized,
            derivation=None,
        )


def _requested_quantity(
    visible: str, facts: dict[str, _Fact], bare_requests: list[str]
) -> str:
    """Resolve one requested quantity and verify the altitude declaration."""

    visible_request = re.search(
        r"Найдите(?:\s+длину)?(?:\s+отрезка)?\s+(AB|AC|BC|AH|BH|CH)\b",
        visible,
        re.IGNORECASE,
    )
    if visible_request is not None:
        bare_requests.append(visible_request.group(1).upper())
    visible_height_request = re.search(
        r"Найдите\s+высот[ау]\s+(AB|AC|BC|AH|BH|CH)\b",
        visible,
        re.IGNORECASE,
    )
    if visible_height_request is not None:
        bare_requests.append(visible_height_request.group(1).upper())
    visible_trig_request = re.search(
        r"Найдите\s+\\(sin|cos|tg)\s*(A|B)\b",
        visible,
        re.IGNORECASE,
    )
    if visible_trig_request is not None:
        bare_requests.append(
            visible_trig_request.group(1).lower()
            + visible_trig_request.group(2).upper()
        )
    requests = list(dict.fromkeys(bare_requests))
    if len(requests) != 1:
        raise AltitudeSolveError(
            "condition must request exactly one supported quantity"
        )
    requested = requests[0]
    if requested in facts:
        raise AltitudeSolveError("requested quantity is already given")
    altitude_used = requested in {"AH", "BH", "CH"} or any(
        quantity in facts for quantity in ("AH", "BH", "CH")
    )
    altitude_declared = bool(
        re.search(r"CH\s*[—–−-]?\s*высот[ау]", visible, re.IGNORECASE)
        or re.search(r"высот[ау]\s+CH", visible, re.IGNORECASE)
        or requested == "CH"
    )
    if altitude_used and not altitude_declared:
        raise AltitudeSolveError("condition must declare CH as the altitude")
    if not facts:
        raise AltitudeSolveError("condition contains no supported known quantities")
    return requested
