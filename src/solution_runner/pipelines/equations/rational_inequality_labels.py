"""Small exact surd labels with radical bars and stacked fractions in source fonts."""

import xml.etree.ElementTree as ET

import sympy as sp

from ..probability.common import UnsupportedCondition

NS = "http://www.w3.org/2000/svg"


def element(root, tag, **attrs):
    return ET.SubElement(
        root,
        "{" + NS + "}" + tag,
        {key.replace("_", "-"): str(value) for key, value in attrs.items()},
    )


def pieces(value):
    result = []
    for term in sp.Add.make_args(sp.expand(value)):
        coefficient, root = term.as_coeff_Mul()
        if coefficient.is_Integer is not True:
            raise UnsupportedCondition(
                "the displayed numerator needs integer coefficients"
            )
        if root == 1:
            result.append((int(coefficient), None))
        elif (
            root.is_Pow
            and root.exp == sp.Rational(1, 2)
            and root.base.is_Integer
            and root.base > 0
        ):
            result.append((int(coefficient), int(root.base)))
        else:
            raise UnsupportedCondition(
                "the displayed scalar must be a bounded sum of square roots"
            )
    return result


def width(parts, size):
    total = 0
    digit = size / 2
    for index, (coefficient, radicand) in enumerate(parts):
        if index or coefficient < 0:
            total += digit
        if radicand is None or abs(coefficient) != 1:
            total += len(str(abs(coefficient))) * digit
        if radicand is not None:
            total += size * 2 / 3 + len(str(radicand)) * digit
    return total


def text(root, value, x, y, size):
    element(
        root,
        "text",
        x=x,
        y=y,
        font_family="Times New Roman,serif",
        font_size=size,
        fill="#000000",
    ).text = value


def draw(root, parts, x, baseline, size):
    digit = size / 2
    for index, (coefficient, radicand) in enumerate(parts):
        if index or coefficient < 0:
            text(root, "−" if coefficient < 0 else "+", x, baseline, size)
            x += digit
        if radicand is None or abs(coefficient) != 1:
            number = str(abs(coefficient))
            text(root, number, x, baseline, size)
            x += len(number) * digit
        if radicand is not None:
            lead, span, high = size * 2 / 3, len(str(radicand)) * digit, size * 0.9
            element(
                root,
                "path",
                data_radicand=radicand,
                d=f"M{x} {baseline - size * 0.35} l{size / 7} {-size * 0.1} l{size / 5} {size * 0.4} L{x + lead} {baseline - high} H{x + lead + span}",
                fill="none",
                stroke="#000000",
                stroke_width=0.65,
            )
            text(root, str(radicand), x + lead, baseline, size)
            x += lead + span


def label(root, value, x, y):
    numerator, denominator = sp.fraction(sp.radsimp(sp.together(value)))
    if denominator.is_Integer is not True or denominator <= 0:
        raise UnsupportedCondition(
            "the exact label must have a positive integer denominator"
        )
    parts = pieces(numerator)
    size = 14 if denominator == 1 else 12
    length = width(parts, size)
    if denominator == 1:
        draw(root, parts, x - length / 2, y + 19, size)
        return
    draw(root, parts, x - length / 2, y + 14, size)
    span = max(length, len(str(denominator)) * size / 2) + 3
    element(
        root,
        "line",
        x1=x - span / 2,
        x2=x + span / 2,
        y1=y + 17,
        y2=y + 17,
        stroke="#000000",
        stroke_width=0.6,
    )
    text(root, str(denominator), x - len(str(denominator)) * size / 4, y + 28, size)
