"""Preserve reviewed sum-to-product methods, including a square and original poles."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup
from sympy.simplify.fu import TR9

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S

X = sp.Symbol("x", real=True)


@dataclass(frozen=True)
class SumProduct:
    cleared: sp.Expr
    root: sp.Expr
    product: sp.Expr
    squared: bool
    poles: tuple = ()
    normalizer: sp.Expr = sp.S.One


def square_style(html):
    return any(
        re.search(
            r"\([^()]*\\sin[^()]*[+-][^()]*\\sin[^()]*\)\^\{?2\}?=0",
            "".join(n["data-inline-latex"].split()),
        )
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )


def actual(formula):
    from .exam_trigonometric_methods import constant_angles, parse_equation

    values, atoms, denominators = parse_equation(formula)
    values, atoms, denominators, _ = constant_angles(values, atoms, denominators)
    if not atoms or any(a.function not in ("sin", "cos") for a in atoms.values()):
        raise UnsupportedCondition("the sum-to-product method requires sine and cosine")
    functions = {
        symbol: (sp.sin if a.function == "sin" else sp.cos)(
            a.coefficient * X + a.shift * sp.pi
        )
        for symbol, a in atoms.items()
    }
    return (values[0] - values[1]).xreplace(functions), denominators, atoms


def compile_square(formula):
    raw, denominators, _ = actual(formula)
    if any(d.free_symbols for d in denominators):
        raise UnsupportedCondition("the square of a sum must have no original poles")
    substitutions = {
        p: 1 - sp.sin(p.base.args[0]) ** 2
        for p in raw.atoms(sp.Pow)
        if p.exp == 2 and p.base.func == sp.cos
    }
    reduced = sp.expand(raw.xreplace(substitutions))
    functions = sorted(reduced.atoms(sp.sin, sp.cos), key=sp.default_sort_key)
    symbols = sp.symbols("v:" + str(len(functions)), real=True)
    forward, backward = dict(zip(functions, symbols)), dict(zip(symbols, functions))
    coefficient, factors = sp.factor_list(reduced.xreplace(forward), *symbols)
    if coefficient == 0 or len(factors) != 1 or factors[0][1] != 2:
        raise UnsupportedCondition(
            "the parent square requires exactly one complete square"
        )
    root = factors[0][0].xreplace(backward)
    if (
        len(sp.Add.make_args(root)) != 2
        or len(root.atoms(sp.sin)) != 2
        or root.has(sp.cos)
    ):
        raise UnsupportedCondition("the square root must be a sum of two sine terms")
    if sp.trigsimp(sp.expand_trig(raw - coefficient * root**2)) != 0:
        raise UnsupportedCondition("the square must equal the original equation")
    return equation(SumProduct(raw, root, TR9(root), True, normalizer=coefficient))


def compile_reciprocal(formula):
    if not all(
        token in "".join(formula.split())
        for token in (r"\frac{1}{\sin", r"\frac{1}{\cos")
    ):
        return None
    raw, denominators, atoms = actual(formula)
    if not any(d.free_symbols for d in denominators) or any(
        a.coefficient != 1 or a.shift != 0 for a in atoms.values()
    ):
        return None
    cleared = sp.cancel(raw * sp.sin(X) * sp.cos(X)).xreplace(
        {sp.sin(X): S, sp.cos(X): C}
    )
    if not cleared.is_polynomial(S, C) or sp.Poly(cleared, S, C).total_degree() != 2:
        return None
    coefficient = cleared.coeff(S).subs(C, 0)
    sign = (
        sp.simplify(-cleared.coeff(S).coeff(C) / (2 * sp.sqrt(2) * coefficient))
        if coefficient
        else 0
    )
    expected = coefficient * (S + C - 2 * sp.sqrt(2) * sign * S * C)
    if not coefficient or sp.expand(cleared - expected) != 0:
        return None
    if sign not in (-1, 1):
        raise UnsupportedCondition(
            "the reciprocal sum requires a reviewed exact difference of sines"
        )
    root = sp.sin(X + sp.pi / 4) - sign * sp.sin(2 * X)
    product = (
        sp.Mul(
            2,
            sp.cos(3 * X / 2 + sp.pi / 8),
            sp.sin(sp.pi / 8 - X / 2, evaluate=False),
            evaluate=False,
        )
        if sign == 1
        else TR9(root)
    )
    return equation(
        SumProduct(
            cleared.xreplace({S: sp.sin(X), C: sp.cos(X)}),
            root,
            product,
            False,
            (sp.sin(X), sp.cos(X)),
            coefficient * sp.sqrt(2),
        )
    )


def equation(data):
    from .exam_trigonometric_methods import Equation

    functions = data.product.atoms(sp.sin, sp.cos)
    if len(functions) != 2 or not data.product.is_Mul:
        raise UnsupportedCondition("the sum must factor into exactly two functions")
    scale = sp.gcd_list([sp.expand(f.args[0]).coeff(X) for f in functions])
    if scale <= 0 or scale.is_Rational is not True or scale.q > 12:
        raise UnsupportedCondition(
            "the angle product requires a bounded rational base angle"
        )
    equivalent = data.root**2 if data.squared else data.root
    if (
        not data.normalizer
        or sp.trigsimp(data.cleared - data.normalizer * equivalent, method="fu") != 0
    ):
        raise UnsupportedCondition(
            "the reduced sum must preserve the original equation"
        )
    if sp.trigsimp(data.root - data.product, method="fu") != 0:
        raise UnsupportedCondition("the sum-to-product identity must hold exactly")
    return Equation(data.root, (), scale, sum_product=data)


def branches(a):
    from .exam_trigonometric import Branch, select
    from .exam_trigonometric_inverse import level_series

    data = a.sum_product
    result = []
    for function in sorted(data.product.atoms(sp.sin, sp.cos), key=sp.default_sort_key):
        angle = sp.expand(function.args[0])
        multiple, phase = (
            angle.coeff(X) / a.scale,
            sp.simplify(angle.subs(X, 0) / sp.pi),
        )
        if multiple < 0:
            multiple, phase = -multiple, -phase
        if (
            multiple.is_Integer is not True
            or not 1 <= multiple <= 12
            or phase.is_Rational is not True
            or (24 * phase).is_Integer is not True
        ):
            raise UnsupportedCondition(
                "the factors require bounded integer angles and exact phases"
            )
        variable = S if function.func == sp.sin else C
        series = tuple(
            ((q - phase) / multiple, period / multiple)
            for q, period in level_series(variable, sp.S.Zero)
        )
        residues = select(series, (0, 2, True, False))[0]
        if any(
            sp.simplify(pole.subs(X, q * sp.pi / a.scale)) == 0
            for q in residues
            for pole in data.poles
        ):
            raise UnsupportedCondition(
                "a sum-product root violates the original nonzero domain"
            )
        result.append(
            Branch(
                variable,
                variable,
                (sp.S.Zero,),
                (sp.S.Zero,),
                residues,
                angle_shift=phase,
                angle_scale=multiple,
            )
        )
    return tuple(result)


def proof(a):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import series_lines

    data = a.sum_product
    html = line(a.original)
    if data.poles:
        html += (
            "<p>Запишем исходную область определения до умножения на знаменатели:</p>"
        )
        html += line(r"\sin x\ne0,\quad\cos x\ne0")
        html += "<p>В этой области умножим на произведение синуса и косинуса:</p>"
    else:
        html += "<p>Применим основное тригонометрическое тождество и выделим полный квадрат:</p>"
    html += line(sp.latex(data.cleared) + "=0")
    if data.squared:
        html += line(sp.latex(data.root**2) + "=0")
    elif data.normalizer != 1:
        html += line(sp.latex(sp.expand(data.cleared / data.normalizer)) + "=0")
    html += line(sp.latex(data.root) + "=0")
    html += "<p>Преобразуем сумму или разность синусов в произведение:</p>"
    html += line(sp.latex(data.product) + "=0")
    for b in a.branches:
        function = sp.sin if b.variable == S else sp.cos
        html += line(
            sp.latex(function(b.angle_scale * a.scale * X + b.angle_shift * sp.pi))
            + "=0"
        )
        series = tuple(
            (
                (q - b.angle_shift) / (b.angle_scale * a.scale),
                period / (b.angle_scale * a.scale),
            )
            for q, period in level_series(b.variable, sp.S.Zero)
        )
        for text in series_lines(series):
            html += line(text + r",\quad k\in\mathbb Z")
    if data.poles:
        html += "<p>Все найденные серии удовлетворяют исходной ОДЗ. Включённую серию объединим с более частой:</p>"
        for text in series_lines(a.series):
            html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Применим формулу суммы и разности синусов:</p>", html
