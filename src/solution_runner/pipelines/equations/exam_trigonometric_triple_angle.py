"""Preserve the triple-angle solution and the parent's factorization note."""

from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, compile_equation


@dataclass(frozen=True)
class TripleAngle:
    polynomial: sp.Expr
    leading: sp.Expr
    remainder: sp.Expr
    note: bool
    branches: tuple


def style(html):
    text = BeautifulSoup(html, "html.parser").get_text(" ").replace("\xad", "").lower()
    return (
        "косинуса тройного угла" in text,
        "примечание" in text and "разложить" in text,
    )


def compile_triple(formula, note):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_methods import Equation

    raw, identities = compile_equation(formula)
    polynomial = sp.expand(sp.rem(raw, S * S + C * C - 1, S))
    if (
        polynomial.free_symbols != {C}
        or sp.degree(polynomial, C) != 3
        or polynomial.coeff(C, 2) != 0
        or polynomial.subs(C, 0) != 0
    ):
        raise UnsupportedCondition(
            "the triple cosine method requires an odd cosine cubic"
        )
    leading = polynomial.coeff(C, 3) / 4
    remainder = sp.simplify(polynomial.coeff(C) + 3 * leading)
    branches = solve_branches(polynomial, C, factored=True)[1]
    branches = tuple(
        replace(
            b,
            square_level=(
                sp.degree(b.polynomial, C) == 2 and b.polynomial.coeff(C) == 0
            ),
        )
        for b in branches
    )
    branches = tuple(sorted(branches, key=lambda b: sp.degree(b.polynomial, C)))
    data = TripleAngle(polynomial, leading, remainder, note, branches)
    return Equation(
        C if remainder == 0 else polynomial,
        identities,
        sp.Integer(3) if remainder == 0 else sp.S.One,
        triple_angle=data,
    )


def factorization(data):
    from .exam_trigonometric_proof import polynomial

    html = "<p>Вынесем общий множитель и решим полученные уравнения:</p>"
    html += line(
        sp.latex(C, symbol_names={C: r"\cos x"})
        + r"\left("
        + sp.latex(sp.cancel(data.polynomial / C), symbol_names={C: r"(\cos x)"})
        + r"\right)=0"
    )
    for branch in data.branches:
        html += polynomial(branch, factorization=True)
    return html


def proof(a):
    from .exam_trigonometric_proof import candidate_lines, formula

    data = a.triple_angle
    html = line(a.original)
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value))
    html += line(formula(data.polynomial) + "=0")
    html += "<p>Применим формулу косинуса тройного угла:</p>"
    html += line(r"4\cos^3x-3\cos x=\cos3x")
    x = sp.Symbol("x", real=True)
    html += line(
        sp.latex(data.leading * sp.cos(3 * x) + data.remainder * sp.cos(x)) + "=0"
    )
    if data.remainder == 0:
        html += candidate_lines(a.branches[0], angle="3 x", root_scale=sp.Integer(3))
    else:
        html += "<p>Решим равносильное уравнение разложением исходного многочлена на множители:</p>"
        html += factorization(data)
    return "<p>Применим формулу приведения:</p>", html


def note(a):
    from .exam_trigonometric import select
    from .exam_trigonometric_selection import root_series

    data = a.triple_angle
    residues = tuple(sorted({q for b in data.branches for q in b.residues}))
    series = root_series(data.branches, residues, None, False)
    if (
        select(series, (0, 2, True, False))[0]
        != select(a.series, (0, 2, True, False))[0]
    ):
        raise UnsupportedCondition(
            "the triple-angle and factorization methods must agree on the full period"
        )
    if data.remainder != 0:
        from ..word_problems.water_season_proof import inline
        from .exam_trigonometric_proof import formula

        return (
            "<p><b>Примечание.</b> После формулы тройного угла остаётся слагаемое "
            + inline(formula(data.remainder * C))
            + ". Для завершения решения в пункте а) использовано разложение на множители.</p>"
        )
    return (
        "<p><b>Примечание.</b> Можно также решить уравнение разложением на множители.</p>"
        + factorization(data)
    )
