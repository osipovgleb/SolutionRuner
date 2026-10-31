"""Read bounded sums of exponential terms and exact closed numeric coefficients."""

import re

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .logarithm_parser import LogarithmParser
from .power_arithmetic import balanced, clean


def scalar(text):
    value = LogarithmParser(text).parse().value
    if value.is_Rational is not True:
        raise UnsupportedCondition(
            "closed exponential coefficients must be exact rationals"
        )
    return value


def read(formula):
    from .exam_exponential import polynomial

    text = clean(formula)
    if text.count("=") != 1:
        raise UnsupportedCondition(
            "exactly one complete exponential equation is required"
        )
    text, right = text.split("=")
    constant = -scalar(right)
    pieces = []
    start = 0
    depth = 0
    for i, ch in enumerate(text):
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        elif ch in "+-" and depth == 0 and i > start:
            pieces.append(text[start:i])
            start = i
    pieces.append(text[start:])
    powers = []
    for piece in pieces:
        sign = -1 if piece.startswith("-") else 1
        piece = piece.lstrip("+-")
        depth = 0
        power = None
        for i, ch in enumerate(piece):
            if ch in "{(":
                depth += 1
            elif ch in "})":
                depth -= 1
            elif depth == 0 and ch.isdigit():
                match = re.match(r"\d+\^", piece[i:])
                if match and (i == 0 or not piece[i - 1].isdigit()):
                    power = (i, match)
                    break
        if power is None:
            constant += sign * scalar(piece)
            continue
        i, match = power
        coefficient = piece[:i].removesuffix(r"\cdot")
        coefficient = sign * (scalar(coefficient) if coefficient else sp.Integer(1))
        base = sp.Integer(match.group()[:-1])
        raw, end = balanced(piece, i + match.end())
        if end != len(piece) or not 1 < base <= 1000:
            raise UnsupportedCondition(
                "each exponential term needs one bounded positive base and no trailing factors"
            )
        exponent = polynomial(raw)
        if not exponent.free_symbols:
            value = coefficient * base**exponent
            if value.is_Rational is not True:
                raise UnsupportedCondition("a constant power must be rational")
            constant += value
        else:
            powers.append((coefficient, base, exponent))
    if not 1 <= len(powers) <= 4:
        raise UnsupportedCondition("one to four bounded exponential terms are required")
    return powers, constant
