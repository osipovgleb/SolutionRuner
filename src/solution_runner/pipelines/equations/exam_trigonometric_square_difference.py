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
    general: bool = False
    rhs: sp.Expr = sp.S.Zero


def compile_difference(values, atoms, denominators):
    direct = compile_direct(values, atoms, denominators)
    if direct is not None:
        return direct
    from .exam_trigonometric_square_fraction import compile_pair

    return compile_pair(values, atoms, denominators)


def compile_direct(values, atoms, denominators):
    from .exam_trigonometric_methods import Equation, shifted_atom
    from .trig_angles import C as NUMERIC_C
    from .trig_angles import S as NUMERIC_S

    if any(d.free_symbols or d == 0 for d in denominators) or not 2 <= len(atoms) <= 4:
        return None
    left = next((s for s in atoms if values[0] == s**2), None)
    right = [s for s in atoms if values[1].coeff(s, 2) == 1]
    if left is None or len(right) != 1:
        return None
    symbols = (left, right[0])
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
    if any(
        atom.function not in ("sin", "cos") or abs(atom.coefficient) != 1
        for atom in atoms.values()
    ):
        return None
    compiled = {
        s: shifted_atom(atom).xreplace({NUMERIC_S: S, NUMERIC_C: C})
        for s, atom in atoms.items()
    }
    rhs = sp.expand((values[1] - symbols[1] ** 2).xreplace(compiled))
    if rhs != 0 and (
        rhs.free_symbols not in ({S}, {C})
        or not rhs.is_polynomial(S, C)
        or sp.Poly(rhs, S, C).total_degree() != 1
        or rhs.subs({S: 0, C: 0}) != 0
        or any(
            c.is_real is not True or abs(c) > 1000 for c in sp.Poly(rhs, S, C).coeffs()
        )
    ):
        return None
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
        rhs=rhs,
    )
    return Equation(
        raw - rhs,
        (),
        sp.S.One,
        square_difference=data,
        factored_source=raw - rhs if rhs != 0 else None,
    )


def parameter(parent_html):
    from .exam_trigonometric_parameters import affine_families

    letters = {name for _, _, name in affine_families(parent_html)}
    if letters == {"l"}:
        return "l"
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
        for symbol in re.findall(r"(?<![A-Za-z\\])([knl])(?![A-Za-z])", text)
    }
    return next(iter(used)) if len(used) == 1 else "k"


def reviewed(parent_html):
    text = (
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
    )
    if "квадраты двух чисел равны" in text:
        return True
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
    if a.square_difference.rhs != 0:
        return linear_rhs_proof(a)
    if a.square_difference.general:
        from .exam_trigonometric_square_fraction import proof as pair_proof

        return pair_proof(a)
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


def linear_rhs_proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    data = a.square_difference
    html = line(a.original)
    html += line(
        r"\left("
        + data.first
        + r"\right)^2-\left("
        + data.second
        + r"\right)^2="
        + formula(data.rhs)
    )
    html += line(
        r"\left("
        + data.first
        + "-"
        + data.second
        + r"\right)\left("
        + data.first
        + "+"
        + data.second
        + r"\right)="
        + formula(data.rhs)
    )
    html += "<p>Применим формулы разности и суммы тригонометрических функций:</p>"
    html += line(data.first + "-" + data.second + "=" + formula(data.difference))
    html += line(data.first + "+" + data.second + "=" + formula(data.total))
    html += line(
        formula(sp.expand(data.difference * data.total)) + "=" + formula(data.rhs)
    )
    html += line(formula(a.raw) + "=0")
    html += line(formula(sp.factor(a.raw, extension=True)) + "=0")
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю:</p>"
    for branch in a.branches:
        html += polynomial(branch, factorization=True)
    return "<p>Используем разность квадратов:</p>", html
