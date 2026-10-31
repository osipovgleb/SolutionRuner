"""Keep the two-square method when a reviewed fraction has original ratio poles."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def compile_pair(values, atoms, denominators):
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_poles import compile_atoms
    from .exam_trigonometric_square_difference import SquareDifference

    numerator, _ = sp.fraction(values[0] - values[1])
    symbols = tuple(atoms)
    if not symbols or not numerator.is_polynomial(*symbols):
        return None
    terms = sp.Poly(numerator, *symbols).terms()
    if len(terms) != 2 or any(
        sum(powers) != 2 or powers.count(2) != 1 for powers, _ in terms
    ):
        return None
    pairs = [(symbols[powers.index(2)], coefficient) for powers, coefficient in terms]
    positive = [(s, c) for s, c in pairs if c.is_positive is True]
    negative = [(s, -c) for s, c in pairs if c.is_negative is True]
    if len(positive) != 1 or len(negative) != 1:
        return None
    selected = [*positive, *negative]
    if any(
        atoms[s].function not in ("sin", "cos") or abs(atoms[s].coefficient) != 1
        for s, _ in selected
    ):
        return None
    originals = [d for d in denominators if d.free_symbols]
    if len(originals) != 1:
        return None
    compiled, intrinsic = compile_atoms(atoms)
    poles = set(intrinsic)
    for d in originals:
        pole = sp.fraction(sp.cancel(d.xreplace(compiled)))[0]
        if not pole.is_polynomial(S, C) or sp.Poly(pole, S, C).total_degree() > 2:
            return None
        poles.add(pole)
    expressions = [sp.sqrt(c) * compiled[s] for s, c in selected]
    if any(
        not e.is_polynomial(S, C) or sp.Poly(e, S, C).total_degree() > 1
        for e in expressions
    ):
        return None
    first, second = expressions
    if sp.expand(first - second) == 0 or sp.expand(first + second) == 0:
        return None
    text = lambda s, c: (
        (sp.latex(sp.sqrt(c)) + r"\," if c != 1 else "")
        + atoms[s].text.replace(r"\alpha", "x")
    )
    data = SquareDifference(
        *(text(s, c) for s, c in selected),
        sp.expand(first - second),
        sp.expand(first + second),
        sp.S.One,
        general=True,
    )
    raw = sp.expand(first * first - second * second)
    return Equation(
        raw,
        (),
        sp.S.One,
        tuple(sorted(poles, key=str)),
        square_difference=data,
        factored_source=raw,
    )


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    data = a.square_difference
    html = "<p>Сохраним область определения исходной дроби:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(a.original)
    html += "<p>При этих ограничениях числитель должен равняться нулю. Квадраты двух чисел равны, когда сами числа равны или противоположны:</p>"
    html += line(
        r"\left(" + data.first + r"\right)^2=\left(" + data.second + r"\right)^2"
    )
    html += line(
        data.first
        + "="
        + data.second
        + r"\quad\text{или}\quad "
        + data.first
        + "=-("
        + data.second
        + ")"
    )
    html += "<p>Применим формулу разности аргументов:</p>"
    html += line(data.first + "=" + formula((data.difference + data.total) / 2))
    html += line(data.second + "=" + formula((data.total - data.difference) / 2))
    for branch in a.branches:
        html += polynomial(branch, allowed_residues=branch.residues)
    return "<p>Решим уравнение, сравнивая два квадрата:</p>", html
