"""Read closed numeric bases, polynomial arguments and a polynomial of logarithms."""

import re
from dataclasses import dataclass, replace

import sympy as sp

from ..calculus.common import polynomial
from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_input import read_interval, read_parts
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser
from .power_arithmetic import ScalarParser, balanced, clean

SYMBOLS = sp.symbols("z w u v", real=True)


@dataclass(frozen=True)
class Atom:
    base: sp.Expr
    argument: sp.Expr
    root: bool
    symbol: sp.Symbol
    denominator: bool = False


def operand(text, index):
    if text[index : index + 1] == "(":
        return balanced(text, index, "(", ")")
    if text.startswith(r"\frac", index):
        _, end = balanced(text, index + 5)
        _, end = balanced(text, end)
        return text[index:end], end
    match = re.match(r"x(?:\^\{[1-6]\}|\^[1-6])?", text[index:])
    if not match:
        raise UnsupportedCondition(
            "a complete polynomial logarithm argument is required"
        )
    return match.group(), index + match.end()


def logarithm(text, index, symbol, *, extended=False):
    index += 5
    if text[index : index + 1] == "{":
        raw, index = balanced(text, index)
    elif text[index : index + 1] in "23456789" and index < len(text):
        raw, index = text[index], index + 1
    else:
        raise UnsupportedCondition("one unambiguous numeric logarithm base is required")
    from .exam_logarithmic_algebra import polynomial as algebraic_polynomial

    base = (
        algebraic_polynomial(raw)
        if extended and "x" in raw
        else ScalarParser(raw).parse()
    )
    if not base.free_symbols and (base.is_positive is not True or base == 1):
        raise UnsupportedCondition(
            "a logarithm base must be positive and different from one"
        )
    power = 1
    if text[index : index + 1] == "^":
        index += 1
        if text[index : index + 1] == "{":
            exponent, index = balanced(text, index)
        else:
            exponent, index = text[index : index + 1], index + 1
        if exponent != "2":
            raise UnsupportedCondition(
                "only the reviewed logarithm square is supported"
            )
        power = 2
    root = text.startswith(r"\sqrt", index)
    if root:
        raw, index = balanced(text, index + 5)
    else:
        raw, index = operand(text, index)
    argument = algebraic_polynomial(raw) if extended else polynomial(raw, X)
    return Atom(base, argument, root, symbol), power, index


def read_equation(formula, *, extended=False):
    text = clean(formula.removesuffix("."))
    if text.count("=") != 1 or any(c in text for c in "zwuv"):
        raise UnsupportedCondition("one complete logarithmic equation in x is required")
    atoms = []
    while r"\log_" in text:
        if len(atoms) >= len(SYMBOLS):
            raise UnsupportedCondition(
                "at most four logarithm occurrences are supported"
            )
        start = text.index(r"\log_")
        atom, power, end = logarithm(
            text, start, SYMBOLS[len(atoms)], extended=extended
        )
        atoms.append(atom)
        text = (
            text[:start] + str(atom.symbol) + ("^2" if power == 2 else "") + text[end:]
        )
    values = []
    nonzero = set()
    for side in text.split("="):
        if extended:
            from .exam_logarithmic_algebra import polynomial as algebraic_polynomial

            # Only logarithm symbols may occur in an original monomial denominator.
            parser = LaurentParser(side)
            if r"\sqrt" in side:
                value = algebraic_polynomial(side, (X, *SYMBOLS))
            else:
                value = symbolic(parser.parse())
            nonzero.update(parser.nonzero)
        else:
            parser = LaurentParser(side)
            value = symbolic(parser.parse())
        allowed = {X, *SYMBOLS} if extended else set(SYMBOLS)
        numerator, denominator = sp.fraction(sp.cancel(value))
        if (
            (
                parser.nonzero
                and (not extended or parser.nonzero - {str(v) for v in SYMBOLS})
            )
            or value.free_symbols - allowed
            or not numerator.is_polynomial(*allowed)
            or not denominator.is_polynomial(*SYMBOLS)
        ):
            raise UnsupportedCondition(
                "unknown variables or original non-logarithmic poles"
            )
        values.append(value)
    expression = sp.expand(values[0] - values[1])
    numerator, denominator = sp.fraction(sp.cancel(expression))
    if extended and sp.Poly(numerator, X, *SYMBOLS).degree(X) > 6:
        raise UnsupportedCondition("the outer polynomial degree in x exceeds six")
    if not atoms or sp.Poly(numerator, *SYMBOLS).total_degree() > (
        4 if extended else 2
    ):
        raise UnsupportedCondition(
            "the logarithm polynomial degree exceeds the reviewed range"
        )
    atoms = tuple(replace(a, denominator=str(a.symbol) in nonzero) for a in atoms)
    return atoms, expression


def read(context):
    parts, formula, second = read_parts(context)
    second = (
        second.replace(r"\left", "")
        .replace(r"\right", "")
        .replace(r"\;", "")
        .replace(r"\,", "")
    )
    # The source has an orphan multiplication mark after the closing interval bracket.
    second = re.sub(r"(?<=[\])])\s*\\cdot\s*$", "", second)
    interval, bounds = read_interval(second)
    return parts, formula, interval, bounds
