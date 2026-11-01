"""Certify both closed sign cases of exponentials in a complete square root."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_power_terms import read
from .exam_scalar import compare
from .exam_trigonometric_absolute import R, side
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation, ExamAngleParser
from .exam_trigonometric_radical_equation import compile_values, same, variable_radicals
from .logarithm_arithmetic import actual, log_ratio

E = sp.Symbol("e", positive=True)


@dataclass(frozen=True)
class SignCase:
    sign: int
    polynomial: sp.Expr
    powers: tuple
    levels: tuple
    accepted: tuple


@dataclass(frozen=True)
class ExponentialAbsolute:
    base: sp.Expr
    variable: sp.Symbol
    radicand: sp.Expr
    coefficients: tuple
    cases: tuple
    accepted: tuple


def reviewed(formula):
    return (
        r"\log" not in formula
        and variable_radicals(formula)
        and re.search(r"\d+\^\{[^{}]*\\(?:sqrt|sin|cos)", formula) is not None
    )


def review_parent(html, variable):
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    formulas = " ".join(
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    )
    name = r"\sinx" if variable == S else r"\cosx"
    if (
        "два случая" not in text
        or soup.find("img")
        or "двойного неравенства" not in text
        or not all(
            part in formulas
            for part in (
                r"\left|" + name + r"\right|",
                name + r"\ge0",
                name + r"\le0",
                "^{-" + name + "}",
            )
        )
        or re.search(r"\b[ty]=|=[ty]\b", formulas)
    ):
        raise UnsupportedCondition(
            "both closed absolute-exponent cases and direct exponential algebra are required"
        )


def source(formula):
    atoms, denominators, radicands = {}, [], []

    def exponent(text):
        if variable_radicals(text):
            value, radicand = side(text, atoms, denominators)
            radicands.append(radicand)
            return value
        return (
            ExamAngleParser(text.replace("x", r"\alpha"), atoms, denominators)
            .parse()
            .value
        )

    terms, constant = read(formula, exponent_reader=exponent)
    if len(terms) != 2 or len(radicands) != 1:
        raise UnsupportedCondition(
            "two exponential terms and one square root are required"
        )
    if not atoms or any(
        a.function not in ("sin", "cos")
        or a.coefficient != 1
        or a.shift != 0
        or a.variable != r"\alpha"
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "unit unshifted sine and cosine exponents are required"
        )
    values, poles, identities = compile_values(
        [*(t[2] for t in terms), radicands[0]], atoms, denominators
    )
    if poles or terms[0][1] != terms[1][1]:
        raise UnsupportedCondition(
            "one common exponential base without original poles is required"
        )
    pairs = list(zip(terms, values[:2], strict=True))
    radical = next((t for t, v in pairs if v == R), None)
    direct = next(((t, v) for t, v in pairs if v in (S, C)), None)
    if radical is None or direct is None or not same(values[2], direct[1] ** 2):
        raise UnsupportedCondition(
            "the radical must be exactly the absolute direct exponent"
        )
    coefficients = (radical[0], direct[0][0], constant)
    if any(v.is_Rational is not True or abs(v) > 10000 for v in coefficients):
        raise UnsupportedCondition(
            "bounded rational exponential coefficients are required"
        )
    return radical[1], direct[1], values[2], coefficients, identities


def sign_case(base, coefficients, sign):
    a, b, c = coefficients
    polynomial = (a + b) * E + c if sign == 1 else -(b * E * E + c * E + a)
    if not 1 <= sp.degree(polynomial, E) <= 2:
        raise UnsupportedCondition(
            "each closed case must give a linear or quadratic equation"
        )
    powers = sorted(
        roots(polynomial.subs(E, X)), key=lambda v: compare(v, sp.S.Zero) <= 0
    )
    levels, accepted = [], []
    for value in powers:
        if compare(value, sp.S.Zero) <= 0:
            levels.append(None)
            continue
        level = actual(log_ratio(base, value))
        if level.is_Rational is not True or abs(level) > 20 or level.q > 12:
            raise UnsupportedCondition(
                "exact bounded rational trigonometric levels are required"
            )
        levels.append(level)
        if -1 <= level <= 1 and sign * level >= 0:
            accepted.append(level)
    return SignCase(
        sign, sp.expand(polynomial), tuple(powers), tuple(levels), tuple(accepted)
    )


def compile_absolute(formula, parent_html):
    base, variable, radicand, coefficients, identities = source(formula)
    review_parent(parent_html, variable)
    cases = tuple(sign_case(base, coefficients, sign) for sign in (1, -1))
    accepted = tuple(dict.fromkeys(v for row in cases for v in row.accepted))
    if not accepted:
        raise UnsupportedCondition(
            "no reviewed trigonometric level survives both closed cases"
        )
    data = ExponentialAbsolute(base, variable, radicand, coefficients, cases, accepted)
    return Equation(
        sp.prod(variable - level for level in accepted),
        identities,
        sp.S.One,
        exponential_absolute=data,
    )
