"""Factor a sine/cosine sum on the unit circle and exclude an impossible branch."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T


def impossible_branch(expression):
    from .exam_trigonometric import Branch

    if (
        not expression.is_polynomial(S, C)
        or sp.Poly(expression, S, C).total_degree() != 1
    ):
        return None
    a, b, d = expression.coeff(S), expression.coeff(C), expression.subs({S: 0, C: 0})
    if (
        a == 0
        or b == 0
        or d == 0
        or sp.simplify(a * a - b * b) != 0
        or sp.simplify(d * d - 4 * a * a) != 0
    ):
        return None
    return Branch(T, sp.S.One, (), (), (), original=expression, impossible=True)


def branches(raw):
    from .exam_trigonometric_ratios import linear_branch

    if (
        raw.free_symbols != {S, C}
        or not raw.is_polynomial(S, C)
        or sp.Poly(raw, S, C).total_degree() != 2
    ):
        raise UnsupportedCondition(
            "the ratio method must arise from a quadratic in sine and cosine"
        )
    constant = raw.subs({S: 0, C: 0})
    lifted = sp.expand(raw + constant * (S * S + C * C - 1))
    from .exam_trigonometric_factors import separated

    separate = separated(lifted, S, False)
    if separate is not None:
        return separate
    factors = sp.factor_list(lifted, S, C, extension=True)[1]
    if len(factors) != 2 or any(power != 1 for _, power in factors):
        raise UnsupportedCondition(
            "the unit-circle substitution must give two linear factors"
        )
    result = []
    for factor, _ in factors:
        branch = linear_branch(factor) or impossible_branch(factor)
        if branch is None:
            raise UnsupportedCondition(
                "each linear combination needs a reviewed solution or impossibility proof"
            )
        result.append(branch)
    if sum(b.impossible for b in result) != 1:
        raise UnsupportedCondition(
            "one homogeneous branch and one impossible extreme branch are required"
        )
    return lifted, tuple(sorted(result, key=lambda b: b.impossible))


def exclude(branch, angle="x"):
    from .exam_trigonometric_proof import formula

    expression = sp.expand(branch.original)
    a, b, d = expression.coeff(S), expression.coeff(C), expression.subs({S: 0, C: 0})
    sine, cosine = sp.simplify(-d / (2 * a)), sp.simplify(-d / (2 * b))
    if sine**2 != 1 or cosine**2 != 1:
        raise UnsupportedCondition(
            "the extreme sum must force both functions to unit magnitude"
        )
    html = "<p>Вторая ветвь требует предельного значения суммы двух величин. Равенство возможно только при одновременных значениях:</p>"
    html += line(formula(a * S + b * C, angle) + "=" + sp.latex(-d))
    html += line(
        formula(S, angle)
        + "="
        + sp.latex(sine)
        + r",\quad "
        + formula(C, angle)
        + "="
        + sp.latex(cosine)
    )
    html += line(formula(S * S + C * C, angle) + "=2")
    html += "<p>Это противоречит основному тождеству, поэтому данная ветвь корней не имеет:</p>"
    html += line(formula(S * S + C * C, angle) + "=1")
    return html


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_variants import argument

    angle = argument(a.scale)
    html = ""
    for text, value in a.identities:
        html += line(text + "=" + formula(value, angle))
    html += line(formula(a.raw, angle) + "=0")
    html += "<p>Заменим единицу суммой квадратов синуса и косинуса, затем выделим квадрат линейного выражения:</p>"
    html += line(formula(S * S + C * C, angle) + "=1")
    html += line(formula(a.reduced, angle) + "=0")
    linear = next(b.original for b in a.branches if not b.impossible)
    coefficient = linear.coeff(S)
    leading = sp.cancel(a.reduced.coeff(S, 2) / coefficient**2)
    middle = sp.cancel(a.reduced.coeff(S).subs(C, 0) / coefficient)
    quadratic = sp.Add(
        sp.Mul(leading, linear**2, evaluate=False),
        sp.Mul(middle, linear, evaluate=False),
        evaluate=False,
    )
    if sp.expand(quadratic - a.reduced) != 0:
        raise UnsupportedCondition(
            "the completed square must match the lifted equation exactly"
        )
    html += line(formula(quadratic, angle) + "=0")
    html += line(formula(sp.factor(a.reduced, extension=True), angle) + "=0")
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю:</p>"
    for branch in a.branches:
        html += line(formula(branch.original, angle) + "=0")
    html += "".join(
        exclude(branch, angle) for branch in a.branches if branch.impossible
    )
    html += "<p>Решим оставшееся однородное линейное уравнение:</p>"
    for branch in a.branches:
        if not branch.impossible:
            html += polynomial(branch, angle=angle, root_scale=a.scale)
    return (
        "<p>Используем формулы суммы аргументов и основное тригонометрическое тождество:</p>",
        html,
    )
