"""Factor sum identities into two equations with independent integer angles."""

from dataclasses import dataclass

import sympy as sp
from sympy.simplify.fu import TR9

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S

X = sp.Symbol("x", real=True)


@dataclass(frozen=True)
class AngleProduct:
    factored: sp.Expr
    factors: tuple


def compile_product(formula):
    from .exam_trigonometric_methods import Equation, parse_equation

    values, atoms, denominators = parse_equation(formula)
    if denominators or any(
        a.function not in ("sin", "cos")
        or a.coefficient.is_Integer is not True
        or not 1 <= a.coefficient <= 12
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "separate angle factors require denominator-free bounded integer angles"
        )
    compiled = {
        symbol: (sp.sin if a.function == "sin" else sp.cos)(
            a.coefficient * X + a.shift * sp.pi
        )
        for symbol, a in atoms.items()
    }
    raw = (values[0] - values[1]).xreplace(compiled)
    factored = sp.factor(TR9(raw))
    factors = sp.factor_list(factored)[1]
    if len(factors) != 2 or any(power != 1 for _, power in factors):
        raise UnsupportedCondition(
            "the sum identity must yield exactly two distinct affine factors"
        )
    result = []
    for expression, _ in factors:
        functions = expression.atoms(sp.sin, sp.cos)
        if len(functions) != 1:
            raise UnsupportedCondition("each factor must use one sine or cosine")
        function = functions.pop()
        scale = sp.cancel(function.args[0] / X)
        variable = S if function.func == sp.sin else C
        polynomial = expression.xreplace({function: variable})
        if (
            scale.is_Integer is not True
            or not 1 <= scale <= 12
            or polynomial.free_symbols != {variable}
            or sp.degree(polynomial, variable) != 1
        ):
            raise UnsupportedCondition(
                "each factor must be affine in one unshifted integer angle"
            )
        result.append((variable, scale, polynomial))
    if sp.trigsimp(sp.expand_trig(raw - factored)) != 0:
        raise UnsupportedCondition("the angle product must equal the original equation")
    return Equation(
        raw, (), sp.S.One, angle_product=AngleProduct(factored, tuple(result))
    )


def branches(product):
    from .exam_trigonometric import Branch
    from .exam_trigonometric_inverse import angles, ordered

    result = []
    for variable, scale, polynomial in product.factors:
        value = sp.cancel(-polynomial.subs(variable, 0) / polynomial.coeff(variable))
        roots = angles(variable, value)
        residues = ordered(
            (q + 2 * k) / scale for q in roots for k in range(int(scale))
        )
        result.append(
            Branch(
                variable, polynomial, (value,), (value,), residues, angle_scale=scale
            )
        )
    return tuple(sorted(result, key=lambda b: b.polynomial.subs(b.variable, 0) != 0))


def proof(a):
    from .exam_trigonometric_proof import polynomial
    from .exam_trigonometric_variants import argument

    html = line(a.original)
    name = (
        "косинусов"
        if not a.raw.has(sp.sin)
        else "синусов"
        if not a.raw.has(sp.cos)
        else "тригонометрических функций"
    )
    html += "<p>Применим формулу приведения, затем формулу суммы " + name + ":</p>"
    html += line(sp.latex(a.raw) + "=0")
    html += line(sp.latex(sp.expand(a.angle_product.factored)) + "=0")
    html += line(sp.latex(a.angle_product.factored) + "=0")
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю. Решим каждое уравнение со своим углом:</p>"
    for branch in a.branches:
        html += polynomial(
            branch, angle=argument(branch.angle_scale), root_scale=branch.angle_scale
        )
    return "<p>Разложим левую часть уравнения на множители:</p>", html
