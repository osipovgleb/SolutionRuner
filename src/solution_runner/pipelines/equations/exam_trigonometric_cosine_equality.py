"""Fold a unit sine/cosine combination and solve the two affine cosine arguments."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from sympy.simplify.fu import TR8

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
    ) or direct_parent(html)


def direct_parent(html):
    from .exam_trigonometric_power_equality import parent_equations

    soup = BeautifulSoup(html, "html.parser")
    forms = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    compact = " ".join("".join(f.split()) for f in forms)
    relations = re.findall(r"(?<![A-Za-z])(-?\d*)x=(-?\d*)x\+2\\pi[knm]", compact)
    if not any(b.startswith("-") for _, b in relations) or not any(
        not b.startswith("-") for _, b in relations
    ):
        return False
    if re.search(r"(?<![A-Za-z])[tyuzv]=", compact):
        raise UnsupportedCondition(
            "the direct cosine argument method must not omit a substitution"
        )
    for equation in parent_equations(forms):
        if equation.count(r"\cos") < 2:
            continue
        try:
            polynomial, atoms, _ = literal(equation)
        except UnsupportedCondition:
            continue
        symbols = tuple(atoms)
        if len(symbols) != 2 or any(a.function != "cos" for a in atoms.values()):
            continue
        weight = polynomial.coeff(symbols[0])
        if (
            weight != 0
            and not weight.free_symbols
            and sp.expand(polynomial - weight * (symbols[0] - symbols[1])) == 0
        ):
            return True
    return False


def cosine_phase(a, b):
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
    return phases[0]


def compile_direct(formula):
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_sine_pair import ArgumentPair, argument_series

    if re.search(r"\\(?:alpha|beta|gamma)", formula):
        raise UnsupportedCondition("the original cosine equality must use x")
    polynomial, atoms, functions = literal(formula)
    if any(
        a.coefficient.is_Rational is not True
        or a.coefficient.q not in (1, 2)
        or abs(a.coefficient) > 12
        or a.shift.is_Rational is not True
        or a.shift.q > 12
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "bounded original integer or half-integer angles are required"
        )
    raw = polynomial.xreplace(functions)
    canonical = raw.xreplace({f: f.func(*f.args) for f in raw.atoms(sp.sin, sp.cos)})
    reduced = sp.expand(TR8(canonical))
    terms = tuple(sorted(reduced.atoms(sp.sin, sp.cos), key=sp.default_sort_key))
    if len(terms) != 2:
        raise UnsupportedCondition(
            "two complete sine/cosine terms are required after identities"
        )
    weights = {f: reduced.coeff(f) for f in terms}
    if (
        any(
            w.free_symbols or w.is_real is not True or w == 0 or abs(w) > 1000
            for w in weights.values()
        )
        or sp.expand(reduced - sum(weights[f] * f for f in terms)) != 0
    ):
        raise UnsupportedCondition(
            "a bounded homogeneous pair of trig terms is required"
        )
    if any(
        (f.args[0] / X).is_Integer is not True or not 0 < abs(f.args[0] / X) <= 12
        for f in terms
    ):
        raise UnsupportedCondition(
            "bounded unshifted integer angles are required after identities"
        )
    if sp.simplify(abs(weights[terms[0]]) - abs(weights[terms[1]])) == 0:
        first = next((f for f in terms if weights[f].is_positive), terms[0])
        second = next(f for f in terms if f != first)
        weight = weights[first]
        left = first.args[0] if first.func == sp.cos else sp.pi / 2 - first.args[0]
        right = second.args[0] if second.func == sp.cos else sp.pi / 2 - second.args[0]
        if sp.simplify(weights[second] - weight) == 0:
            right += sp.pi
        elif sp.simplify(weights[second] + weight) != 0:
            raise UnsupportedCondition("the two complete amplitudes must agree exactly")
    else:
        if len({f.args[0] for f in terms}) != 1:
            raise UnsupportedCondition(
                "unequal amplitudes require the same original angle"
            )
        angle = terms[0].args[0]
        a, b = reduced.coeff(sp.cos(angle)), reduced.coeff(sp.sin(angle))
        weight = sp.sqrt(a * a + b * b)
        left, right = angle + cosine_phase(a / weight, b / weight) * sp.pi, sp.pi / 2
    transformed = weight * (
        sp.cos(left, evaluate=False) - sp.cos(right, evaluate=False)
    )
    scale = 2 if any(a.coefficient.q == 2 for a in atoms.values()) else 1
    if not equivalent(
        raw.subs(X, scale * X), reduced.subs(X, scale * X)
    ) or not equivalent(reduced, transformed):
        raise UnsupportedCondition(
            "the complete cosine normalization requires an exact identity certificate"
        )
    data = ArgumentPair(left, right, cosine=True, reduced=reduced, weight=weight)
    argument_series(data)
    return Equation(raw, (), sp.S.One, argument_pair=data)


def compile_equality(formula, *, parent_html=""):
    from .exam_trigonometric_methods import Equation

    if direct_parent(parent_html):
        return compile_direct(formula)
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
    phase = cosine_phase(a, b)
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
