"""Common radical factors and binomial squares use the existing typed grammar."""

from fractions import Fraction

import sympy as sp

from ..core.numbers import format_answer
from ..probability.common import UnsupportedCondition, finish, line
from .calculation_input import read_calculation
from .expression_repair import with_condition_repair
from .logarithm_parser import LogarithmParser
from .logarithm_proof import walk
from .verified_expression_repair import repair_verified_condition


def _read(context):
    _, condition, answer, solution, expression, parameters = read_calculation(context)
    if (
        parameters.bindings
        or parameters.positive
        or parameters.nonzero
        or parameters.definition
    ):
        raise UnsupportedCondition(
            "the numeric radical method takes no variable declarations"
        )
    node = LogarithmParser(expression).parse()
    if any(n.kind == "log" for n in walk(node)) or node.value.is_Rational is not True:
        raise UnsupportedCondition("an exact rational radical calculation is required")
    return condition, answer, solution, expression, node


def build_common_factor_plan(context):
    condition, answer, solution, expression, node = _read(context)
    if node.kind != "divide":
        raise UnsupportedCondition("the radical method requires a quotient")
    numerator, denominator = node.children
    if numerator.kind not in ("add", "subtract") or denominator.kind != "root":
        raise UnsupportedCondition("the radical numerator must be a sum or difference")
    left, right = numerator.children
    if (
        left.kind != "root"
        or right.kind != "root"
        or any(not n.text.startswith(r"\sqrt[2]") for n in [left, right, denominator])
    ):
        raise UnsupportedCondition(
            "three square roots with a common factor are required"
        )
    decomposed = [n.value.as_coeff_Mul() for n in (left, right, denominator)]
    if len({tail for _, tail in decomposed}) != 1:
        raise UnsupportedCondition("the square-free radical factors differ")
    a, b, c = [coefficient for coefficient, _ in decomposed]
    sign = "+" if numerator.kind == "add" else "-"
    coefficient = a + b if sign == "+" else a - b
    if coefficient / c != node.value:
        raise UnsupportedCondition("the common-factor calculation disagrees")
    tail = decomposed[0][1]
    html = "<p>Переведём смешанные числа в обыкновенные дроби и выделим квадратные множители под корнями:</p>"
    html += line(r"\sqrt{u^2v}=u\sqrt v\quad(u\ge0,v\ge0)")
    for n in [left, right, denominator]:
        html += line(n.text + "=" + sp.latex(n.value))
    html += "<p>Вынесем общий ненулевой радикал и сократим его:</p>"
    html += line(
        expression
        + rf"=\frac{{({sp.latex(a)}{sign}({sp.latex(b)}))({sp.latex(tail)})}}{{({sp.latex(c)})({sp.latex(tail)})}}"
    )
    html += line(
        rf"\frac{{{sp.latex(coefficient)}}}{{{sp.latex(c)}}}={sp.latex(node.value)}"
    )
    return finish(
        condition,
        answer,
        solution,
        format_answer(Fraction(int(node.value.p), int(node.value.q))),
        html,
    )


def build_binomial_square_plan(context):
    condition, answer, solution, expression, node = _read(context)
    if node.kind != "divide" or node.children[0].kind != "power":
        raise UnsupportedCondition(
            "a binomial square over a radical denominator is required"
        )
    numerator, denominator = node.children
    binomial, exponent = numerator.children
    if (
        exponent.value != 2
        or binomial.kind not in ("add", "subtract")
        or not any(n.kind == "root" for n in walk(binomial))
    ):
        raise UnsupportedCondition("the numerator is not a radical binomial square")
    a, b = binomial.children
    sign = "+" if binomial.kind == "add" else "-"
    expanded = sp.expand(numerator.value)
    if sp.expand(expanded - node.value * denominator.value) != 0:
        raise UnsupportedCondition(
            "the radical numerator does not factor by the denominator"
        )
    html = "<p>Раскроем квадрат суммы или разности:</p>"
    html += line(r"(u\pm v)^2=u^2\pm2uv+v^2")
    html += line(
        numerator.text + rf"=({a.text})^2{sign}2({a.text})({b.text})+({b.text})^2"
    )
    html += line(numerator.text + "=" + sp.latex(expanded))
    html += "<p>Вынесем общий множитель в числителе. Знаменатель ненулевой, поэтому сокращение допустимо:</p>"
    html += line(denominator.text + r"\ne0")
    html += line(
        sp.latex(expanded) + "=(" + sp.latex(node.value) + ")(" + denominator.text + ")"
    )
    html += line(
        expression
        + rf"=\frac{{({sp.latex(node.value)})({denominator.text})}}{{{denominator.text}}}={sp.latex(node.value)}"
    )
    return finish(
        condition,
        answer,
        solution,
        format_answer(Fraction(int(node.value.p), int(node.value.q))),
        html,
    )


def build_difference_square_plan(context):
    prepared, change = repair_verified_condition(context)
    condition, answer, solution, expression, node = _read(prepared)
    if node.kind != "root" or node.children[0].kind != "subtract":
        raise UnsupportedCondition(
            "the difference of squares must be entirely under the root"
        )
    left, right = node.children[0].children
    if (
        left.kind != "power"
        or right.kind != "power"
        or left.children[1].value != 2
        or right.children[1].value != 2
    ):
        raise UnsupportedCondition("two explicit squares are required")
    a, b = left.children[0].value, right.children[0].value
    if (
        a.is_Integer is not True
        or b.is_Integer is not True
        or not a > b > 0
        or not node.text.startswith(r"\sqrt[2]")
    ):
        raise UnsupportedCondition(
            "positive integer squares and a square root are required"
        )
    html = "<p>Применим формулу разности квадратов под корнем:</p>" + line(
        r"u^2-v^2=(u-v)(u+v)"
    )
    html += line(expression + rf"=\sqrt{{({a}-{b})({a}+{b})}}")
    html += line(rf"=\sqrt{{{a - b}\cdot{a + b}}}=\sqrt{{{a * a - b * b}}}")
    html += line(
        rf"({sp.latex(node.value)})^2={a * a - b * b},\quad {sp.latex(node.value)}\ge0"
    )
    html += line(expression + "=" + sp.latex(node.value))
    return with_condition_repair(
        finish(
            condition,
            answer,
            solution,
            format_answer(Fraction(int(node.value.p), int(node.value.q))),
            html,
        ),
        change,
    )
