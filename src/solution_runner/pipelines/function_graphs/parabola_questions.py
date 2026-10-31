"""Full quadratic graph questions, declared coefficients and the requested point."""

import re
from dataclasses import dataclass

import sympy as sp

from ..calculus.common import X, polynomial
from ..core.errors import ContentPlanError
from .graph_questions import read
from .hyperbola import number

A, B, C = sp.symbols("a b c", real=True)
PARAMETERS = (A, B, C)


@dataclass(frozen=True)
class Question:
    kind: str
    fixed: dict
    whole: bool = False
    target: sp.Rational | None = None
    given: sp.Expr | None = None


def coefficients(raw, name):
    if not raw.startswith(name + "(x)="):
        raise ContentPlanError("an explicit quadratic function formula is required")
    expression = polynomial(raw[len(name) + 4 :], X, ("a", "b", "c"))
    p = sp.Poly(expression, X)
    if p.degree() != 2:
        raise ContentPlanError("the pictured function must be quadratic")
    values = [p.nth(i) for i in (2, 1, 0)]
    if any(
        v != symbol and v.is_Rational is not True
        for v, symbol in zip(values, PARAMETERS, strict=True)
    ):
        raise ContentPlanError(
            "each coefficient must be its declared parameter or an exact number"
        )
    return expression, {
        symbol: value
        for symbol, value in zip(PARAMETERS, values, strict=True)
        if value.is_Rational is True
    }


def parse(context):
    forms, text = read(context)
    if len(forms) != 2:
        raise ContentPlanError(
            "the complete quadratic graph question must be recognized"
        )
    prefix = r"На рисунке изображен график функции(?: вида)? @0@"
    whole = "где числа" in text
    middle = r"\s*,\s*где числа a\s*,\s*b и c — целые" if whole else ""
    if re.fullmatch(prefix + middle + r"\s*\.\s*Найдите @1@\s*\.", text):
        _, fixed = coefficients(forms[0], "f")
        target = re.fullmatch(r"f\((.+)\)", forms[1])
        if target and len(fixed) in (0, 1):
            return Question("value", fixed, whole, sp.Rational(number(target[1])))
    match = re.fullmatch(
        r"На рисунке изображены графики функций @0@ и @1@\s*,\s*которые пересекаются в точках A и B\s*\.\s*Найдите (абсциссу|ординату) точки B\s*\.",
        text,
    )
    if match:
        given, fixed = coefficients(forms[0], "f")
        other, unknown = coefficients(forms[1], "g")
        if len(fixed) == 3 and not unknown and other == A * X**2 + B * X + C:
            return Question(
                "intersection_x" if match[1] == "абсциссу" else "intersection_y",
                {},
                given=given,
            )
    raise ContentPlanError("the complete quadratic graph question must be recognized")
