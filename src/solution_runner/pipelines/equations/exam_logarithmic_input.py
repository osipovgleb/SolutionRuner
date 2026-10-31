"""Read closed numeric bases, polynomial arguments and a polynomial of logarithms."""

import re
from dataclasses import dataclass

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


def operand(text, index):
    if text[index : index + 1] == "(":
        return balanced(text, index, "(", ")")
    match = re.match(r"x(?:\^\{[1-6]\}|\^[1-6])?", text[index:])
    if not match:
        raise UnsupportedCondition(
            "a complete polynomial logarithm argument is required"
        )
    return match.group(), index + match.end()


def logarithm(text, index, symbol):
    index += 5
    if text[index : index + 1] == "{":
        raw, index = balanced(text, index)
    elif text[index : index + 1] in "23456789" and index < len(text):
        raw, index = text[index], index + 1
    else:
        raise UnsupportedCondition("one unambiguous numeric logarithm base is required")
    base = ScalarParser(raw).parse()
    if base.free_symbols or base.is_positive is not True or base == 1:
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
    return Atom(base, polynomial(raw, X), root, symbol), power, index


def read_equation(formula):
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
        atom, power, end = logarithm(text, start, SYMBOLS[len(atoms)])
        atoms.append(atom)
        text = (
            text[:start] + str(atom.symbol) + ("^2" if power == 2 else "") + text[end:]
        )
    values = []
    for side in text.split("="):
        parser = LaurentParser(side)
        value = symbolic(parser.parse())
        if (
            parser.nonzero
            or value.free_symbols - set(SYMBOLS)
            or not value.is_polynomial(*SYMBOLS)
        ):
            raise UnsupportedCondition(
                "the whole equation must be a polynomial of its logarithms without poles"
            )
        values.append(value)
    expression = sp.expand(values[0] - values[1])
    if not atoms or sp.Poly(expression, *SYMBOLS).total_degree() > 2:
        raise UnsupportedCondition(
            "a nonempty linear or quadratic logarithm equation is required"
        )
    return tuple(atoms), expression


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
