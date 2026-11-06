"""Keep direct positive multiplication and the two parent substitution orders."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_proof import power
from .rational_inequality import set_latex
from .rational_inequality_algebraic_methods import real_factor
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION

METHODS = (
    "positive_multiply",
    "reciprocal_substitution",
    "offset_quadratic",
    "reciprocal_roots",
)


def expression(value, name):
    replacement = name if name in ("t", "y", "z") else r"\left(" + name + r"\right)"
    return sp.latex(value).replace("x", replacement)


def expanded(a, name, *, reciprocal=False, omit_constant=False):
    values = []
    for degree, coefficient in sorted(a.coefficients, reverse=True):
        if degree == 0 and omit_constant:
            continue
        c = abs(coefficient)
        term = sp.latex(c)
        if degree:
            if reciprocal and degree < 0:
                term = r"\frac{" + term + "}{" + name + "}"
            else:
                term = (term + r"\cdot " if c != 1 else "") + (
                    name if degree == 1 else "(" + name + ")^{" + str(degree) + "}"
                )
        values.append(("-" if coefficient < 0 else "+", term))
    return "".join(
        (sign if i or sign == "-" else "") + t for i, (sign, t) in enumerate(values)
    )


def membership(name, solution, *, endpoint=None):
    if isinstance(solution, sp.Interval):
        fmt = endpoint or sp.latex
        lo = "<" if solution.left_open else r"\le "
        hi = "<" if solution.right_open else r"\le "
        if solution.start == -sp.oo:
            return name + hi + fmt(solution.end)
        if solution.end == sp.oo:
            return fmt(solution.start) + lo + name
        return fmt(solution.start) + lo + name + hi + fmt(solution.end)
    return name + r"\in " + set_latex(solution, endpoint=endpoint)


def normalized(a, name):
    p = a.stage.original
    content = polynomial(p).content()
    if content == 1:
        return "", p
    factor = 1 / content if content < 1 else content
    operation = "Умножим" if content < 1 else "Разделим"
    html = (
        "<p>"
        + operation
        + " обе части на положительное число "
        + inline(sp.latex(factor))
        + "; знак неравенства сохраняется:</p>"
    )
    value = sp.expand(p / content)
    return html + line(expression(value, name) + RELATION[a.operator] + "0"), value


def validate_method(a, method):
    if method not in METHODS:
        raise UnsupportedCondition("a reviewed quadratic proof method is required")
    if polynomial(a.stage.original).LC() <= 0:
        raise UnsupportedCondition(
            "these parent methods require a positive leading coefficient"
        )
    reciprocal = method in ("positive_multiply", "reciprocal_substitution")
    if a.multiply_degree != int(reciprocal) or any(
        k not in ((-1, 0, 1) if reciprocal else (0, 1, 2)) for k, _ in a.coefficients
    ):
        raise UnsupportedCondition(
            "the positive-power degrees must match the parent method"
        )
    if len(a.stage.zeros) not in (1, 2) or any(
        r.is_positive is not True for r in a.stage.zeros
    ):
        raise UnsupportedCondition(
            "this parent factorization needs positive real roots"
        )
    if method == "reciprocal_roots" and any(
        v.is_Rational is not True for _, v, _ in a.back
    ):
        raise UnsupportedCondition(
            "the parent root bounds must be exact powers of the base"
        )


def factor_step(a, value, name):
    factored = real_factor(value, a.stage.zeros)
    if len(a.stage.zeros) == 1:
        factored = sp.Mul(*factored.args)
    return line(expression(factored, name) + RELATION[a.operator] + "0")


def substitution(a, method, name):
    actual = power(a.base, a.exponent)
    html = ""
    if method == "offset_quadratic":
        html += "<p>Упростим степени, раскрывая постоянные сдвиги в показателях:</p>"
        html += line(expanded(a, actual) + RELATION[a.operator] + "0")
        steps, value = normalized(a, actual)
        html += steps
    else:
        value = a.stage.original
    html += "<p>Пусть " + inline(name + "=" + actual + ">0") + ".</p>"
    if method == "reciprocal_substitution":
        html += line(
            expanded(a, name, reciprocal=True, omit_constant=True)
            + RELATION[a.operator]
            + sp.latex(-a.constant)
        )
        html += (
            "<p>Умножим обе части на положительное "
            + inline(name)
            + ", не меняя знака неравенства:</p>"
        )
    html += line(expression(value, name) + RELATION[a.operator] + "0")
    if method == "reciprocal_substitution":
        steps, value = normalized(a, name)
        html += steps
    html += factor_step(a, value, name)
    html += line(membership(name, a.positive_solution))
    return html


def direct(a, method, actual):
    html = "<p>Последовательно получаем:</p>"
    html += line(
        expanded(
            a, actual, reciprocal=True, omit_constant=method == "positive_multiply"
        )
        + RELATION[a.operator]
        + (sp.latex(-a.constant) if method == "positive_multiply" else "0")
    )
    if method == "positive_multiply":
        html += (
            "<p>При любом действительном x выполняется "
            + inline(actual + ">0")
            + ". Поэтому умножим обе части на эту степень, не меняя знака неравенства:</p>"
        )
        html += line(expression(a.stage.original, actual) + RELATION[a.operator] + "0")
    steps, value = normalized(a, actual)
    html += steps
    if method == "reciprocal_roots":
        # The parent groups the monic coefficients as the sum and product of roots.
        roots = [power(a.base, v) for _, v, _ in a.back]
        if len(roots) == 2:
            leading = polynomial(value).LC()
            if leading != 1:
                html += (
                    "<p>Разделим на положительный старший коэффициент "
                    + inline(sp.latex(leading))
                    + ":</p>"
                )
            html += line(
                "("
                + actual
                + ")^2-("
                + roots[0]
                + "+"
                + roots[1]
                + r")\cdot "
                + actual
                + "+"
                + roots[0]
                + r"\cdot "
                + roots[1]
                + RELATION[a.operator]
                + "0"
            )
            value = sp.expand(value / leading)
    html += factor_step(a, value, actual)
    if len(a.stage.zeros) == 1 and a.operator == ">" and polynomial(value).LC() > 0:
        html += line(actual + r"\ne " + sp.latex(a.stage.zeros[0]))
    return html


def render(a, method):
    validate_method(a, method)
    actual = power(a.base, a.exponent)
    html = line(a.formula)
    if method in ("reciprocal_substitution", "offset_quadratic"):
        html += substitution(
            a, method, "y" if method == "reciprocal_substitution" else "t"
        )
        html += "<p>Возвращаясь к исходной переменной, получаем:</p>"
    else:
        html += direct(a, method, actual)
    root_labels = (
        {t: power(a.base, v) for t, v, _ in a.back}
        if method == "reciprocal_roots"
        else {}
    )
    if not (
        method == "positive_multiply" and len(a.stage.zeros) == 1 and a.operator == ">"
    ):
        html += line(
            membership(
                actual,
                a.positive_solution,
                endpoint=lambda r: root_labels.get(r, sp.latex(r)),
            )
        )
    html += (
        "<p>Основание "
        + inline(sp.latex(a.base) + ">1")
        + ", поэтому показательная функция возрастает.</p>"
    )
    if a.exponent != X:
        exponent_solution = sp.imageset(sp.Lambda(X, a.exponent), a.solution)
        html += line(membership(sp.latex(a.exponent), exponent_solution))
    return html + line(r"x\in " + a.answer)
