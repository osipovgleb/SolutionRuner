"""Read repeated affine poles and squared numerators without cancelling domains."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..calculus.common import real_roots
from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X, polynomial
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser
from .power_arithmetic import ScalarParser, balanced, clean

Y = sp.Symbol("y", real=True)


def fractions(text):
    result = []
    for match in re.finditer(r"\\frac", text):
        numerator, end = balanced(text, match.end())
        denominator, end = balanced(text, end)
        result.append((numerator, denominator, end))
    return result


def square_fraction(text):
    if not text.startswith(r"\frac"):
        return None
    numerator, end = balanced(text, 5)
    denominator, end = balanced(text, end)
    if end != len(text) or not numerator.startswith("("):
        return None
    inside, index = balanced(numerator, 0, "(", ")")
    if numerator[index:] not in ("^{2}", "^2"):
        return None
    p = polynomial(inside)
    d = ScalarParser(denominator, {"x"}).parse()
    if d.free_symbols - {X} or not d.is_polynomial(X) or sp.Poly(d, X).degree() != 1:
        raise UnsupportedCondition(
            "the common denominator must be one exact affine factor"
        )
    return p, d


def shifted_laurent(formula):
    text = clean(formula)
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete rational equation is required")
    poles = []
    for _, denominator, _ in fractions(text):
        p = polynomial(denominator)
        if p == 0:
            raise UnsupportedCondition("an original rational denominator is zero")
        if sp.Poly(p, X).degree() > 0:
            poles.extend(real_roots(p, X))
    poles = set(poles)
    if len(poles) != 1 or next(iter(poles)).is_Rational is not True:
        raise UnsupportedCondition("one common rational affine pole must be retained")
    pole = next(iter(poles))
    atom = clean(sp.latex(X - pole))
    if pole == 0:
        translated = text.replace("x", "y")
    else:
        translated = text.replace("(" + atom + ")", "y").replace(
            "{" + atom + "}", "{y}"
        )
    left, right = translated.split("=")
    readers = [LaurentParser(part) for part in (left, right)]
    values = [symbolic(p.parse()) for p in readers]
    if any(v.free_symbols - {Y} for v in values) or set.union(
        *(p.nonzero for p in readers)
    ) != {"y"}:
        raise UnsupportedCondition(
            "every variable occurrence and denominator must use the same affine shift"
        )
    difference = sp.expand(values[0] - values[1])
    if any(
        term.as_powers_dict().get(Y, 0) not in (-2, -1, 0, 1, 2)
        for term in sp.Add.make_args(difference)
    ):
        raise UnsupportedCondition(
            "the shifted Laurent equation must have powers between minus two and two"
        )
    return pole, translated, difference


def substitution_scale(translated, parent_html):
    choices = []
    for span in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        text = "".join(span["data-inline-latex"].split())
        if text.startswith(r"t=\frac"):
            choices.append("fraction")
        elif text.startswith("t=x"):
            choices.append("unit")
    if not choices or len(set(choices)) != 1:
        raise UnsupportedCondition(
            "the parent must specify one reciprocal substitution style"
        )
    if choices[0] == "unit":
        return sp.Integer(1)
    matches = re.findall(r"\\frac\{y\}\{(\d+(?:\.\d+)?)\}", translated)
    if len(set(matches)) != 1 or sp.Rational(matches[0]) <= 0:
        raise UnsupportedCondition(
            "the child must specify one positive linear reciprocal coefficient"
        )
    return 1 / sp.Rational(matches[0])
