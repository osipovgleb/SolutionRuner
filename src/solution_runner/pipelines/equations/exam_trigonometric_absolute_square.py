"""Square an absolute equality only together with its original sign condition."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .power_arithmetic import clean


def reviewed(html):
    text = (
        BeautifulSoup(html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
        .replace("ё", "е")
    )
    return "возведем обе части уравнения в квадрат" in text and "|" in html


def compile_square(formula, preferred, scale):
    from .exam_trigonometric_methods import (
        Equation,
        compile_reviewed,
        parse_equation,
        shifted_atom,
    )
    from .trig_angles import C as NC
    from .trig_angles import S as NS

    match = re.fullmatch(r"\|([^|]+)\|=([^|]+)", clean(formula))
    if not match or preferred != S or scale != 2:
        raise UnsupportedCondition(
            "one reviewed absolute equality with a sine double-angle sign is required"
        )
    left, right = match.groups()
    compiled = compile_reviewed("(" + left + ")^2=(" + right + ")^2", preferred, scale)
    values, atoms, denominators = parse_equation(left + "=" + right)
    if (
        compiled.scale != 1
        or denominators
        or any(a.function not in ("sin", "cos") for a in atoms.values())
    ):
        raise UnsupportedCondition(
            "the squared absolute identity requires denominator-free unit base angles"
        )
    substitutions = {
        s: shifted_atom(a).xreplace({NS: S, NC: C}) for s, a in atoms.items()
    }
    rhs = sp.expand(values[1].xreplace(substitutions))
    weight = sp.cancel(rhs / (2 * S * C))
    if weight.free_symbols or weight.is_positive is not True:
        raise UnsupportedCondition(
            "the original right side must be a positive multiple of the double-angle sine"
        )
    from .exam_trigonometric_sine_double import project

    polynomial = project(compiled.raw)
    if polynomial is None or sp.degree(polynomial, S) != 2:
        raise UnsupportedCondition(
            "the squared equation requires a nondegenerate quadratic double-angle certificate"
        )
    left, right = (
        re.sub(r"\\(sin|cos|tg|ctg)(?=[A-Za-z0-9])", r"\\\1 ", text)
        for text in (left, right)
    )
    return Equation(
        polynomial,
        (),
        scale,
        domain=S,
        absolute_square=(left, right, sp.expand(polynomial + weight**2 * S * S)),
    )


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_variants import argument

    left, right, left_square = a.absolute_square
    angle = argument(a.scale)
    html = line(a.original)
    html += "<p>Правая часть должна быть неотрицательной. Только вместе с этим условием возведение в квадрат равносильно исходному уравнению:</p>"
    html += line(
        right + r"\ge0\quad\Longleftrightarrow\quad " + formula(S, angle) + r"\ge0"
    )
    html += line("(" + left + ")^2=(" + right + ")^2")
    html += (
        "<p>Раскроем квадрат и применим основное тождество и формулу двойного угла:</p>"
    )
    html += line("(" + left + ")^2=" + formula(left_square, angle))
    html += line(formula(a.raw, angle) + "=0")
    for branch in a.branches:
        html += polynomial(
            branch, angle=angle, root_scale=a.scale, allowed_residues=branch.residues
        )
        for value in branch.candidates:
            if value.is_negative is not True:
                continue
            html += "<p>Отрицательное значение синуса нарушает знак правой части исходного уравнения:</p>"
            html += line(formula(S, angle) + "=" + sp.latex(value) + "<0")
    return "<p>Решим уравнение с модулем, сохраняя условие на знак:</p>", html
