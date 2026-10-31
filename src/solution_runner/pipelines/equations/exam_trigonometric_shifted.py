"""Read an explicitly shifted function argument when the parent keeps that angle."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .power_arithmetic import ScalarParser, balanced
from .trig_angles import PI
from .trig_symbolic_parser import A


def formula(text):
    return (
        "".join(text.split())
        .replace(r"\left", "")
        .replace(r"\right", "")
        .replace("&", "")
    )


def candidates(text):
    for match in re.finditer(r"\\(sin|cos)\(", text):
        argument, end = balanced(text, match.end() - 1, "(", ")")
        if text[end : end + 1] != "=":
            continue
        right = re.split(
            r"\\\\|\\(?:iff|Leftrightarrow|end|quad|implies)",
            text[end + 1 :],
            maxsplit=1,
        )[0].rstrip(".,")
        if "x" in right or re.search(r"\\(?:sin|cos|tg|ctg)", right):
            continue
        try:
            ScalarParser(right).parse()
        except UnsupportedCondition:
            continue
        if "x" not in argument or re.search(
            r"[A-Za-z]", re.sub(r"\\[A-Za-z]+", "", argument).replace("x", "")
        ):
            raise UnsupportedCondition("the shifted parent argument must use x alone")
        value = ScalarParser(
            argument.replace("x", "a").replace(r"\pi", "p"), {"a", "p"}
        ).parse()
        coefficient = value.expand().coeff(A)
        shift = sp.cancel((value - coefficient * A) / PI)
        if shift == 0:
            continue
        if (
            coefficient != 1
            or shift.is_Rational is not True
            or (12 * shift).is_Integer is not True
            or abs(shift) > 2
        ):
            raise UnsupportedCondition(
                "one unit argument with a reviewed pi shift is required"
            )
        yield match[1], argument, shift


def parent_angle(html):
    soup = BeautifulSoup(html, "html.parser")
    found = [
        item
        for node in soup.select("[data-inline-latex]")
        for item in candidates(formula(node["data-inline-latex"]))
    ]
    if not found:
        return html, sp.S.Zero
    if len({(function, shift) for function, _, shift in found}) != 1:
        raise UnsupportedCondition(
            "the parent must use one shifted function as its quadratic variable"
        )
    for node in soup.select("[data-inline-latex]"):
        text = formula(node["data-inline-latex"])
        for _, argument, _ in found:
            text = text.replace("(" + argument + ")", "x")
        node["data-inline-latex"] = text
    return str(soup), found[0][2]


def identity_arguments(a):
    from .exam_trigonometric_methods import parse_equation

    result = {}
    x = sp.Symbol("x", real=True)
    for text, _ in a.identities:
        _, atoms, _ = parse_equation(text + "=0")
        if len(atoms) != 1:
            raise UnsupportedCondition("one typed function identity is required")
        atom = next(iter(atoms.values()))
        argument = sp.expand(
            atom.coefficient * (x + a.translation * sp.pi) + atom.shift * sp.pi
        )
        result[text] = "\\" + atom.function + "(" + sp.latex(argument) + ")"
    return result
