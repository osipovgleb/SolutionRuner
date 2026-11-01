"""Reduce complete square radicals to absolute values in one sine variable."""

import re
from dataclasses import dataclass, replace
from functools import cmp_to_key, reduce

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation, ExamAngleParser
from .exam_trigonometric_radical_equation import CIRCLE, compile_values
from .logarithm_parser import Node
from .power_arithmetic import balanced, clean

PLACEHOLDERS = sp.symbols("r v", real=True)


@dataclass(frozen=True)
class SquareRadicals:
    radicands: tuple
    linears: tuple
    coefficients: tuple
    remainder: sp.Expr
    signs: tuple
    cases: tuple
    candidates: tuple
    accepted: tuple
    method: str = ""


class Parser(ExamAngleParser):
    def _nested(self, text):
        return Parser(text, self.atoms, self.denominators, self.depth + 1).parse()

    def _primary(self):
        for name, symbol in zip(("r", "v"), PLACEHOLDERS):
            if self.text[self.index : self.index + 1] == name:
                self.index += 1
                return Node(symbol, name)
        return super()._primary()


def read(formula):
    text = clean(formula)
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete square-radical equality is required")
    plain = re.sub(r"\\[A-Za-z]+", "", text).replace("x", "")
    if re.search(r"[A-Za-z]", plain) or re.search(r"\\(?:alpha|beta|gamma)", text):
        raise UnsupportedCondition(
            "the original square-radical equation may contain only x"
        )
    radicands = []
    start = 0
    while (index := text.find(r"\sqrt{", start)) >= 0:
        inside, end = balanced(text, index + 5)
        if "x" not in inside:
            start = end
            continue
        if len(radicands) == 2:
            raise UnsupportedCondition(
                "at most two complete variable roots are reviewed"
            )
        name = ("r", "v")[len(radicands)]
        radicands.append(inside)
        text = text[:index] + "(" + name + ")" + text[end:]
        start = index + 3
    if not radicands:
        raise UnsupportedCondition("an original variable radical is required")
    atoms, denominators = {}, []
    left, right = [
        Parser(p.replace("x", r"\alpha"), atoms, denominators).parse().value
        for p in text.split("=")
    ]
    expression = sp.expand(left - right)
    coefficients = tuple(expression.coeff(p) for p in PLACEHOLDERS[: len(radicands)])
    remainder = expression.subs(dict.fromkeys(PLACEHOLDERS, 0))
    if (
        sp.expand(
            expression
            - remainder
            - sum(c * p for c, p in zip(coefficients, PLACEHOLDERS))
        )
        != 0
    ):
        raise UnsupportedCondition(
            "the roots must occur linearly without root products"
        )
    radicands = [
        ExamAngleParser(p.replace("x", r"\alpha"), atoms, denominators).parse().value
        for p in radicands
    ]
    if not atoms or any(
        a.function not in ("sin", "cos") or a.shift != 0 for a in atoms.values()
    ):
        raise UnsupportedCondition("unshifted sine and cosine arguments are required")
    scale = reduce(sp.gcd, (a.coefficient for a in atoms.values()))
    if scale.is_Rational is not True or scale <= 0 or scale.p > 12 or scale.q > 2:
        raise UnsupportedCondition(
            "one bounded positive integer or half-integer base angle is required"
        )
    scaled = {
        p: replace(a, coefficient=a.coefficient / scale) for p, a in atoms.items()
    }
    values, poles, _ = compile_values(
        [remainder, *coefficients, *radicands], scaled, denominators
    )
    if poles:
        raise UnsupportedCondition(
            "square-radical absolute methods have no extra poles"
        )
    values = tuple(sp.expand(sp.rem(v, CIRCLE, C)) for v in values)
    remainder, coefficients, radicands = (
        values[0],
        values[1 : 1 + len(coefficients)],
        values[1 + len(coefficients) :],
    )
    if any(c.free_symbols or c == 0 for c in coefficients):
        raise UnsupportedCondition(
            "every radical must have a nonzero constant multiplier"
        )
    if any(
        v.free_symbols - {S, C}
        or not v.is_polynomial(S, C)
        or sp.Poly(v, S, C).total_degree() > 2
        for v in (remainder, *radicands)
    ):
        raise UnsupportedCondition("quadratic unit-circle polynomials are required")
    return scale, remainder, coefficients, radicands


