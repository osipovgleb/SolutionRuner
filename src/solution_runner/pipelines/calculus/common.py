"""Read complete text questions and reuse the reviewed polynomial grammar."""

import re
from copy import deepcopy
from fractions import Fraction

import sympy as sp
from bs4 import BeautifulSoup

from ..core.numbers import format_answer
from ..equations.expression_condition import read_math_markup
from ..equations.laurent_arithmetic import symbolic
from ..equations.laurent_parser import LaurentParser
from ..probability.common import UnsupportedCondition
from ..triangles.isosceles.planner import _normalized_content, _section

X, T = sp.symbols("x t", real=True)


def read(context):
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets") or condition.get("asset_keys"):
        raise UnsupportedCondition(
            "this analytic calculus rule requires a text-only condition"
        )
    soup = BeautifulSoup(condition.get("html", ""), "html.parser")
    prepared = deepcopy(context)
    for tag in soup.find_all("sup"):
        if (
            tag.attrs
            or tag.find(True) is not None
            or not re.fullmatch(r"[1-9]\d?", tag.get_text())
        ):
            raise UnsupportedCondition("unsupported polynomial superscript markup")
        tag.replace_with("^{" + tag.get_text() + "}")
    _section(prepared["normalized_content"], "condition")["html"] = str(soup)
    _, _, formulas, text = read_math_markup(prepared, indexed=True)
    for i in reversed(range(len(formulas))):
        text = text.replace("\ufff0" + str(i), formulas[i])
    text = text.replace("\u2060", "").replace("\u200b", "").replace("ё", "е")
    text = re.sub(r"\bх\b", "x", text)
    return condition, _section(content, "answer"), _section(content, "solution"), text


def polynomial(text, variable, parameters=()):
    parser = LaurentParser(text)
    parsed = parser.parse()
    if parser.nonzero or any(p < 0 or p != int(p) for key in parsed for _, p in key):
        raise UnsupportedCondition(
            "calculus input must be a polynomial without original variable denominators"
        )
    result = symbolic(parsed)
    allowed = {variable, *[sp.Symbol(p, real=True) for p in parameters]}
    if result.free_symbols - allowed:
        raise UnsupportedCondition("an undeclared polynomial variable remains")
    if sp.Poly(result, variable).degree() > 6:
        raise UnsupportedCondition("the polynomial degree exceeds the reviewed range")
    return result


def real_roots(expression, variable):
    poly = sp.Poly(expression, variable)
    if poly.degree() not in (1, 2) or any(
        c.is_Rational is not True for c in poly.all_coeffs()
    ):
        raise UnsupportedCondition(
            "a nonconstant linear or quadratic exact equation is required"
        )
    if poly.degree() == 1:
        return [-poly.nth(0) / poly.nth(1)]
    a, b, c = poly.all_coeffs()
    d = b * b - 4 * a * c
    if d < 0:
        return []
    return sorted(
        {sp.simplify((-b + direction * sp.sqrt(d)) / (2 * a)) for direction in [-1, 1]}
    )


def answer(value):
    value = sp.simplify(value)
    if value.is_Rational is not True:
        raise UnsupportedCondition(
            "the requested calculus value is not an exact rational"
        )
    return format_answer(Fraction(int(value.p), int(value.q)))
