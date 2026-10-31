"""Complete two positive squares and retain their exact simultaneous zeros."""

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_sum_identities import X, literal


def reviewed(html):
    text = BeautifulSoup(html, "html.parser").get_text(" ").replace("\xad", "").lower()
    return "полные квадраты" in text and "каждое из них равно нулю" in text


def compile_squares(formula):
    from .exam_trigonometric_methods import Equation

    polynomial, atoms, functions = literal(formula)
    representatives = {}
    aliases = {}
    for symbol, function in functions.items():
        representative = representatives.setdefault(function, symbol)
        aliases[symbol] = representative
    polynomial = sp.expand(polynomial.xreplace(aliases))
    atoms = {symbol: atoms[symbol] for symbol in representatives.values()}
    functions = {symbol: function for function, symbol in representatives.items()}
    if len(atoms) != 2 or any(
        a.shift or a.coefficient.is_Integer is not True or not 1 <= a.coefficient <= 12
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "two bounded unshifted functions are required for the sum of squares"
        )
    symbols = tuple(atoms)
    constraints, squares = [], []
    for symbol in symbols:
        weight = polynomial.coeff(symbol, 2)
        linear = polynomial.coeff(symbol, 1)
        if weight.free_symbols or weight.is_positive is not True or linear.free_symbols:
            raise UnsupportedCondition(
                "two separate positive square coefficients are required"
            )
        value = sp.simplify(-linear / (2 * weight))
        constraints.append((functions[symbol], value))
        squares.append(weight * (symbol - value) ** 2)
    if sp.expand(polynomial - sum(squares)) != 0:
        raise UnsupportedCondition(
            "the complete squares must reproduce the entire original equation"
        )
    bases = [(f, v) for f, v in constraints if f.args[0] == X]
    if len(bases) != 1:
        raise UnsupportedCondition(
            "one unit-angle function is required for the complete intersection"
        )
    base, value = bases[0]
    variable = S if base.func == sp.sin else C
    substitutions = {sp.sin(X): S, sp.cos(X): C}
    residual = sum(
        sp.expand_trig(f - v).xreplace(substitutions) ** 2
        for f, v in constraints
        if f != base
    )
    if not residual.is_polynomial(S, C):
        raise UnsupportedCondition(
            "the remaining square constraint must have an exact unit-circle polynomial"
        )
    return Equation(
        variable - value,
        (),
        sp.S.One,
        domain=-sp.expand(residual),
        sum_squares=(
            polynomial.xreplace(functions),
            sum(squares).xreplace(functions),
            tuple(constraints),
        ),
    )


def proof(a):
    from .exam_trigonometric_inverse import angles
    from .exam_trigonometric_proof import families, pi

    raw, squares, constraints = a.sum_squares
    html = line(a.original)
    html += "<p>Выделим полные квадраты в левой части уравнения:</p>"
    html += line(sp.latex(raw) + "=" + sp.latex(squares) + "=0")
    html += "<p>Каждый квадрат неотрицателен. Их сумма равна нулю тогда и только тогда, когда оба выражения одновременно равны нулю:</p>"
    for f, value in constraints:
        html += line(sp.latex(f) + "=" + sp.latex(value))
    base, value = next((f, v) for f, v in constraints if f.args[0] == X)
    other, target = next((f, v) for f, v in constraints if f != base)
    if base.func == sp.cos and other == sp.sin(2 * X) and value != 0:
        html += line(r"2\sin x\cos x=" + sp.latex(target))
        html += line(r"\cos x=" + sp.latex(value) + r"\ne0")
        html += line(
            r"\sin x=\frac{"
            + sp.latex(target)
            + r"}{2\cdot\left("
            + sp.latex(value)
            + r"\right)}="
            + sp.latex(sp.simplify(target / (2 * value)))
        )
    else:
        html += "<p>Проверим каждую серию уравнения с единичным углом во втором уравнении системы:</p>"
        for q in angles(S if base.func == sp.sin else C, value):
            actual = sp.simplify(other.subs(X, q * sp.pi))
            html += line(
                "x="
                + pi(q)
                + r"+2\pi k:\quad "
                + sp.latex(other)
                + "="
                + sp.latex(actual)
            )
            html += (
                "<p>Серия удовлетворяет обоим уравнениям.</p>"
                if sp.simplify(actual - target) == 0
                else "<p>Серия не удовлетворяет второму уравнению и исключается.</p>"
            )
    html += "<p>Поэтому вся система даёт серии:</p>"
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Решим уравнение как сумму неотрицательных квадратов:</p>", html
