"""Exact dot products and unknown lengths from a known angle between vectors."""

import re
from fractions import Fraction

import sympy as sp

from solution_runner.pipelines.core.numbers import format_answer, parse_rational
from solution_runner.pipelines.probability.bernoulli import RATIONAL
from solution_runner.pipelines.probability.common import (
    UnsupportedCondition,
    finish,
    line,
    require_content,
)

_VEC = r"\\vec\{[a-z]\}"
_UNSIGNED = rf"(?:{RATIONAL}(?:\\sqrt\{{\d{{1,6}}\}})?|\\sqrt\{{\d{{1,6}}\}})"
_VALUE = rf"[−–-]?{_UNSIGNED}"
_DEGREE = r"(?:°|\^\{\\circ\})"
_FORWARD = re.compile(
    rf"Длины векторов (?P<a>{_VEC}) и (?P<b>{_VEC}) равны (?P<first>{_VALUE}) и (?P<second>{_VALUE}), а угол между ними равен (?P<angle>\d{{1,3}}){_DEGREE}\. Найдите скалярное произведение (?P=a)\s*\\cdot\s*(?P=b)\."
)
_INVERSE = re.compile(
    rf"Длина вектора (?P<a>{_VEC}) равна (?P<first>{_VALUE}), угол между векторами (?P=a) и (?P<b>{_VEC}) равен (?P<angle>\d{{1,3}}){_DEGREE}, а скалярное произведение (?P=a)\s*\\cdot\s*(?P=b) равно (?P<second>{_VALUE})\. Найдите длину вектора (?P=b)\."
)
_MEASURE = re.compile(
    rf"(?P<sign>-?)(?P<coefficient>{RATIONAL})?(?:\\sqrt\{{(?P<radicand>\d{{1,6}})\}})?"
)


def measure(token):
    token = token.replace("−", "-").replace("–", "-")
    if len(token) > 200:
        raise UnsupportedCondition("the exact measurement is too long")
    match = _MEASURE.fullmatch(token)
    if match is None or not (match["coefficient"] or match["radicand"]):
        raise UnsupportedCondition("unsupported exact scalar measurement")
    coefficient = parse_rational(match["coefficient"] or "1")
    radicand = int(match["radicand"] or "1")
    if radicand == 0:
        raise UnsupportedCondition("a radical measurement requires a positive radicand")
    value = sp.Rational(coefficient.numerator, coefficient.denominator) * sp.sqrt(
        radicand
    )
    return -value if match["sign"] else value


def cosine(angle):
    if not isinstance(angle, int) or not 0 <= angle <= 180:
        raise UnsupportedCondition(
            "an angle between nonzero vectors must lie in [0,180] degrees"
        )
    return sp.cos(sp.pi * sp.Rational(angle, 180))


def metric_value(first, second, angle, *, inverse=False):
    if first.is_positive is not True or (
        not inverse and second.is_positive is not True
    ):
        raise UnsupportedCondition("the specified vector lengths must be positive")
    c = cosine(angle)
    if inverse and c == 0:
        raise UnsupportedCondition(
            "a right angle does not determine the unknown vector length from a dot product"
        )
    value = sp.simplify(second / (first * c) if inverse else first * second * c)
    if inverse and value.is_positive is not True:
        raise UnsupportedCondition(
            "the dot product sign is inconsistent with the given angle and a positive length"
        )
    return value


def _answer(value):
    if value.is_Rational is not True:
        raise UnsupportedCondition(
            "the exact answer is not rational in the supported format"
        )
    return format_answer(Fraction(int(value.p), int(value.q)))


def _forward(first, second, angle, names):
    a, b = names
    value = metric_value(first, second, angle)
    c = cosine(angle)
    html = "<p>Скалярное произведение двух векторов равно произведению их длин на косинус угла между ними:</p>"
    html += line(rf"{a}\cdot {b}=|{a}|\,|{b}|\cos\alpha")
    html += line(rf"\cos {angle}^{{\circ}}={sp.latex(c)}")
    html += "<p>Подставим данные длины и значение косинуса:</p>"
    html += line(
        rf"{a}\cdot {b}=\left({sp.latex(first)}\right)\cdot\left({sp.latex(second)}\right)\cdot\left({sp.latex(c)}\right)"
    )
    html += line(rf"{a}\cdot {b}={sp.latex(value)}")
    return _answer(value), html


def _inverse(first, product, angle, names):
    a, b = names
    value = metric_value(first, product, angle, inverse=True)
    c = cosine(angle)
    html = "<p>Запишем определение скалярного произведения и выразим неизвестную длину. Длины векторов положительны, а деление возможно при ненулевом косинусе:</p>"
    html += line(rf"{a}\cdot {b}=|{a}|\,|{b}|\cos\alpha")
    html += line(rf"|{b}|=\frac{{{a}\cdot {b}}}{{|{a}|\cos\alpha}}")
    html += line(rf"\cos {angle}^{{\circ}}={sp.latex(c)}")
    html += line(
        rf"|{b}|=\frac{{{sp.latex(product)}}}{{\left({sp.latex(first)}\right)\cdot\left({sp.latex(c)}\right)}}={sp.latex(value)}"
    )
    return _answer(value), html


def build_context_repair_plan(context):
    _, condition, answer_section, solution, text = require_content(context)
    forward = _FORWARD.fullmatch(text)
    inverse = _INVERSE.fullmatch(text)
    match = forward or inverse
    if match is None or match["a"] == match["b"]:
        raise UnsupportedCondition("unsupported complete length-angle vector relation")
    first, second = measure(match["first"]), measure(match["second"])
    renderer = _forward if forward else _inverse
    answer, html = renderer(
        first, second, int(match["angle"]), (match["a"], match["b"])
    )
    return finish(condition, answer_section, solution, answer, html)
