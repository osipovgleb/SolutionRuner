"""Cancel root powers and open absolute values using explicit domains."""

import re
from fractions import Fraction

import sympy as sp

from ..core.numbers import format_answer
from ..probability.common import UnsupportedCondition, finish, line
from ..triangles.isosceles.planner import _section
from .calculation_input import read_calculation
from .expression_condition import read_math_markup
from .expression_repair import with_condition_repair
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser
from .power_arithmetic import ScalarParser, clean
from .verified_expression_repair import repair_verified_condition


def build_nonzero_root_power_plan(context):
    _, condition, answer, solution, expression, parameters = read_calculation(context)
    pattern = r"\\frac\{\(\\sqrt(?:\[(?P<n>\d+)\])?\{(?P<c>\d+)(?P<v>[a-z])\^\{(?P<p>\d+)\}\}\)\^\{(?P<q>\d+)\}\}\{(?P=v)\^\{(?P<r>\d+)\}\}"
    match = re.fullmatch(pattern, clean(expression))
    if (
        not match
        or parameters.bindings
        or parameters.positive
        or parameters.definition
        or parameters.nonzero != {match["v"]}
    ):
        raise UnsupportedCondition(
            "a root power quotient and its explicit nonzero domain are required"
        )
    n, c, p, q, r = (
        int(match["n"] or 2),
        int(match["c"]),
        int(match["p"]),
        int(match["q"]),
        int(match["r"]),
    )
    if (
        not 2 <= n <= 100
        or not 1 <= c <= 10**6
        or p % 2
        or not 2 <= p <= 100
        or not 1 <= q <= 1000
        or q % n
        or p * (q // n) != r
    ):
        raise UnsupportedCondition(
            "the root power does not exactly cancel the denominator"
        )
    k = q // n
    v = match["v"]
    value = c**k
    if value.bit_length() > 4096:
        raise UnsupportedCondition("root power result exceeds the exact range")
    html = "<p>Степень корня кратна его показателю. Подкоренное выражение положительно при заданном ненулевом значении переменной:</p>"
    html += line(rf"{v}\ne0,\quad {c}{v}^{{{p}}}>0")
    html += line(r"(\sqrt[n]{u})^{nk}=u^k\quad(u>0)")
    html += line(expression + rf"=\frac{{({c}{v}^{{{p}}})^{{{k}}}}}{{{v}^{{{r}}}}}")
    html += (
        "<p>Раскроем степень произведения и сократим одинаковые ненулевые степени:</p>"
    )
    html += line(rf"\frac{{{c}^{{{k}}}{v}^{{{p * k}}}}}{{{v}^{{{r}}}}}={c}^{{{k}}}")
    html += line(rf"{c}^{{{k}}}={value}")
    return finish(condition, answer, solution, str(value), html)


def _domain_question(context):
    content, condition, formulas, text = read_math_markup(context, indexed=True)
    if (
        content.get("assets")
        or condition.get("asset_keys")
        or len(formulas) != 2
        or not re.fullmatch(r"Найдите значение выражения \ufff00 при \ufff01\.?", text)
    ):
        raise UnsupportedCondition(
            "a complete radical question and one domain are required"
        )
    return content, condition, formulas


def build_upper_bound_plan(context):
    content, condition, formulas = _domain_question(context)
    query = re.fullmatch(
        r"(?P<v>[a-z])\+\\sqrt\{(?P<polynomial>.+)\}", clean(formulas[0])
    )
    bound = re.fullmatch(r"([a-z])\\le(.+)", clean(formulas[1]))
    if not query or not bound or query["v"] != bound[1]:
        raise UnsupportedCondition("the square root requires the matching upper bound")
    k = ScalarParser(bound[2]).parse()
    if k.is_Rational is not True:
        raise UnsupportedCondition("an exact rational upper bound is required")
    polynomial = symbolic(LaurentParser(query["polynomial"]).parse())
    x = sp.Symbol(query["v"], real=True)
    if sp.expand(polynomial - (x - k) ** 2) != 0:
        raise UnsupportedCondition(
            "the radicand is not the square centred at the domain endpoint"
        )
    v = query["v"]
    centre = sp.latex(k)
    square = sp.latex((x - k) ** 2)
    absolute = sp.latex(sp.Abs(x - k))
    html = "<p>Выделим полный квадрат под корнем:</p>" + line(
        sp.latex(polynomial) + "=" + square
    )
    html += line(formulas[0] + "=" + v + rf"+\sqrt{{{square}}}")
    html += "<p>Арифметический квадратный корень из квадрата равен модулю. Раскроем модуль с учётом заданного неравенства:</p>"
    html += line(r"\sqrt{u^2}=|u|")
    html += line(rf"{v}\le {centre},\quad {sp.latex(x - k)}\le0")
    html += line(absolute + "=" + sp.latex(k - x))
    html += line(formulas[0] + "=" + v + "+(" + sp.latex(k - x) + ")=" + centre)
    return finish(
        condition,
        _section(content, "answer"),
        _section(content, "solution"),
        format_answer(Fraction(int(k.p), int(k.q))),
        html,
    )


def build_interval_plan(context):
    prepared, change = repair_verified_condition(context)
    content, condition, formulas = _domain_question(prepared)
    domain = re.fullmatch(r"(-?\d+)\\le([a-z])\\le(-?\d+)", clean(formulas[1]))
    query = re.fullmatch(
        r"\\sqrt\{\((?P<v>[a-z])-(?P<a>\d+)\)\^\{2\}\}\+\\sqrt\{\((?P=v)-(?P<b>\d+)\)\^\{2\}\}",
        clean(formulas[0]),
    )
    if (
        not domain
        or not query
        or domain[2] != query["v"]
        or int(domain[1]) != int(query["a"])
        or int(domain[3]) != int(query["b"])
        or int(domain[1]) > int(domain[3])
    ):
        raise UnsupportedCondition(
            "the two complete squares must be inside the roots on the matching interval"
        )
    a, b, v = int(domain[1]), int(domain[3]), domain[2]
    html = "<p>Заменим корни из квадратов модулями:</p>" + line(r"\sqrt{u^2}=|u|")
    html += line(formulas[0] + rf"=|{v}-{a}|+|{v}-{b}|")
    html += (
        "<p>На заданном отрезке первый модуль неотрицателен внутри, а второй неположителен:</p>"
        + line(formulas[1])
    )
    html += line(rf"|{v}-{a}|={v}-{a},\quad |{v}-{b}|={b}-{v}")
    html += line(formulas[0] + rf"=({v}-{a})+({b}-{v})={b - a}")
    return with_condition_repair(
        finish(
            condition,
            _section(content, "answer"),
            _section(content, "solution"),
            str(b - a),
            html,
        ),
        change,
    )
