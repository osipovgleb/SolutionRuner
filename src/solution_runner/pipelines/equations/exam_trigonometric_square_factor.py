"""Keep a zero factor separate from a reviewed complete square."""

import re
from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S


def reviewed(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    if "полный квадрат" in text or "полного квадрата" in text:
        return True
    return any(
        re.search(
            r"(?:[ty]|\\(?:sin|cos)x)\([^()]+\)\^\{?2",
            "".join(n["data-inline-latex"].split()),
        )
        for n in soup.select("[data-inline-latex]")
    )


def square(polynomial, variable):
    if not polynomial.is_polynomial(variable) or sp.degree(polynomial, variable) != 2:
        return None
    a, b, c = sp.Poly(polynomial, variable).all_coeffs()
    if any(v.free_symbols for v in (a, b, c)) or sp.simplify(b * b - 4 * a * c) != 0:
        return None
    sign = compare(a, sp.S.Zero)
    if sign == 0:
        return None
    leading = sp.sqrt(sign * a)
    result = sign * (leading * variable + b / (2 * sign * leading)) ** 2
    if sp.expand(result - polynomial) != 0:
        raise UnsupportedCondition(
            "the complete square must equal its polynomial exactly"
        )
    return result


def prepare(compiled, parent_html):
    raw = compiled.raw
    if (
        compiled.poles
        or not reviewed(parent_html)
        or raw.free_symbols != {S, C}
        or not raw.is_polynomial(S, C)
        or sp.Poly(raw, S, C).total_degree() != 3
    ):
        return compiled
    for zero in (S, C):
        if raw.subs(zero, 0) != 0:
            continue
        quotient = sp.cancel(raw / zero)
        reduced = sp.expand(sp.rem(quotient, S * S + C * C - 1, zero))
        other = C if zero == S else S
        if reduced.free_symbols != {other} or square(reduced, other) is None:
            continue
        projected = sp.expand(zero * reduced)
        return replace(
            compiled,
            raw=projected,
            factored_source=raw if projected != raw else compiled.factored_source,
            square_product=(zero, reduced),
        )
    return compiled


def mark(branches, parent_html, product):
    if not reviewed(parent_html):
        return branches
    text = (
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
    )
    note = "можно было найти дискриминант" in " ".join(text.split())
    result = []
    for b in branches:
        degree = sp.degree(b.polynomial, b.variable)
        candidate = (
            b.polynomial
            if degree == 2 and product is not None
            else sp.cancel(b.polynomial / b.variable)
            if degree == 3 and b.polynomial.subs(b.variable, 0) == 0
            else None
        )
        if candidate is not None and square(candidate, b.variable) is not None:
            b = replace(
                b,
                square_factor=True,
                square_discriminant=note,
                candidates=tuple(sorted(b.candidates, key=lambda v: v != 0)),
                values=tuple(sorted(b.values, key=lambda v: v != 0)),
            )
        result.append(b)
    if product is not None:
        result.sort(key=lambda b: b.variable != product[0])
    return tuple(result)


def polynomial_proof(branch, symbol, angle):
    from .exam_trigonometric_proof import formula

    variable = branch.variable
    p = branch.polynomial
    cubic = sp.degree(p, variable) == 3
    q = sp.cancel(p / variable) if cubic else p
    completed = square(q, variable)
    if completed is None:
        raise UnsupportedCondition(
            "the parent square factor needs a double quadratic root"
        )
    html = (
        "<p>Вынесем общий множитель и выделим полный квадрат:</p>"
        if cubic
        else "<p>Выделим полный квадрат:</p>"
    )
    if cubic:
        html += line(
            formula(sp.Mul(variable, q, evaluate=False).subs(variable, symbol), angle)
            + "=0"
        )
        completed = sp.Mul(variable, completed, evaluate=False)
    html += line(formula(completed.subs(variable, symbol), angle) + "=0")
    if branch.square_discriminant:
        a, b, c = sp.Poly(q, variable).all_coeffs()
        html += "<p>Тот же результат для квадратного множителя даёт нулевой дискриминант:</p>"
        html += line(
            "D=(" + sp.latex(b) + ")^2-4(" + sp.latex(a) + ")(" + sp.latex(c) + ")=0"
        )
    return html
