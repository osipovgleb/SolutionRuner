"""Read complete logarithm quotients and one principal affine square-root change."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import logarithm, read_equation
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser
from .logarithm_factor_arguments import read_polynomial
from .logarithm_parser import LogarithmParser
from .power_arithmetic import balanced, clean
from .rational_inequality import OPERATORS
from .rational_inequality_parser import X, polynomial

Q = sp.Symbol("q", real=True)


def fraction_parts(formula):
    parts = re.split(
        r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula.removesuffix(".")
    )
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition("one complete logarithmic inequality is required")
    left = clean(parts[0])
    if not left.startswith(r"\frac"):
        raise UnsupportedCondition("one complete outer logarithm fraction is required")
    numerator, index = balanced(left, 5)
    denominator, index = balanced(left, index)
    if index != len(left):
        raise UnsupportedCondition(
            "no external terms may be discarded around the fraction"
        )
    return numerator, denominator, parts[2].strip(), OPERATORS[parts[1]]


@dataclass(frozen=True)
class Coordinate:
    variable: str
    shift: object

    @property
    def working(self):
        return "y" if self.shift is not None else self.variable

    def read(self, text):
        parser = LaurentParser(re.sub(r"x(?=\()", lambda _: r"x\cdot", text))
        value = symbolic(parser.parse())
        if parser.nonzero or value.free_symbols - (
            {X, Q} if self.shift is not None else {X}
        ):
            raise UnsupportedCondition(
                "original logarithm arguments must be polynomials without hidden poles"
            )
        if self.shift is not None:
            value = value.subs({X: X**2 - self.shift, Q: X}, simultaneous=True)
        value = sp.expand(value)
        p = sp.Poly(value, X)
        if (
            p.is_zero
            or p.degree() > 20
            or any(
                c.is_Rational is not True or max(abs(c.p), c.q) > 10**12
                for c in p.all_coeffs()
            )
        ):
            raise UnsupportedCondition(
                "bounded rational polynomial arguments are required"
            )
        return value


def coordinate(numerator, denominator):
    text = numerator + denominator
    plain = re.sub(r"\\[a-zA-Z]+", "", text)
    variables = set(re.findall("[a-zA-Z]", plain))
    if variables not in ({"x"}, {"y"}):
        raise UnsupportedCondition("one original x or y variable is required")
    variable = next(iter(variables))
    pieces = [
        re.sub(r"(?<![a-zA-Z])y(?![a-zA-Z])", "x", part)
        for part in (numerator, denominator)
    ]
    shifts = set()
    for part in pieces:
        index = 0
        while (start := part.find(r"\sqrt", index)) >= 0:
            raw, end = balanced(part, start + 5)
            radicand, excluded = read_polynomial(raw)
            offset = sp.expand(radicand - X)
            if excluded or offset.is_Integer is not True or abs(offset) > 10:
                raise UnsupportedCondition(
                    "one principal square root of x plus a small integer is required"
                )
            shifts.add(offset)
            index = end
    if len(shifts) > 1:
        raise UnsupportedCondition(
            "all variable radicals must share the same affine radicand"
        )
    shift = next(iter(shifts)) if shifts else None
    if shift is not None:
        for i, part in enumerate(pieces):
            result = ""
            while (start := part.find(r"\sqrt")) >= 0:
                _, end = balanced(part, start + 5)
                result += part[:start] + "q"
                part = part[end:]
            pieces[i] = result + part
    return Coordinate(variable, shift), tuple(pieces)


def complete_log(text, reader):
    reference = None
    if text.startswith(r"\ln"):
        text = r"\log_{2}" + text[3:]
        reference = sp.E
        style = r"\ln"
    elif text.startswith(r"\lg"):
        text = r"\log_{10}" + text[3:]
        reference = sp.Integer(10)
        style = r"\lg"
    else:
        style = None
    if not text.startswith(r"\log_"):
        raise UnsupportedCondition(
            "one complete common-reference logarithm is required"
        )
    atom, power, end = logarithm(
        text, 0, X, extended=True, argument_reader=reader, argument_powers=True
    )
    if (
        power != 1
        or atom.root
        or end != len(text)
        or atom.base.is_Rational is not True
        or max(abs(atom.base.p), atom.base.q) > 1000
    ):
        raise UnsupportedCondition(
            "each quotient entry must be one complete unsquared logarithm"
        )
    return atom, reference if reference is not None else atom.base, style


def ratio_input(formula):
    numerator, denominator, right, operator = fraction_parts(formula)
    bound = LogarithmParser(right).parse().value
    if bound.is_Rational is not True or bound.p != 1 or bound.q not in (3, 5, 7, 9):
        raise UnsupportedCondition(
            "the numeric logarithm quotient must equal one over a reviewed odd power"
        )
    coords, parts = coordinate(numerator, denominator)
    first, reference, style = complete_log(parts[0], coords.read)
    second, other, _ = complete_log(parts[1], coords.read)
    if reference != other:
        raise UnsupportedCondition(
            "the quotient logarithms must have the same original reference base"
        )
    degree = int(bound.q)
    scalar, factors = sp.factor_list(second.argument, X)
    coefficient = scalar ** sp.Rational(1, degree)
    if (
        scalar <= 0
        or coefficient.is_Rational is not True
        or any(k % degree for _, k in factors)
    ):
        raise UnsupportedCondition(
            "the denominator argument must be the complete odd polynomial power"
        )
    B = sp.expand(coefficient * sp.prod(f ** (k // degree) for f, k in factors))
    A = first.argument
    if (
        polynomial(A).degree() != 2
        or polynomial(B).degree() != 2
        or polynomial(A).LC() <= 0
        or polynomial(B).LC() <= 0
        or sp.expand(B**degree - second.argument) != 0
    ):
        raise UnsupportedCondition(
            "the reviewed ratio needs two upward quadratics and the exact argument power"
        )
    return coords, A, B, degree, reference, style, right, operator


def square_input(formula):
    numerator, denominator, right, operator = fraction_parts(formula)
    if clean(right) != "0":
        raise UnsupportedCondition(
            "the reviewed squared-logarithm fraction must be compared with zero"
        )
    reader = lambda text: read_polynomial(text)[0]
    top, expr = read_equation(
        numerator + "=0", extended=True, argument_reader=reader, argument_powers=True
    )
    bottom, den = read_equation(
        denominator + "=0", extended=True, argument_reader=reader, argument_powers=True
    )
    if (
        len(top) != 2
        or len(bottom) != 2
        or any(a.root or a.denominator for a in (*top, *bottom))
    ):
        raise UnsupportedCondition(
            "two numerator logs and two complete denominator logs are required"
        )
    base = top[0].base
    if (
        base.is_Rational is not True
        or base <= 1
        or max(base.p, base.q) > 1000
        or any(a.base != base for a in (*top, *bottom))
    ):
        raise UnsupportedCondition("one common increasing rational base is required")
    if (
        expr != top[0].symbol - top[1].symbol
        or bottom[0].argument != X**2
        or bottom[1].argument != X**4
    ):
        raise UnsupportedCondition(
            "an affine log difference and the complete x-squared/fourth-power denominator are required"
        )
    if any(polynomial(a.argument).degree() != 1 for a in top):
        raise UnsupportedCondition("the numerator arguments must be affine")
    den = sp.expand(den.subs(bottom[1].symbol, 2 * bottom[0].symbol))
    p = sp.Poly(den, bottom[0].symbol)
    if p.degree() != 2 or p.LC() != 1 or sp.discriminant(p) != 0:
        raise UnsupportedCondition(
            "the whole logarithm denominator must be a monic perfect square"
        )
    level = -p.nth(1) / 2
    if level.is_Integer is not True or not -4 <= level <= -1:
        raise UnsupportedCondition(
            "a reviewed negative integer denominator level is required"
        )
    return base, top[0].argument, top[1].argument, level, operator
