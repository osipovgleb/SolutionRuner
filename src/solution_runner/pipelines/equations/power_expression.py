"""Prepare exact positive-base power transformations in the source methods."""

import re
from fractions import Fraction
from math import lcm

import sympy as sp

from ..core.numbers import format_answer, format_latex_fraction
from ..probability.common import UnsupportedCondition, finish, line
from .calculation_input import read_calculation
from .power_arithmetic import ScalarParser, clean, exact_value, totals
from .power_parser import PowerParser

_NUMBER = r"\d+(?:\.\d+)?"
_THREE = re.compile(
    rf"(?P<a>{_NUMBER})\^\{{(?P<x>\\frac\{{\d+\}}\{{\d+\}})\}}\\cdot(?P<b>{_NUMBER})\^\{{(?P<y>\\frac\{{\d+\}}\{{\d+\}})\}}\\cdot(?P<c>{_NUMBER})\^\{{(?P<z>\\frac\{{\d+\}}\{{\d+\}})\}}"
)


def _sum_latex(values):
    result = ""
    for term in values:
        latex = term.latex
        result += ("+" if result and not latex.startswith("-") else "") + latex
    return result


def ledger_latex(terms, *, simplified=False, bindings=None):
    assignments = {sp.Symbol(k, real=True): v for k, v in (bindings or {}).items()}
    values = totals(terms) if simplified else None
    parts = []
    for base, exponents in sorted(
        terms.items(), key=lambda item: (isinstance(item[0], str), item[0])
    ):
        if simplified:
            exponent = values[base]
            if exponent == 0:
                continue
            text = sp.latex(exponent.subs(assignments))
        else:
            text = _sum_latex(exponents)
        label = (
            "(" + sp.latex(bindings[base]) + ")"
            if bindings and base in bindings
            else str(base)
        )
        parts.append(rf"{label}^{{{text}}}")
    return r"\cdot".join(parts) or "1"


def _main_method(expression, terms, bindings, positive=()):
    answer, substituted = exact_value(terms, bindings)
    trace = ledger_latex(terms)
    reduced = ledger_latex(terms, simplified=True)
    html = "<p>Используем свойства степеней. При положительных основаниях показатели при умножении складываются, при делении вычитаются; при возведении степени в степень перемножаются:</p>"
    html += line(
        r"a^u\cdot a^v=a^{u+v},\quad \frac{a^u}{a^v}=a^{u-v},\quad (a^u)^v=a^{uv}"
    )
    if positive:
        html += line(r",\quad ".join(name + ">0" for name in sorted(positive)))
    if r"\sqrt" in expression:
        html += line(r"\sqrt[n]{a}=a^{\frac1n}\quad(a>0)")
    html += "<p>Приведём основания к степеням простых чисел и соберём показатели одинаковых оснований:</p>"
    html += line(expression + "=" + trace)
    if reduced != trace:
        html += line(trace + "=" + reduced)
    if bindings:
        html += "<p>Подставим заданное положительное значение переменной:</p>"
        for name, value in bindings.items():
            html += line(name + "=" + sp.latex(value) + ">0")
        numeric = ledger_latex(terms, simplified=True, bindings=bindings)
        if numeric != reduced:
            html += line(
                reduced
                + "="
                + numeric
                + "="
                + ledger_latex(substituted, simplified=True)
            )
    html += line(
        ledger_latex(substituted, simplified=True) + "=" + format_latex_fraction(answer)
    )
    return answer, html


def _three_methods(expression, terms):
    match = _THREE.fullmatch(clean(expression))
    if match is None:
        raise UnsupportedCondition(
            "the three source methods require three explicit rational powers"
        )
    a, b, c = (Fraction(match[k]) for k in ("a", "b", "c"))
    x, y, z = (ScalarParser(match[k]).parse() for k in ("x", "y", "z"))
    if any(v.is_Rational is not True for v in (x, y, z)) or min(a, b, c) <= 0:
        raise UnsupportedCondition("positive bases and rational exponents are required")
    q = lcm(*(int(v.q) for v in (x, y, z)))
    if (
        not 2 <= q <= 100
        or (x, y, z) != (sp.Rational(1, q), sp.Rational(2, q), sp.Rational(q - 1, q))
        or c != a * b * b
    ):
        raise UnsupportedCondition(
            "the base relation for the three source methods does not hold"
        )
    f = format_latex_fraction
    X, Y, Z = (match[k] for k in ("x", "y", "z"))
    html = "<p>Первый способ. Запишем произведение как один корень и объединим множители под корнем:</p>"

    def root(text):
        return rf"\sqrt[{q}]" + "{" + text + "}"

    inside = rf"({f(a)})\cdot({f(b)})^2\cdot({f(c)})^{{{q - 1}}}"
    html += line(expression + "=" + root(inside))
    html += line(rf"({f(a)})\cdot({f(b)})^2={f(c)}")
    html += line(
        root(rf"({f(c)})\cdot({f(c)})^{{{q - 1}}}")
        + "="
        + root(rf"({f(c)})^{{{q}}}")
        + "="
        + f(c)
    )
    answer, main = _main_method(expression, terms, {})
    html += (
        "<p>Второй способ. Разложим основания на множители и используем свойства степеней:</p>"
        + main
    )
    html += "<p>Третий способ. Выразим третье основание через первые два:</p>"
    html += line(rf"{f(c)}=({f(a)})\cdot({f(b)})^2")
    html += line(rf"{expression}=({f(a)})^{{{X}+{Z}}}\cdot({f(b)})^{{{Y}+2\cdot({Z})}}")
    html += line(rf"({f(a)})^1\cdot({f(b)})^2={f(c)}")
    if answer != c:
        raise UnsupportedCondition("the independent power methods disagree")
    return answer, html


def build_context_repair_plan(context, *, three_methods=False):
    _content, condition, answer, solution, expression, parameters = read_calculation(
        context
    )
    bindings = parameters.bindings
    if parameters.definition or parameters.nonzero - parameters.positive:
        raise UnsupportedCondition(
            "the positive power method needs positive base assumptions"
        )
    if any(v.is_positive is not True for v in bindings.values()):
        raise UnsupportedCondition("the assigned power variables must be positive")
    terms = PowerParser(expression, set(bindings) | parameters.positive).parse()
    if three_methods:
        if bindings:
            raise UnsupportedCondition(
                "the three numeric source methods have no assigned variables"
            )
        value, html = _three_methods(expression, terms)
    else:
        value, html = _main_method(expression, terms, bindings, parameters.positive)
    return finish(condition, answer, solution, format_answer(value), html)
