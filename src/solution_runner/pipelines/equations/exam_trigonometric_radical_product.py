"""Keep zero-radical and positive-radical cases separate at every original pole."""

from dataclasses import dataclass

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T, U, compile_equation
from .power_arithmetic import balanced, clean


@dataclass(frozen=True)
class RadicalProduct:
    factor: sp.Expr
    radicand: sp.Expr


def operands(formula):
    text = clean(formula).removesuffix(".")
    if not text.startswith("("):
        return None
    factor, end = balanced(text, 0, "(", ")")
    tail = text[end:].removeprefix(r"\cdot").removeprefix(r"\times")
    if not tail.startswith(r"\sqrt{"):
        return None
    radicand, end = balanced(tail, 5)
    if tail[end:] != "=0" or "x" not in radicand:
        return None
    return factor, radicand


def compile_product(factor, radicand):
    from .exam_trigonometric_methods import Equation, ExamAngleParser
    from .exam_trigonometric_radical_equation import compile_values

    atoms, denominators = {}, []
    values = [
        ExamAngleParser(text.replace("x", r"\alpha"), atoms, denominators).parse().value
        for text in (factor, radicand)
    ]
    (value, root), poles, identities = compile_values(values, atoms, denominators)
    weights = (root / S, root / C, root * C / S, root * S / C)
    if not any(
        not (w := sp.cancel(weight)).free_symbols and w.is_real is True and w != 0
        for weight in weights
    ):
        raise UnsupportedCondition(
            "one homogeneous sine, cosine or ratio radicand is required"
        )
    if not set(poles) <= {S, C}:
        raise UnsupportedCondition(
            "the radical product retains only original sine/cosine poles"
        )
    numerator, denominator = sp.fraction(sp.cancel(value))
    root_num, root_den = sp.fraction(sp.cancel(root))
    if (
        not numerator.is_polynomial(S, C)
        or sp.Poly(numerator, S, C).total_degree() > 4
        or not denominator.is_polynomial(S, C)
    ):
        raise UnsupportedCondition(
            "the radical factor needs a bounded unit-circle polynomial"
        )
    source_factor, _ = compile_equation(factor + "=0")
    if source_factor.free_symbols - {S, C, T, U} or (
        source_factor.has(T, U)
        and (len(source_factor.free_symbols) != 1 or sp.total_degree(source_factor) > 2)
    ):
        raise UnsupportedCondition(
            "the parent factor must be polynomial or one quadratic ratio"
        )
    return Equation(
        sp.expand(numerator * root_num),
        identities,
        sp.S.One,
        poles=poles,
        domain=sp.expand(root_num * root_den),
        radical_product=RadicalProduct(source_factor, root),
    )


def cases(compiled, preferred, allow_inverse):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_domain import restrict, without_poles

    root_num = sp.fraction(compiled.radical_product.radicand)[0]
    zero = solve_branches(root_num, S if root_num.has(S) else C, allow_inverse)[1]
    positive = solve_branches(
        compiled.radical_product.factor, preferred, allow_inverse
    )[1]
    return (
        without_poles(restrict(zero, compiled.domain), compiled.poles),
        without_poles(restrict(positive, compiled.domain, strict=True), compiled.poles),
    )


def prepare(a, parent_html):
    if a.domain is None or a.strict_domain or operands(a.original) is None:
        return a
    from dataclasses import replace

    from .exam_trigonometric import select
    from .exam_trigonometric_parameters import affine_families
    from .exam_trigonometric_selection import equivalent_series

    parent_html = parent_html.replace(r"\dfrac", r"\frac")
    source = tuple(
        dict.fromkeys(
            (q, p)
            for q, p, _ in affine_families(parent_html)
            if equivalent_series((*a.series, (q, p)), a.series)
        )
    )
    if source and equivalent_series(source, a.series):
        series = source
    else:
        declared = affine_families(parent_html)
        if (
            not declared
            or declared[0][1] != 1
            or (2 * declared[0][0]).is_Integer is not True
        ):
            return a
        zero = tuple(
            item
            for item in a.series
            if item[1] == 1
            and sp.simplify(
                a.domain.subs({S: sp.sin(item[0] * sp.pi), C: sp.cos(item[0] * sp.pi)})
            )
            == 0
        )
        if not zero:
            return a
        series = (*zero, *(item for item in a.series if item not in zero))
    selected, trace = select(series, a.bounds)
    return replace(
        a,
        series=series,
        selected=selected,
        selections=trace,
        series_aligned=series != a.series,
    )
