"""Clear bounded angle quotients and cancel only factors forbidden by original poles."""

from dataclasses import replace

import sympy as sp
from sympy.simplify.fu import TR8, TR9

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_angle_product import AngleProduct, X, factor_angles
from .exam_trigonometric_compile import C, S


def cleared_input(values, atoms, denominators):

    if not atoms or any(
        a.function not in ("sin", "cos", "tg", "ctg")
        or a.shift != 0
        or a.coefficient.is_Rational is not True
        or not 0 < a.coefficient <= 12
        or a.coefficient.q > 2
        for a in atoms.values()
    ):
        raise UnsupportedCondition("bounded unshifted quotient angles are required")
    compiled, poles = {}, set()
    for symbol, atom in atoms.items():
        sine, cosine = sp.sin(atom.coefficient * X), sp.cos(atom.coefficient * X)
        compiled[symbol] = {
            "sin": sine,
            "cos": cosine,
            "tg": sine / cosine,
            "ctg": cosine / sine,
        }[atom.function]
        if atom.function in ("tg", "ctg"):
            poles.add(cosine if atom.function == "tg" else sine)
    for d in denominators:
        if not d.free_symbols:
            continue
        if not d.is_Mul and d not in atoms:
            raise UnsupportedCondition(
                "each added quotient pole must be a trig monomial"
            )
        for symbol, power in d.as_powers_dict().items():
            if (
                symbol in atoms
                and power.is_Integer
                and power > 0
                and atoms[symbol].function in ("sin", "cos")
            ):
                poles.add(compiled[symbol])
            elif symbol.free_symbols:
                raise UnsupportedCondition(
                    "each added quotient pole must be a trig monomial"
                )
    raw, _ = sp.fraction(sp.together((values[0] - values[1]).xreplace(compiled)))
    terms = sp.Add.make_args(sp.expand(raw))
    if len(terms) > 8 or any(
        sum(v for f, v in term.as_powers_dict().items() if f.func in (sp.sin, sp.cos))
        > 3
        for term in terms
    ):
        raise UnsupportedCondition(
            "the cleared quotient exceeds the bounded product identities"
        )
    return raw, poles


def compile_product(values, atoms, denominators, constants):
    from .exam_trigonometric_angle_domain import equivalent
    from .exam_trigonometric_folding import common_scale
    from .exam_trigonometric_methods import Equation

    raw, poles = cleared_input(values, atoms, denominators)
    factored = sp.factor(TR9(TR8(raw)))
    removed = []
    retained = []
    for factor, power in sp.factor_list(factored)[1]:
        if power != 1 or factor.func not in (sp.sin, sp.cos):
            raise UnsupportedCondition(
                "the quotient must factor into distinct sine/cosine zeros"
            )
        ratios = [sp.cancel(p.args[0] / factor.args[0]) for p in poles]
        forbidden = any(
            r.is_Integer is True
            and (
                (factor.func == sp.sin and p.func == sp.sin)
                or (
                    factor.func == sp.cos
                    and (
                        (p.func == sp.cos and r % 2 == 1)
                        or (p.func == sp.sin and r % 2 == 0)
                    )
                )
            )
            for p, r in zip(poles, ratios)
        )
        (removed if forbidden else retained).append(factor)
    if len(retained) != 2 or not removed:
        raise UnsupportedCondition(
            "two angle factors and a certified forbidden factor are required"
        )
    scales = [sp.cancel(f.args[0] / X) for f in (*retained, *poles)]
    from .trig_symbolic_parser import SymbolicAtom

    base = common_scale(
        {i: SymbolicAtom("sin", c, 0, "x", "") for i, c in enumerate(scales)}
    )
    transform = lambda e: e.subs(X, X / base)
    if not equivalent(transform(raw), transform(factored)):
        raise UnsupportedCondition(
            "the quotient factorization requires an exact unit-circle certificate"
        )
    remaining = transform(sp.Mul(*retained))
    factors = factor_angles(remaining)
    if factors is None:
        raise UnsupportedCondition(
            "the remaining quotient factors exceed the reviewed angle bound"
        )
    originals = tuple(sorted((transform(p) for p in poles), key=sp.default_sort_key))
    if any(
        sp.cancel(p.args[0] / X).is_Integer is not True
        or not 1 <= sp.cancel(p.args[0] / X) <= 12
        for p in originals
    ):
        raise UnsupportedCondition(
            "the original quotient poles exceed the reviewed angle bound"
        )
    polynomial_poles = tuple(
        sp.expand(sp.expand_trig(p).xreplace({sp.sin(X): S, sp.cos(X): C}))
        for p in originals
    )
    return Equation(
        transform(raw),
        (),
        base,
        poles=polynomial_poles,
        angle_product=AngleProduct(
            remaining,
            factors,
            constants,
            transform(raw),
            False,
            source_poles=originals,
            cancelled=transform(sp.Mul(*removed)),
            full_product=transform(factored),
        ),
    )


