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
    root_offset: sp.Expr = sp.S.Zero


def operand(text):
    if text.startswith(r"\sqrt{"):
        value, end = balanced(text, 5)
        return "root", value, end
    if text.startswith("("):
        value, end = balanced(text, 0, "(", ")")
        nested = operand(value) if value.startswith(r"\sqrt{") else None
        if nested is not None and nested[2] == len(value):
            return "root", nested[1], end
        return "factor", value, end
    return None


def operands(formula):
    text = clean(formula).removesuffix(".")
    if not text.endswith("=0"):
        return None
    body = text[:-2]
    first = operand(body)
    if first is None:
        return None
    rest = body[first[2] :].removeprefix(r"\cdot").removeprefix(r"\times")
    second = operand(rest)
    if second is None or second[2] != len(rest) or first[0] == second[0]:
        return None
    values = {first[0]: first[1], second[0]: second[1]}
    if "x" not in values["root"]:
        return None
    return values["factor"], values["root"]


def shifted_operands(formula, *, allow_vanishing=False):
    from .exam_trigonometric_absolute import R, RootPlaceholderParser
    from .exam_trigonometric_radical_equation import variable_radicals

    text = clean(formula).removesuffix(".")
    if not text.endswith("=0") or not text.startswith("("):
        return None
    first, end = balanced(text, 0, "(", ")")
    rest = text[end:-2].removeprefix(r"\cdot").removeprefix(r"\times")
    if not rest.startswith("("):
        return None
    second, end = balanced(rest, 0, "(", ")")
    if end != len(rest):
        return None
    candidates = [v for v in (first, second) if variable_radicals(v)]
    if len(candidates) != 1:
        return None
    root_factor = candidates[0]
    roots, start = [], 0
    while (index := root_factor.find(r"\sqrt{", start)) >= 0:
        inner, start = balanced(root_factor, index + 5)
        if "x" in inner:
            roots.append((index, inner, start))
    if len(roots) != 1:
        return None
    index, radicand, end = roots[0]
    atoms, denominators = {}, []
    value = (
        RootPlaceholderParser(
            (root_factor[:index] + "(r)" + root_factor[end:]).replace("x", r"\alpha"),
            atoms,
            denominators,
        )
        .parse()
        .value
    )
    coefficient = value.coeff(R)
    if coefficient not in (sp.S.One, -sp.S.One):
        return None
    offset = sp.simplify(value / coefficient - R)
    positive = coefficient == 1 and offset.is_positive is True
    vanishing = allow_vanishing and offset.is_negative is True
    if atoms or denominators or offset.free_symbols or not (positive or vanishing):
        return None
    return (second if root_factor == first else first), radicand, offset


def compile_product(factor, radicand, root_offset=sp.S.Zero):
    from .exam_trigonometric_methods import Equation, ExamAngleParser
    from .exam_trigonometric_radical_equation import compile_values

    if root_offset.free_symbols or root_offset.is_real is not True:
        raise UnsupportedCondition("the additive root offset must be a real constant")
    atoms, denominators = {}, []
    values = [
        ExamAngleParser(text.replace("x", r"\alpha"), atoms, denominators).parse().value
        for text in (factor, radicand)
    ]
    (value, root), poles, identities = compile_values(values, atoms, denominators)
    root_num, root_den = sp.fraction(sp.cancel(root))
    denominators = (root_den, sp.cancel(root_den / S), sp.cancel(root_den / C))
    if (
        not root_num.is_polynomial(S, C)
        or sp.Poly(root_num, S, C).total_degree() != 1
        or root_num.subs({S: 0, C: 0}) != 0
        or not any(
            not d.free_symbols and d.is_real is True and d != 0 for d in denominators
        )
    ):
        raise UnsupportedCondition(
            "a homogeneous linear radicand numerator over a constant, sine or cosine is required"
        )
    if not set(poles) <= {S, C}:
        raise UnsupportedCondition(
            "the radical product retains only original sine/cosine poles"
        )
    numerator, denominator = sp.fraction(sp.cancel(value))
    if (
        not numerator.is_polynomial(S, C)
        or sp.Poly(numerator, S, C).total_degree() > 4
        or not denominator.is_polynomial(S, C)
    ):
        raise UnsupportedCondition(
            "the radical factor needs a bounded unit-circle polynomial"
        )
    try:
        source_factor, _ = compile_equation(factor + "=0")
    except UnsupportedCondition:
        if not value.is_polynomial(S, C):
            raise
        source_factor = value
    if source_factor.free_symbols - {S, C, T, U} or (
        source_factor.has(T, U)
        and (len(source_factor.free_symbols) != 1 or sp.total_degree(source_factor) > 2)
    ):
        raise UnsupportedCondition(
            "the parent factor must be polynomial or one quadratic ratio"
        )
    if root_offset.is_negative:
        raw = numerator * (root_num - root_offset**2 * root_den)
    elif root_offset:
        raw = numerator
    else:
        raw = numerator * root_num
    return Equation(
        sp.expand(raw),
        identities,
        sp.S.One,
        poles=poles,
        domain=sp.expand(root_num * root_den),
        radical_product=RadicalProduct(source_factor, root, root_offset),
    )


