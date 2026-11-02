"""Retain reviewed sine/cosine argument equalities and their original identities."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup
from sympy.simplify.fu import TR8, TR9

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_angle_domain import equivalent
from .exam_trigonometric_angle_product import AngleProduct, X, factor_angles
from .exam_trigonometric_sum_identities import literal


@dataclass(frozen=True)
class ArgumentPair:
    left: sp.Expr
    right: sp.Expr
    cosine: bool = False
    reduced: sp.Expr | None = None
    weight: sp.Expr = sp.S.One


def reviewed(html):
    formulas = " ".join(
        "".join(n["data-inline-latex"].split())
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )
    if r"=\pi-(" in formulas and r"+2\pik" in formulas and r"\sin(" in formulas:
        return True
    for m in re.finditer(r"(\d+)x=(\d+)x\+2\\pik", formulas):
        low, high = map(int, m.groups())
        if (
            0 < low < high <= 12
            and high == 2 * low
            and str(low) + r"x=\pi-" + str(high) + r"x+2\pik" in formulas
        ):
            return True
    return False


def compile_pair(formula):
    from .exam_trigonometric_methods import Equation

    polynomial, atoms, functions = literal(formula)
    raw = polynomial.xreplace(functions)
    if (
        len(atoms) == 2
        and all(a.function == "sin" for a in atoms.values())
        and any(a.shift or a.coefficient < 0 for a in atoms.values())
    ):
        return compile_arguments(polynomial, atoms, functions)
    canonical = raw.xreplace({f: f.func(*f.args) for f in raw.atoms(sp.sin, sp.cos)})
    reduced = sp.expand(TR8(canonical))
    sines = tuple(reduced.atoms(sp.sin, sp.cos))
    if len(sines) != 2 or any(
        f.func != sp.sin or sp.cancel(f.args[0] / X).is_Integer is not True
        for f in sines
    ):
        raise UnsupportedCondition(
            "two unshifted sine angles are required after the reviewed identities"
        )
    sines = sorted(sines, key=lambda f: sp.cancel(f.args[0] / X))
    low, high = (sp.cancel(f.args[0] / X) for f in sines)
    if not 0 < low < high <= 12 or high != 2 * low:
        raise UnsupportedCondition(
            "the sine pair must have a bounded double-angle relation"
        )
    weights = tuple(reduced.coeff(f) for f in sines)
    if (
        any(w.free_symbols or w.is_real is not True or w == 0 for w in weights)
        or sp.expand(reduced - sum(w * f for w, f in zip(weights, sines))) != 0
    ):
        raise UnsupportedCondition("a homogeneous linear pair of sines is required")
    equal = sp.simplify(sum(weights)) == 0
    factored = (
        sp.factor(TR9(reduced))
        if equal
        else sp.factor(reduced.subs(sines[1], 2 * sines[0] * sp.cos(low * X)))
    )
    factors = factor_angles(factored)
    if factors is None or not equivalent(raw, factored):
        raise UnsupportedCondition(
            "the sine-pair roots require an exact identity certificate"
        )
    return Equation(
        raw,
        (),
        sp.S.One,
        angle_product=AngleProduct(factored, factors, reduced=reduced, summed=equal),
        sine_pair=(reduced, low, high, weights, equal),
    )


def proof(a):
    from .exam_trigonometric_proof import families, polynomial
    from .exam_trigonometric_variants import argument

    reduced, low, high, _weights, equal = a.sine_pair
    html = line(a.original) + line(sp.latex(reduced) + "=0")
    if equal:
        html += "<p>Сократим одинаковые ненулевые коэффициенты. Используем условие равенства синусов:</p>"
        html += line(sp.latex(sp.sin(low * X)) + "=" + sp.latex(sp.sin(high * X)))
        html += line(
            sp.latex(low * X)
            + "="
            + sp.latex(high * X)
            + r"+2\pi k\quad\text{или}\quad "
            + sp.latex(low * X)
            + r"=\pi-"
            + sp.latex(high * X)
            + r"+2\pi k"
        )
        html += "<p>Решим каждое линейное уравнение относительно x:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    else:
        html += "<p>После подстановки чисел коэффициенты синусов различны. Применим формулу двойного угла и вынесем общий синус, сохраняя его нули:</p>"
        html += line(
            sp.latex(sp.sin(high * X))
            + "="
            + sp.latex(2 * sp.sin(low * X) * sp.cos(low * X))
        )
        html += line(sp.latex(a.angle_product.factored) + "=0")
        for b in a.branches:
            html += polynomial(
                b, angle=argument(b.angle_scale), root_scale=b.angle_scale
            )
    return "<p>Применим формулы приведения и двойного угла:</p>", html


def compile_arguments(polynomial, atoms, functions):
    from .exam_trigonometric_methods import Equation

    symbols = tuple(atoms)
    if len(symbols) != 2 or any(
        a.function != "sin"
        or a.coefficient.is_Integer is not True
        or abs(a.coefficient) > 12
        for a in atoms.values()
    ):
        raise UnsupportedCondition("two bounded affine sine arguments are required")
    first, second = symbols
    weight = polynomial.coeff(first)
    if (
        weight == 0
        or weight.free_symbols
        or sp.expand(polynomial - weight * (first - second)) != 0
    ):
        raise UnsupportedCondition(
            "the two sine coefficients must be nonzero and opposite"
        )
    left, right = functions[first].args[0], functions[second].args[0]
    data = ArgumentPair(left, right)
    argument_series(data)
    raw = polynomial.xreplace(functions)
    product = 2 * weight * sp.cos((left + right) / 2) * sp.sin((left - right) / 2)
    if not equivalent(raw.subs(X, 2 * X), product.subs(X, 2 * X)):
        raise UnsupportedCondition(
            "the affine sine equality requires an exact identity certificate"
        )
    return Equation(raw, (), sp.S.One, argument_pair=data)


def argument_rows(data):
    left, right = data.left, data.right
    result = []
    for expression in (left - right, left + right - (0 if data.cosine else sp.pi)):
        coefficient = sp.expand(expression).coeff(X)
        shift = sp.simplify((expression - coefficient * X) / sp.pi)
        if (
            coefficient.is_Integer is not True
            or abs(coefficient) > 24
            or shift.is_Rational is not True
        ):
            raise UnsupportedCondition(
                "both argument equations must have nonzero bounded slopes"
            )
        if coefficient == 0:
            if not data.cosine:
                raise UnsupportedCondition(
                    "both argument equations must have nonzero bounded slopes"
                )
            if (shift / 2).is_Integer:
                raise UnsupportedCondition(
                    "an argument identity gives infinitely many solutions"
                )
            result.append((expression, None))
            continue
        result.append(
            (expression, (sp.cancel(-shift / coefficient), 2 / abs(coefficient)))
        )
    return tuple(result)


def argument_series(data):
    return tuple(series for _, series in argument_rows(data) if series is not None)


def argument_branches(data):
    from .exam_trigonometric import Branch
    from .exam_trigonometric_compile import S

    result = []
    for expression, series in argument_rows(data):
        if series is None:
            continue
        q, p = series
        coefficient = sp.expand(expression).coeff(X)
        shift = sp.simplify((expression - coefficient * X) / sp.pi)
        residues = tuple(
            sorted({(q + k * p) % 2 for k in range(int(abs(coefficient)))})
        )
        result.append(
            Branch(
                S,
                S,
                (sp.S.Zero,),
                (sp.S.Zero,),
                residues,
                angle_scale=abs(coefficient) / 2,
                angle_shift=sp.sign(coefficient) * shift / 2,
            )
        )
    return tuple(result)


def argument_proof(a):
    from .exam_trigonometric_proof import families

    if a.argument_pair.cosine:
        return cosine_argument_proof(a)
    left, right = a.argument_pair.left, a.argument_pair.right
    html = line(a.original) + line(
        sp.latex(sp.sin(left, evaluate=False))
        + "="
        + sp.latex(sp.sin(right, evaluate=False))
    )
    html += "<p>Синусы равны, когда аргументы отличаются на целое число полных оборотов либо в сумме дают π с точностью до полного оборота:</p>"
    html += line(sp.latex(left) + "=" + sp.latex(right) + r"+2\pi k")
    html += line(sp.latex(left) + r"=\pi-\left(" + sp.latex(right) + r"\right)+2\pi k")
    html += "<p>В каждой ветви решим линейное уравнение. При отрицательном коэффициенте заменим целый параметр на противоположный; сдвиг на целое число периодов также не меняет серию:</p>"
    for expression, text in zip((left - right, left + right - sp.pi), families(a)):
        html += line(sp.latex(sp.expand(expression)) + r"=2\pi k")
        html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Применим условия равенства синусов:</p>", html


def cosine_argument_proof(a):
    from .exam_trigonometric_proof import families, series_lines
    from .exam_trigonometric_selection import equivalent_series

    data = a.argument_pair
    left, right = data.left, data.right
    html = line(a.original)
    html += "<p>Применим формулы приведения и двойного угла:</p>"
    html += line(sp.latex(data.reduced) + "=0")
    if data.weight != 1:
        html += "<p>Представим левую часть через косинусы и сократим ненулевой числовой множитель:</p>"
        html += line(
            sp.latex(data.reduced)
            + "="
            + sp.latex(data.weight * (sp.cos(left, evaluate=False) - sp.cos(right)))
        )
        html += line(sp.latex(data.weight) + r"\ne0")
    html += line(
        sp.latex(sp.cos(left, evaluate=False))
        + "="
        + sp.latex(sp.cos(right, evaluate=False))
    )
    html += "<p>Косинусы равны, когда их аргументы совпадают или противоположны с точностью до целого числа полных оборотов:</p>"
    html += line(sp.latex(left) + "=" + sp.latex(right) + r"+2\pi k")
    html += line(sp.latex(left) + r"=-\left(" + sp.latex(right) + r"\right)+2\pi k")
    rows = argument_rows(data)
    if any(
        sp.expand(expression).coeff(X) < 0
        for expression, series in rows
        if series is not None
    ):
        html += "<p>При отрицательном коэффициенте переобозначим целый параметр противоположным; он по-прежнему пробегает все целые числа.</p>"
    for expression, series in rows:
        html += line(sp.latex(sp.expand(expression)) + r"=2\pi k")
        if series is None:
            html += "<p>Это равенство не выполняется ни при одном целом k; эта ветвь решений не даёт.</p>"
        else:
            for text in series_lines((series,)):
                html += line(text + r",\quad k\in\mathbb Z")
    source = tuple(series for _, series in rows if series is not None)
    if len(source) == 2 and equivalent_series(source, (source[1],)):
        html += "<p>Первая серия решений входит во вторую.</p>"
    elif len(source) == 2 and equivalent_series(source, (source[0],)):
        html += "<p>Вторая серия решений входит в первую.</p>"
    else:
        html += "<p>Объединим полученные серии:</p>"
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Сведём уравнение к равенству косинусов:</p>", html
