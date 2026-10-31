"""Whole mixed-graph questions and explicit assignments of function roles."""

import re
from dataclasses import dataclass

import sympy as sp

from ..calculus.common import X, polynomial
from ..core.errors import ContentPlanError
from .graph_questions import read


@dataclass(frozen=True)
class Question:
    curve_kind: str
    curve_name: str
    line_name: str
    line_symbols: tuple
    line_origin: bool
    known_line: sp.Expr | None
    coordinate: str
    letter: str
    count: int


def parse(context):
    forms, text = read(context)
    # This source writes g(x)=kx as ordinary HTML text.
    if len(forms) == 1:
        text = re.sub(r"g\s*\(\s*x\s*\)\s*=\s*kx", "@1@", text)
        forms.append("g(x)=kx")
    match = re.fullmatch(
        r"На рисунке изображены графики функций(?: видов)? @0@ и @1@\s*,\s*(?:которые пересекаются|пересекающиеся) в (точках A и B|точке A)\s*\.\s*Найдите (абсциссу|ординату) точки (A|B)\s*\.",
        text,
    )
    if not match or len(forms) != 2:
        raise ContentPlanError(
            "the entire mixed-graph intersection question must match"
        )
    count = 2 if match[1] == "точках A и B" else 1
    letter = match[3]
    if letter != ("B" if count == 2 else "A"):
        raise ContentPlanError("the question must identify the other B or the unique A")
    coordinate = "x" if match[2] == "абсциссу" else "y"
    quad = r"ax^{2}+bx+c"
    if forms[1] == "g(x)=" + quad and forms[0].startswith("f(x)="):
        given = polynomial(forms[0][5:], X)
        if sp.Poly(given, X).degree() != 1 or any(
            c.is_Rational is not True for c in sp.Poly(given, X).all_coeffs()
        ):
            raise ContentPlanError(
                "the specified function must be an exact affine line"
            )
        return Question(
            "parabola", "g", "f", (), False, given, coordinate, letter, count
        )
    if forms[0] == "f(x)=" + quad and forms[1] in {"g(x)=kx+d", "g(x)=kx"}:
        origin = forms[1] == "g(x)=kx"
        return Question(
            "parabola", "f", "g", ("k", "d"), origin, None, coordinate, letter, count
        )
    if forms == [r"f(x)=\frac{k}{x}", "g(x)=ax+b"]:
        return Question(
            "reciprocal", "f", "g", ("a", "b"), False, None, coordinate, letter, count
        )
    if forms[0] == r"f(x)=a\sqrt{x}" and forms[1] in {"g(x)=kx+b", "g(x)=kx"}:
        return Question(
            "root",
            "f",
            "g",
            ("k", "b"),
            forms[1] == "g(x)=kx",
            None,
            coordinate,
            letter,
            count,
        )
    raise ContentPlanError(
        "only the inspected mixed curve and line formulas are supported"
    )
