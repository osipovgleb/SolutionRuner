"""Preserve source reductions, complementary signs and the two tangent methods."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .trig_angles import C, S, reduce_polynomial
from .trig_symbolic_parser import formula

T = sp.Symbol("t", real=True)


def _given_reduction(calc):
    expression = calc.original.xreplace(calc.values)
    function, value = calc.given.function, calc.given_value
    if function == "cos":
        expression = reduce_polynomial(expression.xreplace({S: C, C: S})).xreplace(
            {S: C, C: S}
        )
        return expression, sp.cancel(expression.subs(C, value))
    if function == "sin":
        expression = reduce_polynomial(expression)
        return expression, sp.cancel(expression.subs(S, value))
    variable = C if function == "tg" else S
    expression = sp.cancel(
        expression.subs(S, value * C)
        if function == "tg"
        else expression.subs(C, value * S)
    )
    n, d = sp.fraction(expression)
    relation = variable**2 - 1 / (1 + value**2)
    return expression, sp.cancel(
        sp.rem(n, relation, variable) / sp.rem(d, relation, variable)
    )


def _cotangent(calc):
    if (
        calc.given.function != "sin"
        or len(calc.pairs) != 1
        or sp.cancel(calc.reduced - S / C) != 0
    ):
        raise UnsupportedCondition(
            "the source cotangent method needs sine and a determined tangent sign"
        )
    value = calc.given_value
    if value == 0:
        raise UnsupportedCondition("the cotangent method requires a nonzero sine")
    theta = calc.theta
    cotangent = sp.simplify(calc.pairs[0][1] / calc.pairs[0][0])
    if cotangent == 0:
        raise UnsupportedCondition("the requested tangent is undefined")
    square = sp.simplify(1 / value**2 - 1)
    sign = "-" if cotangent < 0 else ""
    html = "<p>Определим знак котангенса по заданному промежутку и выразим его через синус:</p>"
    html += line(calc.question.domain)
    html += line(rf"\ctg({theta})" + ("<0" if cotangent < 0 else ">0"))
    html += line(rf"\ctg^2({theta})=\frac1{{\sin^2({theta})}}-1")
    html += line(
        rf"\ctg^2({theta})=\frac1{{({sp.latex(value)})^2}}-1={sp.latex(square)}"
    )
    html += line(
        rf"\ctg({theta})={sign}\sqrt{{{sp.latex(square)}}}={sp.latex(cotangent)}"
    )
    html += "<p>Найдём тангенс как обратную величину:</p>"
    html += line(
        calc.question.expression
        + rf"=\frac1{{\ctg({theta})}}=\frac1{{{sp.latex(cotangent)}}}={sp.latex(calc.answer)}"
    )
    return html


def _two_tangent_methods(calc):
    if calc.given.function != "tg":
        raise UnsupportedCondition("the two ratio methods require a given tangent")
    raw = calc.original.xreplace(calc.values)
    numerator, denominator = sp.fraction(raw)
    if any(sp.Poly(p, S, C).total_degree() > 1 for p in [numerator, denominator]):
        raise UnsupportedCondition(
            "the source ratio methods require affine sine and cosine terms"
        )
    theta = calc.theta
    q = calc.given_value
    first = sp.cancel(raw.subs(S, q * C))
    if first != calc.answer:
        raise UnsupportedCondition(
            "the linear sine substitution does not make the ratio constant"
        )
    html = "<p>Первый способ. Выразим синус через косинус и заданный тангенс:</p>"
    html += line(
        rf"\sin({theta})=\tg({theta})\cos({theta})=({sp.latex(q)})\cos({theta})"
    )
    n = sp.expand(numerator.subs(S, q * C))
    d = sp.expand(denominator.subs(S, q * C))
    html += line(
        calc.question.expression
        + "="
        + rf"\frac{{{formula(n, theta)}}}{{{formula(d, theta)}}}"
    )
    html += line(
        rf"\frac{{{formula(n, theta)}}}{{{formula(d, theta)}}}={sp.latex(calc.answer)}"
    )
    html += (
        "<p>Второй способ. Разделим числитель и знаменатель на ненулевой косинус:</p>"
    )
    html += line(rf"\cos({theta})\ne0")
    n2 = sp.expand(numerator / C).subs(S / C, T)
    d2 = sp.expand(denominator / C).subs(S / C, T)

    def show(value):
        return sp.latex(
            value,
            symbol_names={T: r"(\tg(" + theta + "))", C: r"(\cos(" + theta + "))"},
        )

    html += line(calc.question.expression + rf"=\frac{{{show(n2)}}}{{{show(d2)}}}")
    html += line(
        rf"\frac{{{show(n2.subs(T, q))}}}{{{show(d2.subs(T, q))}}}={sp.latex(calc.answer)}"
    )
    return html


def _direct_tangent(calc):
    if (
        calc.given.function not in ("sin", "cos")
        or len(calc.pairs) != 1
        or sp.cancel(calc.reduced - S / C) != 0
    ):
        raise UnsupportedCondition(
            "the direct tangent method needs a sine or cosine and a determined sign"
        )
    cosine = calc.pairs[0][1]
    if cosine == 0:
        raise UnsupportedCondition("the requested tangent is undefined")
    theta = calc.theta
    square = sp.simplify(1 / cosine**2 - 1)
    sign = "-" if calc.answer < 0 else ""
    html = "<p>По заданному промежутку определим знак тангенса:</p>" + line(
        calc.question.domain
    )
    html += line(
        rf"\tg({theta})"
        + ("<0" if calc.answer < 0 else ">0" if calc.answer > 0 else "=0")
    )
    html += "<p>Выразим квадрат тангенса через квадрат косинуса:</p>"
    html += line(rf"\tg^2({theta})=\frac1{{\cos^2({theta})}}-1")
    if calc.given.function == "sin":
        html += line(
            rf"\cos^2({theta})=1-({sp.latex(calc.given_value)})^2={sp.latex(cosine**2)}"
        )
    else:
        html += line(calc.question.relation)
        html += line(
            rf"\cos^2({theta})=({sp.latex(calc.given_value)})^2={sp.latex(cosine**2)}"
        )
    html += line(
        rf"\tg^2({theta})=\frac1{{{sp.latex(cosine**2)}}}-1={sp.latex(square)}"
    )
    html += "<p>Извлечём корень с учётом найденного знака:</p>"
    html += line(
        calc.question.expression
        + rf"={sign}\sqrt{{{sp.latex(square)}}}={sp.latex(calc.answer)}"
    )
    return html


def render(calc, *, via_cotangent=False, direct_tangent=False, two_methods=False):
    if direct_tangent:
        return _direct_tangent(calc)
    if via_cotangent:
        return _cotangent(calc)
    if two_methods:
        return _two_tangent_methods(calc)
    q = calc.question
    theta = calc.theta
    html = "<p>Применим формулы приведения и тригонометрические тождества:</p>"
    html += line(r"\sin^2t+\cos^2t=1,\quad\tg t=\frac{\sin t}{\cos t}")
    html += line(r"\sin2t=2\sin t\cos t,\quad\cos2t=1-2\sin^2t=2\cos^2t-1")
    if calc.given:
        html += line(q.relation)
    if q.domain:
        html += line(q.domain)
    seen = set()
    for symbol, atom in calc.parser.atoms.items():
        if atom.shift == 0 and (
            (atom.function == "sin" and calc.values[symbol] == S)
            or (atom.function == "cos" and calc.values[symbol] == C)
        ):
            continue
        step = atom.text + "=" + formula(calc.values[symbol], theta)
        if step not in seen:
            html += line(step)
            seen.add(step)
    if calc.denominators:
        html += "<p>Сохраняем условия ненулевых знаменателей исходного выражения:</p>"
        for d in dict.fromkeys(calc.denominators):
            html += line(formula(d, theta) + r"\ne0")
    original = sp.latex(
        calc.original,
        symbol_names={
            symbol: "(" + formula(value, theta) + ")"
            for symbol, value in calc.values.items()
        },
    )
    html += line(q.expression + "=" + original)
    if not calc.given:
        html += (
            "<p>Приведём подобные слагаемые и сократим общие ненулевые множители:</p>"
        )
        return html + line(original + "=" + sp.latex(calc.answer))
    return html + _substitution(calc)


def _substitution(calc):
    q, theta = calc.question, calc.theta
    html = ""
    expression, reduced = _given_reduction(calc)
    if calc.given.function in ("sin", "cos"):
        known = S if calc.given.function == "sin" else C
        unknown = C if known == S else S
        if unknown in reduced.free_symbols:
            if len(calc.pairs) != 1:
                raise UnsupportedCondition(
                    "the proof needs an undetermined complementary sign"
                )
            value = calc.pairs[0][1] if unknown == C else calc.pairs[0][0]
            function = "cos" if unknown == C else "sin"
            sign = "-" if value < 0 else ""
            html += "<p>По промежутку определим знак второй функции и используем основное тождество:</p>"
            html += line(
                rf"\{function}^2({theta})=1-({sp.latex(calc.given_value)})^2={sp.latex(value**2)}"
            )
            html += line(
                rf"\{function}({theta})={sign}\sqrt{{{sp.latex(value**2)}}}={sp.latex(value)}"
            )
            numeric = {S: calc.pairs[0][0], C: calc.pairs[0][1]}
            reduced = sp.simplify(reduced.subs(numeric))
        else:
            numeric = {known: calc.given_value}
    else:
        value = calc.given_value
        html += line(
            rf"\sin({theta})=({sp.latex(value)})\cos({theta})"
            if calc.given.function == "tg"
            else rf"\cos({theta})=({sp.latex(value)})\sin({theta})"
        )
        numeric = {S: value * C} if calc.given.function == "tg" else {C: value * S}
    if sp.simplify(reduced - calc.answer) != 0:
        raise UnsupportedCondition(
            "the symbolic proof does not imply the independently evaluated answer"
        )
    html += "<p>Подставим заданное значение после упрощения:</p>"
    html += line(q.expression + "=" + formula(expression, theta))
    substituted = sp.latex(
        expression,
        symbol_names={
            symbol: "(" + sp.latex(value) + ")"
            if not value.free_symbols
            else formula(value, theta)
            for symbol, value in numeric.items()
        }
        | {
            symbol: formula(symbol, theta) for symbol in [S, C] if symbol not in numeric
        },
    )
    html += line(
        formula(expression, theta) + "=" + substituted + "=" + sp.latex(calc.answer)
    )
    return html
