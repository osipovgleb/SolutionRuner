"""Infer altitude facts and order their derivations."""

from __future__ import annotations

import sympy as sp

from .altitude_math import (
    _assign,
    _coefficient_term,
    _fact_latex,
    _latex_number,
    _proportion_parts,
    _same,
    _squared_display,
)
from .altitude_types import _PYTHAGOREAN, AltitudeSolveError, _Derivation, _Fact


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

    (
        variable,
        numerator_coefficient,
        denominator_coefficient,
        numerator_term,
        denominator_term,
        setup,
    ) = _proportion_parts(facts, function, numerator, denominator)
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
    if (
        third_coefficient.is_real is not True
        or third_coefficient.is_positive is not True
    ):
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
        value = sp.sqrt(1 - facts["sinA"].value ** 2)
        row = (
            r"\cos A=\sqrt{1-(\sin A)^2}="
            rf"\sqrt{{1-({_fact_latex(facts, 'sinA')})^2}}={_latex_number(value)}"
        )
        return _assign(facts, "cosA", value, _Derivation(("sinA",), (row,)))
    if "cosA" in facts and "sinA" not in facts:
        value = sp.sqrt(1 - facts["cosA"].value ** 2)
        row = (
            r"\sin A=\sqrt{1-(\cos A)^2}="
            rf"\sqrt{{1-({_fact_latex(facts, 'cosA')})^2}}={_latex_number(value)}"
        )
        return _assign(facts, "sinA", value, _Derivation(("cosA",), (row,)))
    if (
        "sinA" in facts
        and "cosA" in facts
        and not _same(
            facts["sinA"].value ** 2 + facts["cosA"].value ** 2, sp.Integer(1)
        )
    ):
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
    denominator_value = sp.simplify(facts[hypotenuse].value / sp.sqrt(1 + tangent**2))
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
