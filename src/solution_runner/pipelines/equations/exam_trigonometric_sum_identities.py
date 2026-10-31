"""Retain a constant sum factor and an auxiliary angle before sum-to-product."""

import re
from itertools import combinations

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import S
from .exam_trigonometric_sum_product import SumProduct, X, equation


def style(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ").replace("\xad", "").lower()
    if "вспомогательн" in text and "разности косинусов" in text:
        return "auxiliary_cosine"
    for node in soup.select("[data-inline-latex]"):
        formula = "".join(node["data-inline-latex"].split())
        for match in re.finditer(r"\\sin\([^()]*x[^()]*\)\(([^()]*)\)=0", formula):
            if "x" not in match[1] and re.search(r"\\(?:sin|cos)", match[1]):
                return "constant_sum"
    return None


def literal(formula):
    from .exam_trigonometric_methods import constant_angles, parse_equation

    values, atoms, denominators = parse_equation(formula)
    values, atoms, denominators, _ = constant_angles(values, atoms, denominators)
    if (
        any(d.free_symbols for d in denominators)
        or not atoms
        or any(a.function not in ("sin", "cos") for a in atoms.values())
    ):
        raise UnsupportedCondition(
            "the sum identity requires denominator-free sine and cosine"
        )
    functions = {
        symbol: (sp.sin if a.function == "sin" else sp.cos)(
            a.coefficient * X + a.shift * sp.pi, evaluate=False
        )
        for symbol, a in atoms.items()
    }
    return values[0] - values[1], atoms, functions


def compile_identity(formula, method):
    polynomial, atoms, functions = literal(formula)
    if method == "constant_sum":
        return constant_sum(polynomial, atoms, functions)
    if method == "auxiliary_cosine":
        return auxiliary(polynomial.xreplace(functions))
    raise UnsupportedCondition("unknown reviewed sum identity")


def constant_sum(polynomial, atoms, functions):
    if (
        len(atoms) != 3
        or not polynomial.is_polynomial(*atoms)
        or sp.Poly(polynomial, *atoms).total_degree() != 1
        or polynomial.subs(dict.fromkeys(atoms, 0)) != 0
    ):
        raise UnsupportedCondition("three linear sine terms are required")
    if (
        any(a.function != "sin" for a in atoms.values())
        or len({a.coefficient for a in atoms.values()}) != 1
    ):
        raise UnsupportedCondition("the sine sum requires one common angle multiplier")
    for first, second in combinations(atoms, 2):
        third = next(s for s in atoms if s not in (first, second))
        weight = polynomial.coeff(first)
        if (
            not weight
            or polynomial.coeff(second) != weight
            or polynomial.coeff(third) != -weight
        ):
            continue
        left, right = functions[first].args[0], functions[second].args[0]
        average, difference = (
            sp.expand((left + right) / 2),
            sp.expand((left - right) / 2),
        )
        if (
            difference.has(X)
            or sp.trigsimp(sp.sin(average) - functions[third], method="fu") != 0
        ):
            continue
        coefficient = weight * (2 * sp.cos(difference, evaluate=False) - 1)
        if compare(sp.simplify(coefficient), sp.S.Zero) == 0:
            raise UnsupportedCondition("a zero constant factor would give an identity")
        product = sp.Mul(coefficient, sp.sin(average, evaluate=False), evaluate=False)
        identities = (
            (
                functions[first] + functions[second],
                2
                * sp.sin(average, evaluate=False)
                * sp.cos(difference, evaluate=False),
            ),
            (coefficient, sp.simplify(coefficient)),
        )
        raw = polynomial.xreplace(functions)
        return equation(
            SumProduct(
                raw, raw, product, False, kind="constant_sum", identities=identities
            )
        )
    raise UnsupportedCondition("the third sine must equal the mean-angle sine")


def auxiliary(raw):
    sine, cosine = sp.sin(X), sp.cos(X)
    raw = sp.expand(raw)
    a, b = raw.coeff(sine), raw.coeff(cosine)
    rest = sp.expand(raw - a * sine - b * cosine)
    if not a or not b or a.free_symbols or b.free_symbols:
        raise UnsupportedCondition(
            "the auxiliary angle needs both unit-angle functions"
        )
    functions = rest.atoms(sp.sin, sp.cos)
    if len(functions) != 1:
        raise UnsupportedCondition("one second cosine is required")
    other = next(iter(functions))
    multiple = sp.cancel(other.args[0] / X)
    amplitude = sp.sqrt(sp.simplify(a * a + b * b))
    if (
        other.func != sp.cos
        or multiple.is_Integer is not True
        or not 2 <= multiple <= 12
        or sp.simplify(rest / amplitude) not in (other, -other)
    ):
        raise UnsupportedCondition(
            "two cosines of equal amplitude and bounded integer angles are required"
        )
    phases = [
        sp.Rational(i, 12)
        for i in range(-11, 13)
        if sp.simplify(amplitude * sp.cos(i * sp.pi / 12) - b) == 0
        and sp.simplify(-amplitude * sp.sin(i * sp.pi / 12) - a) == 0
    ]
    if len(phases) != 1:
        raise UnsupportedCondition("one reviewed exact auxiliary angle is required")
    phase = phases[0] * sp.pi
    shifted = sp.cos(X + phase, evaluate=False)
    root = shifted + rest / amplitude
    average = (X + phase + other.args[0]) / 2
    difference = (other.args[0] - X - phase) / 2
    product = (
        sp.Mul(
            2,
            sp.sin(average, evaluate=False),
            sp.sin(difference, evaluate=False),
            evaluate=False,
        )
        if sp.simplify(rest / amplitude) == -other
        else sp.Mul(
            2,
            sp.cos(average, evaluate=False),
            sp.cos(difference, evaluate=False),
            evaluate=False,
        )
    )
    identity = ((a * sine + b * cosine) / amplitude, shifted)
    return equation(
        SumProduct(
            raw,
            root,
            product,
            False,
            normalizer=amplitude,
            kind="auxiliary_cosine",
            identities=(identity,),
        )
    )


def proof(a):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import series_lines

    data = a.sum_product
    html = line(a.original)
    html += (
        "<p>Применим формулу суммы синусов:</p>"
        if data.kind == "constant_sum"
        else "<p>Введём вспомогательный угол с помощью формулы косинуса суммы:</p>"
    )
    for left, right in data.identities[:1]:
        html += line(sp.latex(left) + "=" + sp.latex(right))
    if data.kind == "auxiliary_cosine":
        html += line(sp.latex(data.cleared / data.normalizer) + "=0")
        html += line(sp.latex(data.root) + "=0")
        html += "<p>Применим формулу разности или суммы косинусов:</p>"
    html += line(sp.latex(data.product) + "=0")
    if data.kind == "constant_sum":
        coefficient, value = data.identities[1]
        html += (
            "<p>Постоянный множитель ненулевой, поэтому на него можно разделить:</p>"
        )
        html += line(sp.latex(coefficient) + "=" + sp.latex(value) + r"\ne0")
    for branch in a.branches:
        function = sp.sin if branch.variable == S else sp.cos
        html += line(
            sp.latex(
                function(
                    branch.angle_scale * a.scale * X + branch.angle_shift * sp.pi,
                    evaluate=False,
                )
            )
            + "=0"
        )
        series = tuple(
            (
                (q - branch.angle_shift) / (branch.angle_scale * a.scale),
                period / (branch.angle_scale * a.scale),
            )
            for q, period in level_series(branch.variable, sp.S.Zero)
        )
        for text in series_lines(series):
            html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Преобразуем сумму тригонометрических функций:</p>", html
