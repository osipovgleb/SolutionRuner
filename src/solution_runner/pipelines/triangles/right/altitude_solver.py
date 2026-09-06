"""Infer exact right-triangle altitude quantities and render their proof rows."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from html import unescape
import math
import re
import unicodedata

import sympy as sp


class AltitudeSolveError(ValueError):
    """Report an ambiguous, inconsistent, or unsupported altitude condition."""


@dataclass(frozen=True)
class AltitudeSolution:
    """Hold one exact requested value and its dependency-ordered formula rows."""

    requested: str
    exact_value: sp.Expr
    answer: str
    rows: tuple[str, ...]


@dataclass(frozen=True)
class _Derivation:
    """Describe the exact facts and display rows used to infer one quantity."""

    inputs: tuple[str, ...]
    rows: tuple[str, ...]


@dataclass(frozen=True)
class _Fact:
    """Store one positive exact value, display form, and optional derivation."""

    value: sp.Expr
    latex: str
    derivation: _Derivation | None


_LENGTHS = ("AB", "AC", "BC", "AH", "BH", "CH")
_TRIG = ("sinA", "cosA", "tgA", "sinB", "cosB", "tgB")
_QUANTITIES = set(_LENGTHS + _TRIG)
_RATIOS = (
    ("sinA", "BC", "AB"),
    ("sinA", "CH", "AC"),
    ("sinA", "BH", "BC"),
    ("cosA", "AC", "AB"),
    ("cosA", "AH", "AC"),
    ("cosA", "CH", "BC"),
    ("tgA", "BC", "AC"),
    ("tgA", "CH", "AH"),
    ("tgA", "BH", "CH"),
    ("sinB", "AC", "AB"),
    ("sinB", "AH", "AC"),
    ("sinB", "CH", "BC"),
    ("cosB", "BC", "AB"),
    ("cosB", "CH", "AC"),
    ("cosB", "BH", "BC"),
    ("tgB", "AC", "BC"),
    ("tgB", "AH", "CH"),
    ("tgB", "CH", "BH"),
)
_PYTHAGOREAN = (
    ("AB", "AC", "BC"),
    ("AC", "AH", "CH"),
    ("BC", "BH", "CH"),
)
_TANGENT_HYPOTENUSE = (
    ("AB", "BC", "AC"),
    ("AC", "CH", "AH"),
    ("BC", "BH", "CH"),
)
_RATIO_VARIABLES = {
    ("BC", "AB"): "x",
    ("AC", "AB"): "x",
    ("BC", "AC"): "x",
    ("CH", "AC"): "y",
    ("AH", "AC"): "y",
    ("CH", "AH"): "y",
    ("BH", "BC"): "z",
    ("CH", "BC"): "z",
    ("BH", "CH"): "z",
    ("AC", "BC"): "x",
    ("AH", "CH"): "y",
    ("CH", "BH"): "z",
}


def _visible_text(value: str) -> str:
    """Return normalized visible text with visually identical labels unified."""

    decoded = unicodedata.normalize("NFKC", unescape(value)).replace("\u00ad", "")
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", decoded)).strip()

    def latin_label(match: re.Match[str]) -> str:
        return match.group(0).translate(str.maketrans({"А": "A", "В": "B", "С": "C", "Н": "H"}))

    return re.sub(r"\b[АВСН]{1,3}\b", latin_label, plain)


def _normalized_formula(value: str) -> str:
    """Normalize source aliases while preserving the displayable exact value."""

    normalized = unescape(value).strip().translate(
        str.maketrans({"А": "A", "В": "B", "С": "C", "Н": "H"})
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

    compact = _normalized_formula(value).replace(" ", "").replace("{,}", ".").replace(",", ".")
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


def _latex_number(value: sp.Expr) -> str:
    """Render one exact positive value with stable compact multiplication."""

    return sp.latex(sp.simplify(value)).replace(r" \sqrt", r"\sqrt")


def _answer_text(value: sp.Expr) -> str:
    """Render one finite numeric answer using the source's decimal comma."""

    numeric = float(sp.N(value, 15))
    if not math.isfinite(numeric):
        raise AltitudeSolveError("computed answer is not finite")
    rounded = round(numeric, 10)
    if math.isclose(rounded, round(rounded), abs_tol=1e-9):
        return str(round(rounded))
    return f"{rounded:.10f}".rstrip("0").rstrip(".").replace(".", ",")


