"""Source methods for exponential function ratios and equal-index roots."""

import re
from fractions import Fraction

from ..core.numbers import format_answer, format_latex_fraction
from ..probability.common import UnsupportedCondition, finish, line
from .calculation_input import read_calculation
from .power_arithmetic import clean, exact_value
from .power_expression import _main_method
from .power_parser import PowerParser


def build_function_ratio_plan(context):
    _content, condition, answer, solution, expression, parameters = read_calculation(
        context
    )
    definition = re.fullmatch(
        r"g\(x\)=(?P<base>\d+(?:\.\d+)?)\^(?:\{x\}|x)", parameters.definition or ""
    )
    query = re.fullmatch(
        r"\\frac\{g\(x(?P<a>[+-]\d+)\)\}\{g\(x(?P<b>[+-]\d+)\)\}", clean(expression)
    )
    if (
        not definition
        or not query
        or parameters.bindings
        or parameters.positive
        or parameters.nonzero
    ):
        raise UnsupportedCondition("unsupported complete exponential function ratio")
    base = definition["base"]
    expanded = rf"\frac{{{base}^{{x{query['a']}}}}}{{{base}^{{x{query['b']}}}}}"
    terms = PowerParser(expanded, ("x",)).parse()
    value, steps = _main_method(expanded, terms, {})
    html = (
        "<p>Подставим аргументы в определение функции:</p>"
        + line(expression + "=" + expanded)
        + steps
    )
    return finish(condition, answer, solution, format_answer(value), html)


def _root_pattern(name):
    return (
        r"\\sqrt(?:\[(?P<n"
        + name
        + r">\d{1,3})\])?\{(?P<"
        + name
        + r">\d+(?:\.\d+)?)\}"
    )


_ROOT_RATIO = re.compile(
    r"\\frac\{"
    + _root_pattern("a")
    + r"\\cdot"
    + _root_pattern("b")
    + r"\}\{"
    + _root_pattern("c")
    + r"\}"
)


def build_root_ratio_plan(context):
    _content, condition, answer, solution, expression, parameters = read_calculation(
        context
    )
    match = _ROOT_RATIO.fullmatch(clean(expression))
    if (
        not match
        or parameters.bindings
        or parameters.positive
        or parameters.nonzero
        or parameters.definition
    ):
        raise UnsupportedCondition(
            "the common-root method requires three numeric roots"
        )
    degrees = [int(match["n" + k] or "2") for k in ("a", "b", "c")]
    if len(set(degrees)) != 1:
        raise UnsupportedCondition("the combined roots need the same index")
    degree = degrees[0]
    a, b, c = (Fraction(match[k]) for k in ("a", "b", "c"))
    value, _ = exact_value(PowerParser(expression).parse(), {})
    radicand = a * b / c
    if value**degree != radicand:
        raise UnsupportedCondition("the exact common-root computation disagrees")

    def root(text):
        return (r"\sqrt" if degree == 2 else rf"\sqrt[{degree}]") + "{" + text + "}"

    x, y, z = (match[k].replace(".", "{,}") for k in ("a", "b", "c"))
    inside = rf"\frac{{({x})\cdot({y})}}{{{z}}}"
    html = "<p>Объединим корни одинаковой степени. Подкоренные числа положительны, знаменатель ненулевой:</p>"
    html += line(expression + "=" + root(inside))
    html += "<p>Вычислим подкоренное выражение точно:</p>" + line(
        inside + "=" + format_latex_fraction(radicand)
    )
    html += line(
        root(format_latex_fraction(radicand)) + "=" + format_latex_fraction(value)
    )
    return finish(condition, answer, solution, format_answer(value), html)
