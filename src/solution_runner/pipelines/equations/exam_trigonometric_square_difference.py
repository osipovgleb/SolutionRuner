"""Read a nondegenerate square difference and retain the parent's product method."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from .exam_trigonometric_compile import C, S


@dataclass(frozen=True)
class SquareDifference:
    first: str
    second: str
    difference: sp.Expr
    total: sp.Expr
    coefficient: sp.Expr
    parameter: str = "k"


def compile_difference(values, atoms, denominators):
    from .exam_trigonometric_methods import Equation, shifted_atom
    from .trig_angles import C as NUMERIC_C
    from .trig_angles import S as NUMERIC_S

    if denominators or len(atoms) != 2:
        return None
    symbols = tuple(atoms)
    if values != [symbols[0] ** 2, symbols[1] ** 2]:
        return None
    first, second = (atoms[s] for s in symbols)
    if (
        first.function != second.function
        or first.function not in ("sin", "cos")
        or first.coefficient != -second.coefficient
        or abs(first.coefficient) != 1
        or first.shift != second.shift
    ):
        return None
    a, b = (
        shifted_atom(atom).xreplace({NUMERIC_S: S, NUMERIC_C: C})
        for atom in (first, second)
    )
    raw = sp.expand(a * a - b * b)
    coefficient = sp.cancel(raw / (S * C))
    if not coefficient or coefficient.free_symbols:
        return None
    data = SquareDifference(
        first.text.replace(r"\alpha", "x"),
        second.text.replace(r"\alpha", "x"),
        sp.expand(a - b),
        sp.expand(a + b),
        coefficient,
    )
    return Equation(raw, (), sp.S.One, square_difference=data)


def parameter(parent_html):
    expressions = [
        n["data-inline-latex"]
        for n in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    ]
    families = [
        text for text in expressions if re.search(r"x&?=", "".join(text.split()))
    ]
    used = {
        symbol
        for text in families
        for symbol in re.findall(r"(?<![A-Za-z\\])([kn])(?![A-Za-z])", text)
    }
    return "n" if used == {"n"} else "k"


def reviewed(parent_html):
    for node in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        text = (
            "".join(node["data-inline-latex"].split())
            .replace(r"\left", "")
            .replace(r"\right", "")
        )
        if any(
            text.count("\\" + name + "(") >= 4
            and "-\\" + name + "(" in text
            and "+\\" + name + "(" in text
            for name in ("sin", "cos")
        ):
            return True
    return False


def proof(a):
    from .exam_trigonometric_proof import families, formula

    d = a.square_difference
    first, second = d.first, d.second
    html = line(a.original)
    html += "<p>Используем разность квадратов:</p>"
    html += line(
        r"\left("
        + first
        + "-"
        + second
        + r"\right)\left("
        + first
        + "+"
        + second
        + r"\right)=0"
    )
    html += "<p>Применим формулы суммы и разности тригонометрических функций к каждой скобке:</p>"
    html += line(first + "-" + second + "=" + formula(d.difference))
    html += line(first + "+" + second + "=" + formula(d.total))
    html += line(formula(a.raw) + "=0")
    html += line(sp.latex(d.coefficient) + r"\ne0")
    html += "<p>Разделим на ненулевой числовой множитель и применим формулу двойного угла:</p>"
    html += line(formula(S * C) + "=0") + line(r"\sin2x=0")
    for family in families(a):
        html += line(family + r",\quad " + d.parameter + r"\in\mathbb Z")
    return "<p>Разложим разность квадратов на множители:</p>", html