def _function_latex(quantity: str) -> str:
    """Return the canonical LaTeX name for one trigonometric quantity."""

    return {
        "sinA": r"\sin A",
        "cosA": r"\cos A",
        "tgA": r"\tg A",
        "sinB": r"\sin B",
        "cosB": r"\cos B",
        "tgB": r"\tg B",
    }[quantity]


def _fact_latex(facts: dict[str, _Fact], quantity: str) -> str:
    """Return the preserved or derived display value for one known quantity."""

    return facts[quantity].latex


def _coefficient_term(coefficient: sp.Expr, variable: str) -> str:
    """Render a positive coefficient times one proportionality variable."""

    return variable if _same(coefficient, sp.Integer(1)) else _latex_number(coefficient) + variable


def _squared_display(value: str) -> str:
    """Parenthesize a compound exact value before applying a square."""

    return (
        value + "^2"
        if re.fullmatch(r"(?:\d+(?:\{,\}\d+)?|[xyz])", value)
        else f"({value})^2"
    )


def _proportion_parts(
    facts: dict[str, _Fact],
    function: str,
    numerator: str,
    denominator: str,
) -> tuple[str, sp.Expr, sp.Expr, str, str, str]:
    """Return the approved coefficient representation for one known function."""

    variable = _RATIO_VARIABLES[(numerator, denominator)]
    numerator_coefficient, denominator_coefficient = sp.fraction(
        sp.together(facts[function].value)
    )
    numerator_term = _coefficient_term(numerator_coefficient, variable)
    denominator_term = _coefficient_term(denominator_coefficient, variable)
    row = (
        rf"{_function_latex(function)}={_fact_latex(facts, function)}="
        rf"\frac{{{numerator_term}}}{{{denominator_term}}}="
        rf"\frac{{{numerator}}}{{{denominator}}}"
        rf"\Longrightarrow {numerator}={numerator_term},\ {denominator}={denominator_term}"
    )
    return (
        variable,
        numerator_coefficient,
        denominator_coefficient,
        numerator_term,
        denominator_term,
        row,
    )