def factor_branches(factor, preferred, allow_inverse):
    from .exam_trigonometric import solve_branches

    if not factor.free_symbols:
        if factor == 0:
            raise UnsupportedCondition(
                "an identically zero factor requires its complete domain"
            )
        return ()
    if factor.free_symbols in ({S}, {C}):
        preferred = next(iter(factor.free_symbols))
    elif factor.free_symbols <= {S, C} and preferred not in (S, C):
        preferred = S
    result = solve_branches(factor, preferred, allow_inverse)[1]
    if factor.free_symbols in ({S}, {C}):
        variable = next(iter(factor.free_symbols))
        if sp.degree(factor, variable) == 2 and factor.coeff(variable) == 0:
            from dataclasses import replace

            result = tuple(replace(b, square_level=True) for b in result)
    return result


def cases(compiled, preferred, allow_inverse):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_domain import restrict, without_poles

    data = compiled.radical_product
    root_num = sp.fraction(data.radicand)[0]
    shifted = data.root_offset != 0
    zero = (
        solve_branches(
            root_function(data) - data.root_offset**2, preferred, allow_inverse
        )[1]
        if data.root_offset.is_negative
        else ()
        if shifted
        else solve_branches(root_num, S if root_num.has(S) else C, allow_inverse)[1]
    )
    positive = factor_branches(admissible_factor(compiled)[0], preferred, allow_inverse)
    return (
        without_poles(restrict(zero, compiled.domain), compiled.poles),
        without_poles(
            restrict(positive, compiled.domain, strict=not shifted), compiled.poles
        ),
    )


def root_function(data):
    denominator = sp.fraction(data.radicand)[1]
    if denominator.has(S):
        return sp.cancel(data.radicand.subs(C, U * S))
    if denominator.has(C):
        return sp.cancel(data.radicand.subs(S, T * C))
    return data.radicand


def admissible_factor(compiled):
    factor = compiled.radical_product.factor
    divisor = sp.S.One
    if compiled.radical_product.root_offset.is_negative:
        for pole in compiled.poles:
            if pole not in (S, C):
                continue
            while (
                factor != 0 and factor.is_polynomial(pole) and factor.subs(pole, 0) == 0
            ):
                factor = sp.cancel(factor / pole)
                divisor *= pole
    return factor, divisor


def prepare(a, parent_html):
    if (
        a.domain is None
        or a.strict_domain
        or (
            operands(a.original) is None
            and not (a.radical_product and a.radical_product.root_offset)
        )
    ):
        return a
    import re
    from dataclasses import replace
    from html import escape

    from bs4 import BeautifulSoup

    from .exam_trigonometric import select
    from .exam_trigonometric_parameters import affine_families
    from .exam_trigonometric_selection import equivalent_series

    parent_html = parent_html.replace(r"\dfrac", r"\frac")
    formulas = BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    source = ()
    for node in reversed(formulas):
        tail = re.split(r"\\(?:iff|Leftrightarrow)", node["data-inline-latex"])[-1]
        candidates = tuple(
            (q, p)
            for q, p, _ in affine_families(
                '<span data-inline-latex="' + escape(tail) + '"></span>'
            )
            if equivalent_series((*a.series, (q, p)), a.series)
        )
        if candidates and equivalent_series(candidates, a.series):
            source = candidates
            break
    if not source:
        declared_source = tuple(
            f for node in formulas for f in affine_families(str(node))
        )
        source = tuple(
            reversed(
                tuple(
                    dict.fromkeys(
                        (q, p)
                        for q, p, _ in reversed(declared_source)
                        if equivalent_series((*a.series, (q, p)), a.series)
                    )
                )
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
