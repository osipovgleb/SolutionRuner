"""Prepare integer-power reductions and check the original denominator domain."""

import sympy as sp

from ..core.numbers import format_answer, format_latex_fraction
from ..probability.common import UnsupportedCondition, finish, line
from .calculation_input import read_calculation
from .expression_repair import repair_terminal_product, with_condition_repair
from .laurent_arithmetic import exact_value, latex, symbolic
from .laurent_parser import LaurentParser


def build_context_repair_plan(context):
    prepared, change = repair_terminal_product(context)
    _content, condition, answer, solution, expression, parameters = read_calculation(
        prepared
    )
    if parameters.definition:
        raise UnsupportedCondition("a Laurent expression has no function definition")
    parser = LaurentParser(expression)
    poly = parser.parse()
    nonzero = parser.nonzero | parameters.nonzero
    for name in parameters.positive:
        if (
            name in parameters.bindings
            and parameters.bindings[name].is_positive is not True
        ):
            raise UnsupportedCondition(
                "the assigned value violates a positive variable constraint"
            )
    value = exact_value(poly, parameters.bindings, nonzero)
    html = "<p>Используем свойства целых степеней: степень произведения раскрываем по множителям, показатели при умножении складываем, при делении вычитаем:</p>"
    html += line(r"(ab)^n=a^nb^n,\quad(a^m)^n=a^{mn},\quad\frac{a^m}{a^n}=a^{m-n}")
    if nonzero:
        html += (
            "<p>Сохраняем условия ненулевых знаменателей исходного выражения:</p>"
            + line(r",\quad ".join(name + r"\ne0" for name in sorted(nonzero)))
        )
    html += "<p>Раскроем степени мономов и приведём подобные слагаемые:</p>"
    for trace in dict.fromkeys(parser.trace):
        html += line(trace)
    html += line(expression + "=" + latex(poly))
    if parameters.bindings:
        html += "<p>Подставим заданные значения после упрощения:</p>"
        for name, number in parameters.bindings.items():
            html += line(name + "=" + sp.latex(number))
        substituted = symbolic(poly).subs(
            {sp.Symbol(k, real=True): v for k, v in parameters.bindings.items()}
        )
        html += line(
            latex(poly)
            + "="
            + sp.latex(substituted)
            + "="
            + format_latex_fraction(value)
        )
    elif latex(poly) != format_latex_fraction(value):
        html += line(latex(poly) + "=" + format_latex_fraction(value))
    return with_condition_repair(
        finish(condition, answer, solution, format_answer(value), html), change
    )
