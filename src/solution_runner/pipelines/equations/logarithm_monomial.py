"""Expand a logarithm of a monomial using one given logarithm."""

import re
from fractions import Fraction

import sympy as sp

from ..core.numbers import format_answer
from ..probability.common import UnsupportedCondition, finish, line
from ..triangles.isosceles.planner import _section
from .expression_condition import read_math_markup
from .laurent_parser import LaurentParser
from .power_arithmetic import ScalarParser, clean


def build_context_repair_plan(context):
    content, condition, formulas, text = read_math_markup(context, indexed=True)
    if (
        content.get("assets")
        or condition.get("asset_keys")
        or len(formulas) != 2
        or not re.fullmatch(
            r"Найдите(?: значение выражения)? \ufff00, если \ufff01\.?", text
        )
    ):
        raise UnsupportedCondition(
            "a whole monomial question and one logarithm relation are required"
        )
    query = re.fullmatch(r"\\log_([ab])(.+)", clean(formulas[0]))
    relation = re.fullmatch(r"\\log_([ab])([ab])=(.+)", clean(formulas[1]))
    if not query or not relation or relation[1] == relation[2]:
        raise UnsupportedCondition("unsupported given logarithm relation")
    given = ScalarParser(relation[3]).parse()
    if given.is_Rational is not True:
        raise UnsupportedCondition("the given logarithm must be an exact rational")
    parser = LaurentParser(query[2])
    poly = parser.parse()
    if len(poly) != 1:
        raise UnsupportedCondition("the logarithm argument must be a monomial")
    powers, coefficient = next(iter(poly.items()))
    if coefficient != 1 or any(name not in "ab" for name, _ in powers):
        raise UnsupportedCondition(
            "only the declared positive variables form the monomial"
        )
    powers = dict(powers)
    base = query[1]
    other = "b" if base == "a" else "a"
    reciprocal = relation[1] != base
    if reciprocal and given == 0:
        raise UnsupportedCondition("a zero logarithm cannot be inverted")
    if given == 0 and query[1] == relation[2]:
        raise UnsupportedCondition(
            "the relation makes the query logarithm base equal to one"
        )
    value = sp.Rational(powers.get(base, 0)) + powers.get(other, 0) * (
        1 / given if reciprocal else given
    )
    html = "<p>Применим логарифм произведения и степени. Учитываем область определения логарифмов:</p>"
    html += line(
        r"a>0,\quad b>0,\quad " + base + r"\ne1,\quad " + relation[1] + r"\ne1"
    )
    html += line(r"\log_c(uv)=\log_c u+\log_c v,\quad\log_c(u^r)=r\log_c u")
    m, n = powers.get(base, 0), powers.get(other, 0)
    expanded = rf"({m})\log_{{{base}}}{base}+({n})\log_{{{base}}}{other}"
    reduced = rf"{m}+({n})\log_{{{base}}}{other}"
    html += line(formulas[0] + "=" + expanded)
    html += line(expanded + "=" + reduced)
    html += "<p>Подставим заданное значение логарифма:</p>"
    if reciprocal:
        html += line(
            rf"\log_{{{base}}}{other}=\frac1{{\log_{{{other}}}{base}}}=\frac1{{{sp.latex(given)}}}"
        )
    else:
        html += line(formulas[1])
    html += line(
        reduced
        + rf"={m}+({n})\cdot({sp.latex(1 / given if reciprocal else given)})="
        + sp.latex(value)
    )
    return finish(
        condition,
        _section(content, "answer"),
        _section(content, "solution"),
        format_answer(Fraction(int(value.p), int(value.q))),
        html,
    )
