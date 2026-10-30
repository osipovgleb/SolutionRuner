"""Solve affine sine/cosine equations and squared-function relations exactly."""

from fractions import Fraction

import sympy as sp

from ..core.numbers import format_answer
from ..probability.common import UnsupportedCondition, finish, line
from .power_arithmetic import ScalarParser
from .trig_angles import C, S
from .trig_given_domain import candidates, read_question
from .trig_symbolic_parser import SymbolicTrigonometricParser, compile_atoms, formula

T = sp.Symbol("t", real=True)


def _read(context, power):
    q = read_question(context)
    query = SymbolicTrigonometricParser(q.expression)
    node = query.parse()
    if (
        len(query.atoms) != 1
        or not q.relation
        or q.domain
        or q.relation.count("=") != 1
    ):
        raise UnsupportedCondition(
            "one tangent query and one complete relation are required"
        )
    symbol, atom = next(iter(query.atoms.items()))
    if (
        node.value != symbol**power
        or atom.function != "tg"
        or atom.coefficient != 1
        or atom.shift != 0
    ):
        raise UnsupportedCondition(
            "the query must be tangent or its square at the original angle"
        )
    lhs, rhs = q.relation.split("=")
    parser = SymbolicTrigonometricParser(lhs)
    original = parser.parse().value
    base, variable, values, denominators = compile_atoms(parser)
    value = ScalarParser(rhs).parse()
    if base != 1 or variable != atom.variable or value.is_Rational is not True:
        raise UnsupportedCondition(
            "the equation must use the same angle and an exact rational right side"
        )
    expression = original.xreplace(values)
    return q, expression, value, denominators, variable


def _linear(poly):
    a, b = sp.expand(poly).coeff(S), sp.expand(poly).coeff(C)
    if a.free_symbols or b.free_symbols or sp.expand(poly - a * S - b * C) != 0:
        raise UnsupportedCondition(
            "cross multiplication must give a homogeneous linear trigonometric relation"
        )
    return a, b


def build_tangent_equation_plan(context, *, divide_first=False):
    q, expression, value, denominators, theta = _read(context, 1)
    numerator, denominator = sp.fraction(expression)
    cross = sp.expand(numerator - value * denominator)
    a, b = _linear(cross)
    if a == 0:
        raise UnsupportedCondition(
            "the relation does not determine a finite unique tangent"
        )
    answer = sp.cancel(-b / a)
    if answer.is_Rational is not True:
        raise UnsupportedCondition("the tangent equation has no exact rational answer")
    valid = False
    for s, c in candidates("tg", answer, None):
        checks = [sp.simplify(d.subs({S: s, C: c})) for d in denominators]
        if any(d.is_zero is True for d in checks):
            continue
        if any(d.is_zero is not False for d in checks):
            raise UnsupportedCondition("an equation denominator is not proved nonzero")
        if sp.simplify(expression.subs({S: s, C: c}) - value) == 0:
            valid = True
    if not valid:
        raise UnsupportedCondition(
            "the cross-multiplied equation has no valid original solution"
        )
    html = "<p>Учитываем ненулевой знаменатель исходной дроби:</p>"
    html += line(q.relation)
    for d in dict.fromkeys(denominators):
        html += line(formula(d, theta) + r"\ne0")
    if divide_first:
        ns, nc = _linear(numerator)
        ds, dc = _linear(denominator)
        html += "<p>Проверим, что косинус ненулевой, прежде чем делить на него:</p>"
        if ds:
            html += line(
                rf"\cos({theta})=0\ \Longrightarrow\ {q.relation.split('=')[0]}=\frac{{{sp.latex(ns)}}}{{{sp.latex(ds)}}}\ne {sp.latex(value)}"
            )
        else:
            html += line(
                rf"\cos({theta})=0\ \Longrightarrow\ "
                + formula(denominator, theta)
                + "=0"
            )
        html += "<p>Разделим числитель и знаменатель на косинус и введём тангенс:</p>"
        n, d = ns * T + nc, ds * T + dc
        show = lambda p: sp.latex(p, symbol_names={T: r"(\tg(" + theta + "))"})
        html += line(
            q.relation.split("=")[0]
            + rf"=\frac{{{show(n)}}}{{{show(d)}}}={sp.latex(value)}"
        )
        html += line(show(n) + "=(" + sp.latex(value) + ")(" + show(d) + ")")
    else:
        html += "<p>Умножим равенство на исходный знаменатель и раскроем скобки:</p>"
        html += line(
            formula(numerator, theta)
            + "=("
            + sp.latex(value)
            + ")("
            + formula(denominator, theta)
            + ")"
        )
        html += line(formula(cross, theta) + "=0")
        html += "<p>Косинус ненулевой: иначе получились бы одновременно нулевые синус и косинус, что противоречит основному тождеству.</p>"
        html += line(rf"\sin^2({theta})+\cos^2({theta})=1,\quad\cos({theta})\ne0")
    html += "<p>Решим полученное линейное уравнение относительно тангенса:</p>"
    html += line(rf"({sp.latex(a)})\tg({theta})={sp.latex(-b)}")
    html += line(
        q.expression + rf"=\frac{{{sp.latex(-b)}}}{{{sp.latex(a)}}}={sp.latex(answer)}"
    )
    return finish(
        q.condition,
        q.answer,
        q.solution,
        format_answer(Fraction(int(answer.p), int(answer.q))),
        html,
    )