def square(radicand):
    if radicand.has(C):
        for polynomial in (radicand + CIRCLE, radicand - CIRCLE, radicand):
            coefficient, factors = sp.factor_list(polynomial, S, C)
            if len(factors) == 1 and factors[0][1] == 2:
                linear = sp.sqrt(coefficient) * factors[0][0]
                if (
                    coefficient > 0
                    and sp.Poly(linear, S, C).total_degree() == 1
                    and sp.rem(sp.expand(linear**2 - radicand), CIRCLE, C) == 0
                ):
                    return linear
        raise UnsupportedCondition(
            "the reviewed unit-circle radicand is not a linear square"
        )
    if sp.degree(radicand, S) != 2:
        raise UnsupportedCondition(
            "each variable radical must be a complete linear square"
        )
    leading = sp.sqrt(radicand.coeff(S, 2))
    if leading.is_Rational is not True or leading <= 0:
        raise UnsupportedCondition(
            "the linear square needs a positive rational leading coefficient"
        )
    linear = leading * S + radicand.coeff(S) / (2 * leading)
    if sp.expand(linear**2 - radicand) != 0:
        raise UnsupportedCondition(
            "the radicand is not exactly the square of a linear polynomial"
        )
    return linear


def compile_squares(formula, method=""):
    scale, remainder, coefficients, radicands = read(formula)
    linears = tuple(square(r) for r in radicands)
    if method:
        from .exam_trigonometric_square_radical_cases import compile_cases

        return compile_cases(scale, remainder, coefficients, radicands, linears, method)
    if any(v.has(C) for v in (*linears, remainder)):
        raise UnsupportedCondition(
            "mixed absolute values require their reviewed parent method"
        )
    signs = tuple(
        1
        if min(v.subs(S, -1), v.subs(S, 1)) >= 0
        else -1
        if max(v.subs(S, -1), v.subs(S, 1)) <= 0
        else 0
        for v in linears
    )
    cases = ()
    candidates = ()
    if all(signs):
        raw = sp.expand(
            remainder + sum(c * s * v for c, s, v in zip(coefficients, signs, linears))
        )
        if sp.degree(raw, S) not in (1, 2):
            raise UnsupportedCondition(
                "the fixed-sign reduction must have degree one or two"
            )
        candidates = (tuple(sorted(roots(raw.subs(S, X)), key=cmp_to_key(compare))),)
    elif len(linears) == 1:
        right = sp.expand(-remainder / coefficients[0])
        cases = tuple(sp.expand(linears[0] - sign * right) for sign in (1, -1))
        if any(sp.degree(p, S) not in (1, 2) for p in cases):
            raise UnsupportedCondition(
                "both absolute-value branches must have degree one or two"
            )
        candidates = tuple(
            tuple(sorted(roots(p.subs(S, X)), key=cmp_to_key(compare))) for p in cases
        )
    else:
        raise UnsupportedCondition(
            "two sign-changing absolute values need a separately reviewed method"
        )
    accepted = tuple(
        dict.fromkeys(
            v
            for row in candidates
            for v in row
            if compare(v, -sp.S.One) >= 0
            and compare(v, sp.S.One) <= 0
            and sp.simplify(
                remainder.subs(S, v)
                + sum(c * abs(l.subs(S, v)) for c, l in zip(coefficients, linears))
            )
            == 0
        )
    )
    if not accepted:
        raise UnsupportedCondition(
            "no reviewed sine level remains after the absolute-value conditions"
        )
    raw = sp.prod(S - v for v in accepted)
    data = SquareRadicals(
        radicands, linears, coefficients, remainder, signs, cases, candidates, accepted
    )
    return Equation(raw, (), scale, square_radicals=data)
