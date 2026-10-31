"""Fold a unit sine/cosine combination and solve the two affine cosine arguments."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_angle_domain import equivalent
from .exam_trigonometric_compile import C
from .exam_trigonometric_sum_identities import X, literal


def reviewed(html):
    formulas = "".join(
        "".join(n["data-inline-latex"].split())
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )
    return bool(
        re.search(r"\\cos\d+x=-\\cos\(x[+-]", formulas) and r"\pi\pm" in formulas
    )


def compile_equality(formula):
    from .exam_trigonometric_methods import Equation

    polynomial, _, functions = literal(formula)
    raw = sp.expand(polynomial.xreplace(functions))
    higher = [
        f
        for f in raw.atoms(sp.sin, sp.cos)
        if f.func == sp.cos
        and sp.cancel(f.args[0] / X).is_Integer is True
        and 2 <= sp.cancel(f.args[0] / X) <= 12
    ]
    if len(higher) != 1:
        raise UnsupportedCondition("one bounded unshifted higher cosine is required")
    high = higher[0]
    multiple = sp.cancel(high.args[0] / X)
    weight = raw.coeff(high)
    a, b = (
        sp.simplify(raw.coeff(sp.cos(X)) / weight),
        sp.simplify(raw.coeff(sp.sin(X)) / weight),
    )
    if (
        weight == 0
        or sp.simplify(a * a + b * b - 1) != 0
        or sp.expand(raw - weight * (high + a * sp.cos(X) + b * sp.sin(X))) != 0
    ):
        raise UnsupportedCondition(
            "the remaining unit-angle combination must have exactly the same amplitude"
        )
    phases = [
        sp.Rational(k, 12)
        for k in range(-11, 13)
        if sp.simplify(sp.cos(sp.pi * k / 12) - a) == 0
        and sp.simplify(-sp.sin(sp.pi * k / 12) - b) == 0
    ]
    if len(phases) != 1:
        raise UnsupportedCondition(
            "the cosine addition angle must have a reviewed exact phase"
        )
    phase = phases[0]
    if not equivalent(raw / weight, high + sp.cos(X + phase * sp.pi)):
        raise UnsupportedCondition(
            "the cosine addition formula requires an exact unit-circle certificate"
        )
    return Equation(
        raw, (), sp.S.One, cosine_equality=(multiple, phase, raw, weight, a, b)
    )


def series(data):
    multiple, phase, *_ = data
    return (
        (sp.cancel((1 + phase) / (multiple - 1)), sp.cancel(2 / (multiple - 1))),
        (sp.cancel((1 - phase) / (multiple + 1)), sp.cancel(2 / (multiple + 1))),
    )


def branches(data):
    from .exam_trigonometric import Branch

    result = []
    for (q, p), multiple in zip(series(data), (data[0] - 1, data[0] + 1)):
        residues = tuple(sorted({(q + k * p) % 2 for k in range(int(multiple))}))
        shift = -data[1] / 2 if multiple == data[0] - 1 else data[1] / 2
        result.append(
            Branch(
                C,
                C,
                (sp.S.Zero,),
                (sp.S.Zero,),
                residues,
                angle_scale=multiple / 2,
                angle_shift=shift,
            )
        )
    return tuple(result)


def proof(a):
    from .exam_trigonometric_proof import families

    multiple, phase, _raw, _weight, alpha, beta = a.cosine_equality
    html = line(a.original)
    html += "<p>Применим формулу косинуса суммы к линейной комбинации синуса и косинуса:</p>"
    html += line(
        sp.latex(alpha * sp.cos(X) + beta * sp.sin(X))
        + "="
        + sp.latex(sp.cos(X + phase * sp.pi))
    )
    html += line(
        sp.latex(sp.cos(multiple * X)) + "=-" + sp.latex(sp.cos(X + phase * sp.pi))
    )
    html += "<p>Косинусы противоположны, когда их аргументы связаны следующими двумя равенствами:</p>"
    html += line(
        sp.latex(multiple * X)
        + r"=\pi\pm\left("
        + sp.latex(X + phase * sp.pi)
        + r"\right)+2\pi k"
    )
    for sign in (1, -1):
        html += line(
            sp.latex((multiple - sign) * X)
            + "="
            + sp.latex((1 + sign * phase) * sp.pi)
            + r"+2\pi k"
        )
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Сведём уравнение к равенству косинусов с разными аргументами:</p>", html
