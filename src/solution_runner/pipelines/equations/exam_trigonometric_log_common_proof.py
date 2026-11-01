"""Show only the parent's base/power normalization and exact constant log levels."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_log_common import exact_power


def logarithm(base, argument):
    return r"\log_{" + sp.latex(base) + r"}\left(" + argument + r"\right)"


def expression(data, value, *, names=None, factor=False):
    mapping = dict(names or {})
    if data.normalization is not None:
        mapping = {
            symbol: r"\left(" + name + r"\right)" for symbol, name in mapping.items()
        }
        for index, (base, argument, constant) in enumerate(
            data.normalization.constants
        ):
            if constant.is_Rational is True:
                continue
            symbol = sp.Dummy("constant_log_" + str(index), real=True)
            value = value.subs(constant, symbol)
            mapping[symbol] = logarithm(base, sp.latex(argument))
    return sp.latex(sp.factor(value) if factor else value, symbol_names=mapping)


def steps(a, log):
    from .exam_trigonometric_proof import formula

    data = a.log_polynomial
    if data.normalization is None:
        return ""
    html = ""
    if data.normalization.cancelled:
        factor, polynomial, sources = data.normalization.cancelled
        for text, value in a.identities:
            if text not in (r"\sin(x)", r"\cos(x)"):
                html += line(text + "=" + formula(value))
        source_names = {
            symbol: r"\left(" + logarithm(base, formula(argument)) + r"\right)"
            for symbol, base, argument in sources
        }
        original_poly = sp.latex(polynomial, symbol_names=source_names)
        html += "<p>После формул приведения исходный знаменатель совпадает с множителем числителя. Он не равен нулю по ОДЗ, поэтому сократим на него:</p>"
        html += line(
            r"\frac{\left("
            + formula(factor)
            + r"\right)\left("
            + original_poly
            + r"\right)}{"
            + formula(factor)
            + "}=0"
        )
        html += line(original_poly + "=0")
    if data.normalization.relations:
        html += "<p>На исходной области определения приведём логарифмы к одному основанию и вынесем показатель положительного аргумента:</p>"
    for base, argument, multiplier in data.normalization.relations:
        weight = (
            ""
            if multiplier == 1
            else "-"
            if multiplier == -1
            else sp.latex(multiplier) + r"\cdot"
        )
        html += line(logarithm(base, formula(argument)) + "=" + weight + log)
    html += line(
        expression(data, data.polynomial, names={sp.Symbol("l", real=True): log}) + "=0"
    )
    return html


def power_level(data, level):
    return (
        sp.latex(level)
        if level.is_Rational is True
        else logarithm(data.base, sp.latex(exact_power(data.base, level)))
    )
