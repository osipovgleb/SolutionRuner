"""Parse and validate bounded inverse-tangent endpoints without expression eval."""

import re

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .power_arithmetic import ScalarParser, balanced, clean


def endpoint(text):
    if not any(name in text for name in ("arctan", "arctg")):
        return None
    text = (
        clean(text)
        .replace(r"\operatorname{arctg}", r"\arctan")
        .replace(r"\arctg", r"\arctan")
    )
    if r"\arctan" not in text:
        return None
    match = re.fullmatch(r"([+-]?)\\arctan(.+)", text)
    if not match:
        raise UnsupportedCondition(
            "one signed inverse tangent is required as the endpoint"
        )
    argument = match[2]
    for left, right in (("(", ")"), ("{", "}")):
        if argument.startswith(left):
            inner, end = balanced(argument, 0, left, right)
            if end == len(argument):
                argument = inner
    if not re.fullmatch(r"[+-]?(?:\d+(?:/\d+)?|\\frac\{[+-]?\d+\}\{\d+\})", argument):
        raise UnsupportedCondition(
            "one explicit rational arctangent argument is required"
        )
    value = ScalarParser(argument).parse()
    if value.is_Rational is not True or abs(value) > 1000:
        raise UnsupportedCondition(
            "a bounded rational inverse-tangent argument is required"
        )
    return (-1 if match[1] == "-" else 1) * sp.atan(value)


def validate(value):
    if value.is_Rational is True:
        return
    radians = sp.cancel(value * sp.pi)
    if radians.is_Rational is True and abs(radians) <= 1000:
        return
    e_coefficient = sp.cancel(radians / sp.E)
    if e_coefficient.is_Rational is True and 0 < abs(e_coefficient) <= 1000:
        return
    functions = list(value.atoms(sp.atan))
    if len(functions) == 1:
        angle = functions[0]
        coefficient = sp.simplify(value.coeff(angle) * sp.pi)
        shift = sp.simplify(value - coefficient * angle / sp.pi)
        argument = angle.args[0]
        if (
            coefficient in (-1, 1)
            and shift.is_Rational is True
            and abs(shift) <= 1000
            and argument.is_Rational is True
            and abs(argument) <= 1000
        ):
            return
    functions = list(value.atoms(sp.acos))
    if len(functions) == 1:
        from .exam_scalar import compare

        angle = functions[0]
        coefficient = sp.simplify(value.coeff(angle) * sp.pi)
        shift = sp.simplify(value - coefficient * angle / sp.pi)
        argument = angle.args[0]
        square = sp.simplify(argument**2)
        if (
            coefficient in (-1, 1)
            and shift.is_Rational is True
            and abs(shift) <= 1000
            and square.is_Rational is True
            and 0 < square < 1
            and compare(argument, -sp.S.One) > 0
            and compare(argument, sp.S.One) < 0
        ):
            return
    raise UnsupportedCondition(
        "a reviewed rational-pi, inverse-tangent or bounded quadratic-cosine angle is required"
    )
