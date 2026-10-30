"""Positive-variable roots reuse exact Laurent addition and monomial division."""

import re
from fractions import Fraction

import sympy as sp

from ..core.numbers import format_answer
from ..probability.common import UnsupportedCondition, finish, line
from .calculation_input import read_calculation
from .laurent_arithmetic import exact_value, latex, names
from .laurent_parser import LaurentParser
from .power_arithmetic import balanced


class RadicalLaurentParser(LaurentParser):
    def __init__(self, text, positive, trace=None, nonzero=None, depth=0):
        super().__init__(text, trace, nonzero, depth)
        self.positive = positive

    def _nested(self, text):
        return RadicalLaurentParser(
            text, self.positive, self.trace, self.nonzero, self.depth + 1
        ).parse()

    def _primary(self):
        if not self.text.startswith(r"\sqrt", self.index):
            return super()._primary()
        start = self.index
        self.index += 5
        degree = 2
        if self.text[self.index : self.index + 1] == "[":
            raw, self.index = balanced(self.text, self.index, "[", "]")
            if not re.fullmatch(r"\d{1,3}", raw) or not 2 <= int(raw) <= 100:
                raise UnsupportedCondition(
                    "a bounded positive radical index is required"
                )
            degree = int(raw)
        raw, self.index = balanced(self.text, self.index)
        poly = self._nested(raw)
        if len(poly) != 1 or names(poly) - self.positive:
            raise UnsupportedCondition("variable roots require a positive monomial")
        key, coefficient = next(iter(poly.items()))
        if coefficient != 1:
            raise UnsupportedCondition(
                "this variable radical method requires unit coefficient"
            )
        result = {
            tuple((name, Fraction(power, degree)) for name, power in key): Fraction(1)
        }
        if any(p.denominator > 10000 for k in result for _, p in k):
            raise UnsupportedCondition("nested radical index exceeds its exact bound")
        original, reduced = self.text[start : self.index], latex(result)
        if original != reduced:
            self.trace.append(original + "=" + reduced)
        return result


def _calculate(expression, positive, bindings):
    parser = RadicalLaurentParser(expression, positive)
    polynomial = parser.parse()
    value = exact_value(polynomial, bindings, parser.nonzero)
    return parser, polynomial, value


def build_context_repair_plan(context, *, two_methods=False):
    _, condition, answer, solution, expression, parameters = read_calculation(context)
    if parameters.definition or parameters.nonzero - parameters.positive:
        raise UnsupportedCondition(
            "variable radical calculations require positive variables"
        )
    if any(value.is_positive is not True for value in parameters.bindings.values()):
        raise UnsupportedCondition("the assigned radical variable must be positive")
    positive = parameters.positive | set(parameters.bindings)
    if not positive:
        raise UnsupportedCondition("a positive radical variable is required")
    parser, polynomial, value = _calculate(expression, positive, parameters.bindings)
    html = "<p>Используем свойства корней при положительных переменных:</p>"
    html += line(r",\quad ".join(name + ">0" for name in sorted(positive)))
    html += line(r"\sqrt[n]{\sqrt[m]{a}}=\sqrt[nm]{a},\quad (\sqrt{x})^2=x")
    if two_methods:
        html += "<p>Первый способ. Приведём дроби к общим множителям и сократим:</p>"
    else:
        html += "<p>Приведём одинаковые радикалы и подобные слагаемые:</p>"
    for step in dict.fromkeys(parser.trace):
        html += line(step)
    html += line(expression + "=" + latex(polynomial))
    if parameters.bindings:
        html += "<p>После упрощения подставим заданное значение:</p>"
        for name, number in parameters.bindings.items():
            html += line(name + "=" + sp.latex(number))
        html += line(
            latex(polynomial)
            + "="
            + sp.latex(sp.Rational(value.numerator, value.denominator))
        )
    if two_methods:
        if positive != {"x"} or parameters.bindings:
            raise UnsupportedCondition(
                "the source substitution method requires one positive x"
            )
        changed = parser.text.replace(r"\sqrt{x}", "t")
        changed = re.sub(r"(?<![a-z])x(?![a-z])", "(t^2)", changed)
        check = LaurentParser(changed)
        alternate = exact_value(check.parse(), {}, check.nonzero)
        if alternate != value:
            raise UnsupportedCondition("the two radical methods disagree")
        html += "<p>Второй способ. Сделаем замену, сохраняя положительность:</p>"
        html += line(r"t=\sqrt{x}>0,\quad x=t^2")
        html += line(expression + "=" + changed)
        html += "".join(line(step) for step in dict.fromkeys(check.trace))
        html += line(
            changed + "=" + sp.latex(sp.Rational(value.numerator, value.denominator))
        )
    return finish(condition, answer, solution, format_answer(value), html)
