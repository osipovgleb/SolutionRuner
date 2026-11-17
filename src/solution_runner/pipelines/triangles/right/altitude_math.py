"""Exact arithmetic and proportionality steps for altitude proofs."""

from __future__ import annotations

import math
import re

import sympy as sp

from .altitude_types import _RATIO_VARIABLES, AltitudeSolveError, _Derivation, _Fact


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

    return (
        variable
        if _same(coefficient, sp.Integer(1))
        else _latex_number(coefficient) + variable
    )


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


def _apply_ratio(
    facts: dict[str, _Fact], function: str, numerator: str, denominator: str
) -> bool:
    """Infer the only missing member of one trigonometric side ratio."""

    known = {
        quantity for quantity in (function, numerator, denominator) if quantity in facts
    }
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
        return _assign(
            facts, function, value, _Derivation((numerator, denominator), (row,))
        )
    if numerator not in facts:
        return _derive_ratio_numerator(facts, function, numerator, denominator)
    if denominator not in facts:
        return _derive_ratio_denominator(facts, function, numerator, denominator)
    expected = facts[numerator].value / facts[denominator].value
    if not _same(facts[function].value, expected):
        raise AltitudeSolveError(f"inconsistent {function}")
    return False


def _derive_ratio_numerator(
    facts: dict[str, _Fact], function: str, numerator: str, denominator: str
) -> bool:
    """Derive the missing numerator from a known trigonometric ratio."""

    function_latex = _function_latex(function)
    definition = rf"{function_latex}=\frac{{{numerator}}}{{{denominator}}}"
    value = facts[denominator].value * facts[function].value
    if facts[denominator].derivation is not None:
        row = (
            definition + rf"\Longrightarrow {numerator}={denominator}{function_latex}="
            rf"{_fact_latex(facts, denominator)}\cdot"
            rf"{_fact_latex(facts, function)}={_latex_number(value)}"
        )
        return _assign(
            facts,
            numerator,
            value,
            _Derivation((denominator, function), (row,)),
        )
    variable, _num_coefficient, den_coefficient, num_term, den_term, setup = (
        _proportion_parts(facts, function, numerator, denominator)
    )
    scale = sp.simplify(facts[denominator].value / den_coefficient)
    source_derivation = facts[denominator].derivation
    rows = (
        (rf"{numerator}={num_term}={_latex_number(value)}",)
        if source_derivation is not None and setup in source_derivation.rows
        else (
            setup,
            (
                rf"{denominator}={_fact_latex(facts, denominator)}={den_term}"
                rf"\Longrightarrow {variable}={_latex_number(scale)}"
            ),
            rf"{numerator}={num_term}={_latex_number(value)}",
        )
    )
    return _assign(facts, numerator, value, _Derivation((denominator, function), rows))


def _derive_ratio_denominator(
    facts: dict[str, _Fact], function: str, numerator: str, denominator: str
) -> bool:
    """Derive the missing denominator from a known trigonometric ratio."""

    function_latex = _function_latex(function)
    definition = rf"{function_latex}=\frac{{{numerator}}}{{{denominator}}}"
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
    variable, num_coefficient, _den_coefficient, num_term, den_term, setup = (
        _proportion_parts(facts, function, numerator, denominator)
    )
    scale = sp.simplify(facts[numerator].value / num_coefficient)
    source_derivation = facts[numerator].derivation
    rows = (
        (rf"{denominator}={den_term}={_latex_number(value)}",)
        if source_derivation is not None and setup in source_derivation.rows
        else (
            setup,
            (
                rf"{numerator}={_fact_latex(facts, numerator)}={num_term}"
                rf"\Longrightarrow {variable}={_latex_number(scale)}"
            ),
            rf"{denominator}={den_term}={_latex_number(value)}",
        )
    )
    return _assign(facts, denominator, value, _Derivation((numerator, function), rows))


def _apply_pythagoras(
    facts: dict[str, _Fact], hypotenuse: str, leg_a: str, leg_b: str
) -> bool:
    """Infer or verify one side through the Pythagorean theorem."""

    quantities = (hypotenuse, leg_a, leg_b)
    known = [quantity for quantity in quantities if quantity in facts]
    if len(known) < 2:
        return False
    if hypotenuse not in facts:
        value = sp.sqrt(facts[leg_a].value ** 2 + facts[leg_b].value ** 2)
        row = (
            rf"{hypotenuse}=\sqrt{{{leg_a}^2+{leg_b}^2}}="
            rf"\sqrt{{({_fact_latex(facts, leg_a)})^2+({_fact_latex(facts, leg_b)})^2}}="
            + _latex_number(value)
        )
        return _assign(facts, hypotenuse, value, _Derivation((leg_a, leg_b), (row,)))
    missing = leg_a if leg_a not in facts else leg_b if leg_b not in facts else None
    if missing is not None:
        other = leg_b if missing == leg_a else leg_a
        square = sp.simplify(facts[hypotenuse].value ** 2 - facts[other].value ** 2)
        if square.is_positive is not True:
            raise AltitudeSolveError(f"inconsistent {hypotenuse}")
        value = sp.sqrt(square)
        row = (
            rf"{missing}=\sqrt{{{hypotenuse}^2-{other}^2}}="
            rf"\sqrt{{({_fact_latex(facts, hypotenuse)})^2-({_fact_latex(facts, other)})^2}}="
            + _latex_number(value)
        )
        return _assign(facts, missing, value, _Derivation((hypotenuse, other), (row,)))
    expected = facts[leg_a].value ** 2 + facts[leg_b].value ** 2
    if not _same(facts[hypotenuse].value ** 2, expected):
        raise AltitudeSolveError(f"inconsistent {leg_b}")
    return False