def filter_branches(branches, poles):
    result = []
    for b in branches:
        retained = []
        for q in b.residues:
            excluded = False
            for pole in poles:
                angle = sp.cancel(pole.args[0] / X) * q
                if angle.is_Rational is not True:
                    raise UnsupportedCondition(
                        "quotient pole checks require exact rational angles"
                    )
                excluded |= (
                    angle.is_Integer is True
                    if pole.func == sp.sin
                    else (angle - sp.Rational(1, 2)).is_Integer is True
                )
            if not excluded:
                retained.append(q)
        result.append(replace(b, residues=tuple(retained)))
    return tuple(result)


def proof(a):
    from .exam_trigonometric_proof import families, polynomial
    from .exam_trigonometric_variants import argument

    data = a.angle_product
    physical = lambda e: sp.latex(e.subs(X, a.scale * X))
    html = "<p>Сохраним исходные ограничения до преобразования дробей:</p>"
    for pole in data.source_poles:
        html += line(physical(pole) + r"\ne0")
    html += line(a.original)
    html += "<p>Приведём дроби к общему ненулевому знаменателю. Применим формулы косинуса суммы, двойного угла и разности синусов:</p>"
    html += line(physical(data.reduced) + "=0")
    variable, small, _ = min(data.factors, key=lambda item: item[1])
    common = (sp.sin if variable == S else sp.cos)(small * X)
    html += line(
        physical(
            sp.Mul(common, TR8(sp.cancel(data.full_product / common)), evaluate=False)
        )
        + "=0"
    )
    html += line(physical(data.full_product) + "=0")
    html += "<p>Нули следующего множителя запрещены исходной областью определения, поэтому на этот множитель можно разделить:</p>"
    html += line(physical(data.cancelled) + r"\ne0")
    html += line(physical(data.factored) + "=0")
    for branch in a.branches:
        html += polynomial(
            branch,
            angle=argument(branch.angle_scale * a.scale),
            root_scale=branch.angle_scale * a.scale,
        )
    html += "<p>Проверяем каждую серию по исходным знаменателям и исключаем запрещённые значения целого параметра:</p>"
    parameter = sp.Symbol("p", integer=True)
    for family in a.restricted_families:
        for index in family.excluded:
            forbidden = sp.expand(
                family.offset + family.period * (family.modulus * parameter + index)
            )
            html += line(
                family.parameter
                + "="
                + sp.latex(family.modulus * parameter + index)
                + r",\quad p\in\mathbb Z"
            )
            html += line("x=" + sp.latex(forbidden * sp.pi))
            for pole in data.source_poles:
                if sp.simplify(pole.subs(X, a.scale * forbidden * sp.pi)) == 0:
                    html += line(physical(pole) + "=0")
                    break
            else:
                raise UnsupportedCondition(
                    "every excluded index class must have an original zero denominator"
                )
    for text in families(a):
        html += line(text)
    return "<p>Решим уравнение с учётом области определения:</p>", html
