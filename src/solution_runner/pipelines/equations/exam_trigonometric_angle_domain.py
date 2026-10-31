"""Keep base-angle poles and nested root families of bounded angle products."""

from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .trig_angles import C as NC
from .trig_angles import S as NS

X = sp.Symbol("x", real=True)


def fraction_input(values, atoms, denominators, compiled):
    from .exam_trigonometric_methods import shifted_atom

    originals = [d for d in denominators if d.free_symbols]
    if not originals:
        return (values[0] - values[1]).xreplace(compiled), (), None
    numerator, denominator = sp.fraction(values[0] - values[1])
    if len(originals) != 1 or not denominator.free_symbols:
        raise UnsupportedCondition("one original angle-product fraction is required")
    poles = []
    for d in originals:
        if any(abs(atoms[s].coefficient) != 1 for s in d.free_symbols):
            raise UnsupportedCondition(
                "the original angle-product pole must use the base angle"
            )
        pole = sp.expand(
            d.xreplace(
                {
                    s: shifted_atom(atoms[s]).xreplace({NS: S, NC: C})
                    for s in d.free_symbols
                }
            )
        )
        if not pole.is_polynomial(S, C) or sp.Poly(pole, S, C).total_degree() not in (
            1,
            2,
        ):
            raise UnsupportedCondition(
                "the angle-product pole must be linear or quadratic"
            )
        poles.append(pole)
    return numerator.xreplace(compiled), tuple(poles), poles[0]


def addition_identity(raw, factored, factors):
    if any(v != S or p.subs(S, 0) != 0 for v, _, p in factors):
        return ()
    a, b = (scale * X for _, scale, _ in factors)
    coefficient = sp.cancel(factored / (sp.sin(a) * sp.sin(b)))
    if (
        coefficient.free_symbols
        or sp.expand(raw - coefficient * (sp.cos(a) * sp.cos(b) - sp.cos(a + b))) != 0
    ):
        return ()
    return ((sp.cos(a + b), sp.cos(a) * sp.cos(b) - sp.sin(a) * sp.sin(b)),)


def nested(poles, factors):
    scales = sorted(scale for _, scale, _ in factors)
    return (
        len(poles) == 1
        and not sp.cancel(poles[0] / (C + 1)).free_symbols
        and all(v == S and p.subs(S, 0) == 0 for v, _, p in factors)
        and scales[0] < scales[1]
        and scales[1] % scales[0] == 0
        and scales[1] in (2, 4, 8)
    )


def review(compiled, parent_html):
    data = compiled.angle_product
    text = (
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
    )
    requested = "входят в множество" in text and "исключить" in text
    if requested and not data.nested:
        raise UnsupportedCondition(
            "the parent's nested-root note requires its reviewed dyadic lattice and pole"
        )
    note = data.nested and requested
    return replace(compiled, angle_product=replace(data, note=note))


def series(data, residues):
    scale = max(scale for _, scale, _ in data.factors)
    remaining = set(residues)
    if remaining != {sp.Rational(k, scale) for k in range(2 * int(scale))} - {sp.S.One}:
        raise UnsupportedCondition(
            "nested families must cover the complete lattice except the original pole"
        )
    result = []
    step = sp.Rational(1, scale)
    while step < 1:
        result.append((step, 2 * step))
        remaining -= {step + 2 * step * k for k in range(int(1 / step))}
        step *= 2
    if remaining != {sp.S.Zero}:
        raise UnsupportedCondition("the nested families must be disjoint and complete")
    return (*result, (sp.S.Zero, sp.Integer(2)))


def note(a):
    from .exam_trigonometric_proof import pi

    scales = sorted(scale for _, scale, _ in a.angle_product.factors)
    small, large = scales
    html = "<p><b>Примечание.</b> Все корни уравнения с меньшим углом входят в множество корней уравнения с большим углом:</p>"
    html += line(
        r"\sin("
        + str(small)
        + r"x)=0\quad\Longleftrightarrow\quad x="
        + pi(1 / small)
        + r"k,\quad k\in\mathbb Z"
    )
    html += line(
        r"\sin("
        + str(large)
        + r"x)=0\quad\Longleftrightarrow\quad x="
        + pi(1 / large)
        + r"k,\quad k\in\mathbb Z"
    )
    html += (
        "<p>Из общего множества необходимо исключить точки исходного знаменателя:</p>"
        + line(r"x\ne\pi+2\pi k,\quad k\in\mathbb Z")
    )
    return (
        html
        + "<p>Поэтому корни записаны несколькими непересекающимися сериями: ни одна не содержит исключённую точку.</p>"
    )


def equivalent(left, right):
    expression = sp.expand(
        sp.expand_trig(left - right).xreplace({sp.sin(X): S, sp.cos(X): C})
    )
    if expression.free_symbols - {S, C} or not expression.is_polynomial(S, C):
        return False
    return sp.simplify(sp.rem(expression, S * S + C * C - 1, S)) == 0