def build_square_relation_plan(context):
    q, expression, r, denominators, theta = _read(context, 2)
    a, b = sp.expand(expression).coeff(S**2), sp.expand(expression).coeff(C**2)
    if (
        denominators
        or a.free_symbols
        or b.free_symbols
        or sp.expand(expression - a * S * S - b * C * C) != 0
        or a == b
    ):
        raise UnsupportedCondition(
            "two distinct squared-function coefficients are required"
        )
    sine_square = sp.cancel((r - b) / (a - b))
    cosine_square = 1 - sine_square
    if (
        sine_square.is_Rational is not True
        or not 0 <= sine_square <= 1
        or cosine_square <= 0
    ):
        raise UnsupportedCondition(
            "the relation is inconsistent or gives an undefined tangent"
        )
    answer = sp.cancel(sine_square / cosine_square)
    html = "<p>Используем основное тригонометрическое тождество:</p>"
    html += line(rf"\sin^2({theta})+\cos^2({theta})=1")
    html += "<p>Первый способ. Перенесём правую часть и сгруппируем квадраты:</p>"
    html += line(
        formula(expression, theta)
        + "=("
        + sp.latex(r)
        + rf")(\sin^2({theta})+\cos^2({theta}))"
    )
    html += line(
        rf"({sp.latex(a - r)})\sin^2({theta})=({sp.latex(r - b)})\cos^2({theta})"
    )
    html += line(
        rf"\tg^2({theta})=\frac{{{sp.latex(r - b)}}}{{{sp.latex(a - r)}}}={sp.latex(answer)}"
    )
    html += "<p>Второй способ. Сначала найдём квадрат косинуса, затем используем связь тангенса с косинусом:</p>"
    html += line(
        rf"({sp.latex(a)})(\sin^2({theta})+\cos^2({theta}))+({sp.latex(b - a)})\cos^2({theta})={sp.latex(r)}"
    )
    html += line(
        rf"\cos^2({theta})=\frac{{{sp.latex(r - a)}}}{{{sp.latex(b - a)}}}={sp.latex(cosine_square)}>0"
    )
    html += line(
        rf"1+\tg^2({theta})=\frac1{{\cos^2({theta})}}={sp.latex(1 / cosine_square)}"
    )
    html += line(
        q.expression + "=" + sp.latex(1 / cosine_square) + "-1=" + sp.latex(answer)
    )
    return finish(
        q.condition,
        q.answer,
        q.solution,
        format_answer(Fraction(int(answer.p), int(answer.q))),
        html,
    )
