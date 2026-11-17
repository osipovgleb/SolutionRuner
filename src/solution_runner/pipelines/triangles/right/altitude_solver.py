"""Infer exact right-triangle altitude quantities and render their proof rows."""

from __future__ import annotations

import re
from html import unescape

import sympy as sp

from .altitude_inference import (
    _apply_identity,
    _apply_sum,
    _apply_tangent_hypotenuse,
    _apply_trig_pythagorean_scale,
    _depends_on,
    _proof_rows,
)
from .altitude_math import (
    _answer_text,
    _apply_pythagoras,
    _apply_ratio,
    _fact_latex,
    _latex_number,
    _same,
)
from .altitude_parsing import _extract_condition, _parse_positive_value, _visible_text
from .altitude_parsing import _split_braced as _exported_split_braced
from .altitude_types import (
    _PYTHAGOREAN,
    _RATIOS,
    _TANGENT_HYPOTENUSE,
    AltitudeSolution,
    AltitudeSolveError,
    _Derivation,
    _Fact,
)

_split_braced = _exported_split_braced


def solve_altitude_condition(condition_html: str) -> AltitudeSolution:
    """Solve one supported altitude condition or fail without partial output."""

    facts, requested = _extract_condition(condition_html)
    givens = tuple((key, fact.value, fact.latex) for key, fact in facts.items())
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
        if "sinA" in facts and "cosA" in facts or requested not in facts:
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
                    (
                        rf"BH=AB-AH={_fact_latex(facts, 'AB')}"
                        rf"-{_fact_latex(facts, 'AH')}={_latex_number(subtraction)}"
                    ),
                ),
            ),
        )
    return AltitudeSolution(
        requested=requested,
        exact_value=facts[requested].value,
        answer=_answer_text(facts[requested].value),
        rows=_proof_rows(facts, requested),
        givens=givens,
        values=tuple((key, fact.value) for key, fact in facts.items()),
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
