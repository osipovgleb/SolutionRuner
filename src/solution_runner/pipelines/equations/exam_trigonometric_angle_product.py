"""Factor reviewed sum and square identities into equations with separate angles."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup
from sympy.simplify.fu import TR8, TR9

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S

X = sp.Symbol("x", real=True)
FUNCTION = r"\\(?:sin|cos)\d*x"


@dataclass(frozen=True)
class AngleProduct:
    factored: sp.Expr
    factors: tuple
    identities: tuple = ()
    reduced: sp.Expr | None = None
    summed: bool = True


def reviewed(parent_html):
    patterns = (
        FUNCTION + r"(?:\\cdot)?\([^()]*" + FUNCTION + r"[^()]*\)",
        r"\([^()]*" + FUNCTION + r"[^()]*\)(?:\\cdot)?" + FUNCTION,
    )
    nodes = BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    solved = set()
    for node in nodes:
        text = "".join(node["data-inline-latex"].split())
        for m in re.finditer(r"\\(sin|cos)(\d*)x&?=", text):
            right = re.split(
                r"\\\\|\\(?:iff|Leftrightarrow|end|quad)", text[m.end() :], maxsplit=1
            )[0]
            if not re.search(r"\\(?:sin|cos)", right):
                solved.add((m[1], int(m[2] or 1)))
    for node in nodes:
        text = (
            "".join(node["data-inline-latex"].split())
            .replace(r"\left", "")
            .replace(r"\right", "")
        )
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                angles = {
                    (name, int(coefficient or 1))
                    for name, coefficient in re.findall(r"\\(sin|cos)(\d*)x", match[0])
                }
                if (
                    len(angles) > 1
                    and angles <= solved
                    and any(scale > 1 for _, scale in angles)
                ):
                    return True
    zero_base = any(
        re.search(r"\\(?:sin|cos)x=0", "".join(n["data-inline-latex"].split()))
        for n in nodes
    )
    text = (
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
    )
    return bool(
        zero_base
        and len(solved) == 2
        and any(scale > 1 for _, scale in solved)
        and nodes
        and re.search(r"\\(?:tg|ctg)", nodes[0]["data-inline-latex"])
        and "из первой серии" in text
        and "из второй" in text
    )


def reduce_squares(expression):
    substitutions = {}
    for power in expression.atoms(sp.Pow):
        if power.exp == 2 and power.base.func in (sp.sin, sp.cos) and power.base.has(X):
            angle = power.base.args[0]
            substitutions[power] = (
                1 + (-1 if power.base.func == sp.sin else 1) * sp.cos(2 * angle)
            ) / 2
    identities = tuple(
        sorted(substitutions.items(), key=lambda item: sp.default_sort_key(item[0]))
    )
    return sp.expand(expression.xreplace(substitutions)), identities


def factor_angles(expression):
    factors = sp.factor_list(expression)[1]
    if len(factors) != 2 or any(power != 1 for _, power in factors):
        return None
    result = []
    for factor, _ in factors:
        functions = factor.atoms(sp.sin, sp.cos)
        if len(functions) != 1:
            return None
        function = functions.pop()
        scale = sp.cancel(function.args[0] / X)
        variable = S if function.func == sp.sin else C
        polynomial = factor.xreplace({function: variable})
        if (
            scale.is_Integer is not True
            or not 1 <= scale <= 12
            or polynomial.free_symbols != {variable}
            or sp.degree(polynomial, variable) != 1
        ):
            return None
        result.append((variable, scale, polynomial))
    return tuple(result)


def compile_product(formula):
    from .exam_trigonometric_methods import Equation, constant_angles, parse_equation

    values, atoms, denominators = parse_equation(formula)
    values, atoms, denominators, constants = constant_angles(
        values, atoms, denominators
    )
    if any(a.function in ("tg", "ctg") for a in atoms.values()):
        return compile_ratio_factor(values, atoms, denominators, constants)
    if (
        denominators
        or not atoms
        or any(
            a.function not in ("sin", "cos")
            or a.coefficient.is_Integer is not True
            or not 1 <= abs(a.coefficient) <= 12
            for a in atoms.values()
        )
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
    reduced, identities = reduce_squares(raw)
    for summed, candidate in [
        (False, reduced),
        *[(True, value) for value in sum_products(reduced)],
    ]:
        factored = sp.factor(candidate)
        factors = factor_angles(factored)
        if factors is not None:
            break
    else:
        raise UnsupportedCondition(
            "the identities must yield exactly two distinct affine angle factors"
        )
    if sp.trigsimp(sp.expand_trig(raw - factored)) != 0:
        raise UnsupportedCondition("the angle product must equal the original equation")
    return Equation(
        raw,
        (),
        sp.S.One,
        angle_product=AngleProduct(
            factored, factors, constants + identities, reduced, summed
        ),
    )


def compile_ratio_factor(values, atoms, denominators, constants):
    from dataclasses import replace

    from .exam_trigonometric_poles import compile_quotients

    equation = compile_quotients(values, atoms, denominators)
    numerator = (
        equation.factored_source
        if equation.factored_source is not None
        else equation.raw
    )
    raw = numerator.xreplace({S: sp.sin(X), C: sp.cos(X)})
    factored = sp.Mul(*(TR8(factor) for factor in sp.Mul.make_args(sp.factor(raw))))
    factors = factor_angles(factored)
    if factors is None or sp.trigsimp(sp.expand_trig(raw - factored)) != 0:
        raise UnsupportedCondition(
            "the cleared ratio must give two exact affine angle factors"
        )
    identities = constants + tuple(
        (left, right.xreplace({S: sp.sin(X), C: sp.cos(X)}))
        for left, right in equation.identities
    )
    identities += ((sp.sin(X) * sp.cos(X), sp.sin(2 * X) / 2),)
    return replace(
        equation,
        raw=raw,
        angle_product=AngleProduct(factored, factors, identities, raw, False),
    )


def sum_products(expression):
    yield TR9(expression)
    terms = sp.Add.make_args(expression)
    if len(terms) > 8:
        raise UnsupportedCondition(
            "the reviewed sum-to-product expression has at most eight terms"
        )
    for i, first in enumerate(terms):
        for second in terms[i + 1 :]:
            paired = TR9(first + second)
            if paired != first + second:
                yield sp.expand(expression - first - second + paired)


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
    from .exam_trigonometric_proof import families, formula, pi, polynomial
    from .exam_trigonometric_variants import argument

    data = a.angle_product
    html = ""
    if a.poles:
        html += (
            "<p>Сохраним исходную область определения до умножения на знаменатель:</p>"
        )
        for pole in a.poles:
            html += line(formula(pole) + r"\ne0")
    html += line(a.original)
    if data.identities:
        html += (
            "<p>Используем определение тригонометрического отношения и формулу двойного угла:</p>"
            if a.poles
            else "<p>Применим формулы приведения и понижения степени:</p>"
        )
        for left, right in data.identities:
            html += line(
                (left if isinstance(left, str) else sp.latex(left))
                + "="
                + sp.latex(right)
            )
    if data.summed:
        name = (
            "косинусов"
            if not a.raw.has(sp.sin)
            else "синусов"
            if not a.raw.has(sp.cos)
            else "тригонометрических функций"
        )
        html += "<p>Применим формулу приведения, затем формулу суммы " + name + ":</p>"
    else:
        html += "<p>Вынесем общий множитель:</p>"
    if a.poles:
        html += "<p>Умножаем только на ненулевой в исходной области определения знаменатель:</p>"
    html += line(sp.latex(data.reduced if data.identities else a.raw) + "=0")
    html += line(sp.latex(sp.expand(data.factored)) + "=0")
    html += line(sp.latex(data.factored) + "=0")
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю. Решим каждое уравнение со своим углом:</p>"
    nominal = branches(data) if a.poles else a.branches
    for branch in nominal:
        html += polynomial(
            branch, angle=argument(branch.angle_scale), root_scale=branch.angle_scale
        )
    if a.poles:
        excluded = sorted({q for b in nominal for q in b.residues} - set(a.residues))
        for q in excluded:
            html += "<p>Эта серия нарушает исходную область определения:</p>" + line(
                "x=" + pi(q) + r"+2\pi k"
            )
        html += "<p>После проверки исходных ограничений остаются серии:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Разложим левую часть уравнения на множители:</p>", html