def _extract_condition(condition_html: str) -> tuple[dict[str, _Fact], str]:
    """Extract all exact known quantities and exactly one requested quantity."""

    visible = _visible_text(condition_html)
    formula_cells = [
        _normalized_formula(value)
        for value in re.findall(r'data-inline-latex="([^"]+)"', unescape(condition_html))
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
        raise AltitudeSolveError("condition must request exactly one supported quantity")
    requested = requests[0]
    if requested in facts:
        raise AltitudeSolveError("requested quantity is already given")
    altitude_used = requested in {"AH", "BH", "CH"} or any(
        quantity in facts for quantity in {"AH", "BH", "CH"}
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
    return facts, requested


def _same(left: sp.Expr, right: sp.Expr) -> bool:
    """Return exact symbolic equality for two supported positive expressions."""

    return sp.simplify(left - right) == 0


def _assign(
    facts: dict[str, _Fact],
    quantity: str,
    value: sp.Expr,
    derivation: _Derivation,
) -> bool:
    """Store one inference or reject disagreement with an existing exact fact."""

    value = sp.simplify(value)
    if value.is_real is not True or value.is_positive is not True:
        raise AltitudeSolveError(f"derived {quantity} is not positive")
    existing = facts.get(quantity)
    if existing is not None:
        if not _same(existing.value, value):
            raise AltitudeSolveError(f"inconsistent {quantity}")
        return False
    facts[quantity] = _Fact(
        value=value,
        latex=_latex_number(value),
        derivation=derivation,
    )
    return True


def _apply_ratio(facts: dict[str, _Fact], function: str, numerator: str, denominator: str) -> bool:
    """Infer the only missing member of one trigonometric side ratio."""

    known = {quantity for quantity in (function, numerator, denominator) if quantity in facts}
    if len(known) < 2:
        return False
    function_latex = _function_latex(function)
    definition = rf"{function_latex}=\frac{{{numerator}}}{{{denominator}}}"
    if function not in facts:
        value = facts[numerator].value / facts[denominator].value
        row = (
            definition
            + rf"=\frac{{{_fact_latex(facts, numerator)}}}{{{_fact_latex(facts, denominator)}}}="
            + _latex_number(value)
        )
        return _assign(facts, function, value, _Derivation((numerator, denominator), (row,)))
    if numerator not in facts:
        value = facts[denominator].value * facts[function].value
        if facts[denominator].derivation is not None:
            row = (
                definition
                + rf"\Longrightarrow {numerator}={denominator}{function_latex}="
                rf"{_fact_latex(facts, denominator)}\cdot"
                rf"{_fact_latex(facts, function)}={_latex_number(value)}"
            )
            return _assign(
                facts,
                numerator,
                value,
                _Derivation((denominator, function), (row,)),
            )
        variable, num_coefficient, den_coefficient, num_term, den_term, setup = (
            _proportion_parts(facts, function, numerator, denominator)
        )
        scale = sp.simplify(facts[denominator].value / den_coefficient)
        source_derivation = facts[denominator].derivation
        rows = (
            (rf"{numerator}={num_term}={_latex_number(value)}",)
            if source_derivation is not None and setup in source_derivation.rows
            else (
                setup,
                rf"{denominator}={_fact_latex(facts, denominator)}={den_term}"
                rf"\Longrightarrow {variable}={_latex_number(scale)}",
                rf"{numerator}={num_term}={_latex_number(value)}",
            )
        )
        return _assign(facts, numerator, value, _Derivation((denominator, function), rows))
    if denominator not in facts:
        value = facts[numerator].value / facts[function].value
        if facts[numerator].derivation is not None:
            row = (
                definition
                + rf"\Longrightarrow {denominator}=\frac{{{numerator}}}{{{function_latex}}}="
                rf"\frac{{{_fact_latex(facts, numerator)}}}"
                rf"{{{_fact_latex(facts, function)}}}={_latex_number(value)}"
            )
            return _assign(
                facts,
                denominator,
                value,
                _Derivation((numerator, function), (row,)),
            )
        variable, num_coefficient, den_coefficient, num_term, den_term, setup = (
            _proportion_parts(facts, function, numerator, denominator)
        )
        scale = sp.simplify(facts[numerator].value / num_coefficient)
        source_derivation = facts[numerator].derivation
        rows = (
            (rf"{denominator}={den_term}={_latex_number(value)}",)
            if source_derivation is not None and setup in source_derivation.rows
            else (
                setup,
                rf"{numerator}={_fact_latex(facts, numerator)}={num_term}"
                rf"\Longrightarrow {variable}={_latex_number(scale)}",
                rf"{denominator}={den_term}={_latex_number(value)}",
            )
        )
        return _assign(facts, denominator, value, _Derivation((numerator, function), rows))
    expected = facts[numerator].value / facts[denominator].value
    if not _same(facts[function].value, expected):
        raise AltitudeSolveError(f"inconsistent {function}")
    return False


def _apply_pythagoras(facts: dict[str, _Fact], hypotenuse: str, leg_a: str, leg_b: str) -> bool:
    """Infer or verify one side through the Pythagorean theorem."""

    quantities = (hypotenuse, leg_a, leg_b)
    known = [quantity for quantity in quantities if quantity in facts]
    if len(known) < 2:
        return False
    if hypotenuse not in facts:
        value = sp.sqrt(facts[leg_a].value**2 + facts[leg_b].value**2)
        row = (
            rf"{hypotenuse}=\sqrt{{{leg_a}^2+{leg_b}^2}}="
            rf"\sqrt{{({_fact_latex(facts, leg_a)})^2+({_fact_latex(facts, leg_b)})^2}}="
            + _latex_number(value)
        )
        return _assign(facts, hypotenuse, value, _Derivation((leg_a, leg_b), (row,)))
    missing = leg_a if leg_a not in facts else leg_b if leg_b not in facts else None
    if missing is not None:
        other = leg_b if missing == leg_a else leg_a
        square = sp.simplify(facts[hypotenuse].value**2 - facts[other].value**2)
        if square.is_positive is not True:
            raise AltitudeSolveError(f"inconsistent {hypotenuse}")
        value = sp.sqrt(square)
        row = (
            rf"{missing}=\sqrt{{{hypotenuse}^2-{other}^2}}="
            rf"\sqrt{{({_fact_latex(facts, hypotenuse)})^2-({_fact_latex(facts, other)})^2}}="
            + _latex_number(value)
        )
        return _assign(facts, missing, value, _Derivation((hypotenuse, other), (row,)))
    expected = facts[leg_a].value**2 + facts[leg_b].value**2
    if not _same(facts[hypotenuse].value**2, expected):
        raise AltitudeSolveError(f"inconsistent {leg_b}")
    return False


def _apply_trig_pythagorean_scale(
    facts: dict[str, _Fact],
    function: str,
    numerator: str,
    denominator: str,
) -> bool:
    """Infer a ratio's two sides from its third side without changing function."""

    if function not in facts or numerator in facts or denominator in facts:
        return False
    triangle = next(
        (
            (hypotenuse, leg_a, leg_b)
            for hypotenuse, leg_a, leg_b in _PYTHAGOREAN
            if {numerator, denominator}.issubset({hypotenuse, leg_a, leg_b})
        ),
        None,
    )
    if triangle is None:
        return False
    hypotenuse, leg_a, leg_b = triangle
    third = ({hypotenuse, leg_a, leg_b} - {numerator, denominator}).pop()
    if third not in facts:
        return False

    variable, numerator_coefficient, denominator_coefficient, numerator_term, denominator_term, setup = (
        _proportion_parts(facts, function, numerator, denominator)
    )
    coefficient_by_side = {
        numerator: numerator_coefficient,
        denominator: denominator_coefficient,
    }
    if hypotenuse == denominator:
        third_coefficient = sp.sqrt(
            denominator_coefficient**2 - numerator_coefficient**2
        )
    elif hypotenuse == numerator:
        third_coefficient = sp.sqrt(
            numerator_coefficient**2 - denominator_coefficient**2
        )
    else:
        third_coefficient = sp.sqrt(
            numerator_coefficient**2 + denominator_coefficient**2
        )
    third_coefficient = sp.simplify(third_coefficient)
    if third_coefficient.is_real is not True or third_coefficient.is_positive is not True:
        raise AltitudeSolveError(f"inconsistent {function}")
    coefficient_by_side[third] = third_coefficient
    scale = sp.simplify(facts[third].value / third_coefficient)
    term_by_side = {
        numerator: numerator_term,
        denominator: denominator_term,
        third: _coefficient_term(third_coefficient, variable),
    }
    displayed_by_side = dict(term_by_side)
    displayed_by_side[third] = _fact_latex(facts, third)
    equation = (
        rf"{_squared_display(displayed_by_side[hypotenuse])}="
        rf"{_squared_display(displayed_by_side[leg_a])}+"
        rf"{_squared_display(displayed_by_side[leg_b])}"
        rf"\Longrightarrow {variable}={_latex_number(scale)}"
    )
    identity = rf"{hypotenuse}^2={leg_a}^2+{leg_b}^2"
    changed = False
    for quantity in (numerator, denominator):
        value = sp.simplify(coefficient_by_side[quantity] * scale)
        rows = (
            setup,
            identity,
            equation,
            rf"{quantity}={term_by_side[quantity]}={_latex_number(value)}",
        )
        changed = (
            _assign(
                facts,
                quantity,
                value,
                _Derivation((function, third), rows),
            )
            or changed
        )
    return changed


def _apply_sum(facts: dict[str, _Fact]) -> bool:
    """Infer or verify the two altitude projections on hypotenuse AB."""

    known = {quantity for quantity in ("AB", "AH", "BH") if quantity in facts}
    if len(known) < 2:
        return False
    if "AB" not in facts:
        value = facts["AH"].value + facts["BH"].value
        row = rf"AB=AH+BH={_fact_latex(facts, 'AH')}+{_fact_latex(facts, 'BH')}={_latex_number(value)}"
        return _assign(facts, "AB", value, _Derivation(("AH", "BH"), (row,)))
    missing = "AH" if "AH" not in facts else "BH" if "BH" not in facts else None
    if missing is not None:
        other = "BH" if missing == "AH" else "AH"
        value = facts["AB"].value - facts[other].value
        row = rf"{missing}=AB-{other}={_fact_latex(facts, 'AB')}-{_fact_latex(facts, other)}={_latex_number(value)}"
        return _assign(facts, missing, value, _Derivation(("AB", other), (row,)))
    if not _same(facts["AB"].value, facts["AH"].value + facts["BH"].value):
        raise AltitudeSolveError("inconsistent AB")
    return False


def _apply_identity(facts: dict[str, _Fact]) -> bool:
    """Infer only sine from cosine or cosine from sine through the basic identity."""

    if "sinA" in facts and "cosA" not in facts:
        value = sp.sqrt(1 - facts["sinA"].value**2)
        row = (
            r"\cos A=\sqrt{1-(\sin A)^2}="
            rf"\sqrt{{1-({_fact_latex(facts, 'sinA')})^2}}={_latex_number(value)}"
        )
        return _assign(facts, "cosA", value, _Derivation(("sinA",), (row,)))
    if "cosA" in facts and "sinA" not in facts:
        value = sp.sqrt(1 - facts["cosA"].value**2)
        row = (
            r"\sin A=\sqrt{1-(\cos A)^2}="
            rf"\sqrt{{1-({_fact_latex(facts, 'cosA')})^2}}={_latex_number(value)}"
        )
        return _assign(facts, "sinA", value, _Derivation(("cosA",), (row,)))
    if "sinA" in facts and "cosA" in facts:
        if not _same(facts["sinA"].value**2 + facts["cosA"].value**2, sp.Integer(1)):
            raise AltitudeSolveError("inconsistent sinA and cosA")
    return False


def _apply_tangent_hypotenuse(
    facts: dict[str, _Fact],
    hypotenuse: str,
    numerator: str,
    denominator: str,
) -> bool:
    """Use tangent substitution in Pythagoras without a tangent identity."""

    if "tgA" not in facts or hypotenuse not in facts or denominator in facts:
        return False
    tangent = facts["tgA"].value
    denominator_value = sp.simplify(
        facts[hypotenuse].value / sp.sqrt(1 + tangent**2)
    )
    variable, _num_coefficient, den_coefficient, num_term, den_term, setup = (
        _proportion_parts(facts, "tgA", numerator, denominator)
    )
    scale = sp.simplify(denominator_value / den_coefficient)
    rows = (
        setup,
        rf"{hypotenuse}^2={denominator}^2+{numerator}^2",
        (
            rf"{_squared_display(_fact_latex(facts, hypotenuse))}="
            rf"{_squared_display(den_term)}+{_squared_display(num_term)}"
            rf"\Longrightarrow {variable}={_latex_number(scale)}"
        ),
        rf"{denominator}={den_term}={_latex_number(denominator_value)}",
    )
    return _assign(
        facts,
        denominator,
        denominator_value,
        _Derivation((hypotenuse, "tgA"), rows),
    )


def _proof_rows(facts: dict[str, _Fact], requested: str) -> tuple[str, ...]:
    """Return dependency-ordered rows needed for the selected requested fact."""

    rows: list[str] = []
    visited: set[str] = set()

    def visit(quantity: str) -> None:
        if quantity in visited:
            return
        visited.add(quantity)
        derivation = facts[quantity].derivation
        if derivation is None:
            return
        for dependency in derivation.inputs:
            visit(dependency)
        for row in derivation.rows:
            if row not in rows:
                rows.append(row)

    visit(requested)
    if not rows:
        raise AltitudeSolveError(f"cannot derive {requested}")
    return tuple(rows)


def _depends_on(
    facts: dict[str, _Fact],
    quantity: str,
    dependency: str,
    visited: set[str] | None = None,
) -> bool:
    """Return whether one derived fact transitively uses another fact."""

    if quantity == dependency:
        return True
    if quantity not in facts or facts[quantity].derivation is None:
        return False
    seen = set() if visited is None else visited
    if quantity in seen:
        return False
    seen.add(quantity)
    return any(
        _depends_on(facts, item, dependency, seen)
        for item in facts[quantity].derivation.inputs
    )


def solve_altitude_condition(condition_html: str) -> AltitudeSolution:
    """Solve one supported altitude condition or fail without partial output."""

    facts, requested = _extract_condition(condition_html)
    for _ in range(20):
        changed = False
        for hypotenuse, leg_a, leg_b in _PYTHAGOREAN:
            changed = _apply_pythagoras(facts, hypotenuse, leg_a, leg_b) or changed
        for function, numerator, denominator in _RATIOS:
            changed = (
                _apply_trig_pythagorean_scale(
                    facts,
                    function,
                    numerator,
                    denominator,
                )
                or changed
            )
        for function, numerator, denominator in _RATIOS:
            changed = _apply_ratio(facts, function, numerator, denominator) or changed
        for hypotenuse, leg_a, leg_b in _PYTHAGOREAN:
            changed = _apply_pythagoras(facts, hypotenuse, leg_a, leg_b) or changed
        changed = _apply_sum(facts) or changed
        for hypotenuse, numerator, denominator in _TANGENT_HYPOTENUSE:
            changed = (
                _apply_tangent_hypotenuse(
                    facts,
                    hypotenuse,
                    numerator,
                    denominator,
                )
                or changed
            )
        if "sinA" in facts and "cosA" in facts:
            changed = _apply_identity(facts) or changed
        elif requested not in facts:
            changed = _apply_identity(facts) or changed
        if not changed:
            break
    else:
        raise AltitudeSolveError("altitude inference did not converge")
    if requested not in facts:
        raise AltitudeSolveError(f"cannot derive {requested}")
    if (
        requested == "BH"
        and "AB" in facts
        and "AH" in facts
        and not _depends_on(facts, "AB", "BH")
        and not _depends_on(facts, "AH", "BH")
    ):
        subtraction = sp.simplify(facts["AB"].value - facts["AH"].value)
        if not _same(facts["BH"].value, subtraction):
            raise AltitudeSolveError("inconsistent BH")
        facts["BH"] = _Fact(
            value=subtraction,
            latex=_latex_number(subtraction),
            derivation=_Derivation(
                ("AB", "AH"),
                (
                    rf"BH=AB-AH={_fact_latex(facts, 'AB')}"
                    rf"-{_fact_latex(facts, 'AH')}={_latex_number(subtraction)}",
                ),
            ),
        )
    return AltitudeSolution(
        requested=requested,
        exact_value=facts[requested].value,
        answer=_answer_text(facts[requested].value),
        rows=_proof_rows(facts, requested),
    )


def answer_value(answer_html: str) -> sp.Expr:
    """Parse one materialized answer for exact comparison with a solution."""

    formulas = re.findall(r'data-inline-latex="([^"]+)"', unescape(answer_html))
    if len(formulas) == 1:
        return _parse_positive_value(formulas[0])
    visible = _visible_text(answer_html).replace(" ", "")
    if not visible:
        raise AltitudeSolveError("materialized answer is missing")
    return _parse_positive_value(visible)


def answer_matches(answer_html: str, expected: sp.Expr) -> bool:
    """Return exact mathematical equality for one materialized answer."""

    return _same(answer_value(answer_html), expected)
