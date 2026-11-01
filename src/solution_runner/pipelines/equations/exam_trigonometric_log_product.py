"""Solve the two zero factors, checking every original logarithm and ratio pole."""

from dataclasses import dataclass, replace

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T, U
from .power_arithmetic import clean


@dataclass(frozen=True)
class LogProduct:
    factor: sp.Expr
    base: sp.Expr
    argument: sp.Expr
    denominator: tuple | None
    divide: sp.Expr = sp.S.One


def compile_product(formula):
    from .exam_trigonometric_log_parser import Parser
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_radical_equation import compile_values

    text = clean(formula).removesuffix(".")
    if text.count("=") != 1 or not text.endswith("=0"):
        raise UnsupportedCondition("a complete log-factor product must equal zero")
    atoms, denominators, logs = {}, [], []
    value = (
        Parser(text[:-2].replace("x", r"\alpha"), atoms, denominators, logs)
        .parse()
        .value
    )
    if not logs:
        raise UnsupportedCondition("a variable logarithm factor is required")
    symbols = tuple(item[0] for item in logs)
    values, poles, identities = compile_values(
        [value, *(item[2] for item in logs)], atoms, denominators, extra_symbols=symbols
    )
    value, *arguments = values
    numerator, denominator = sp.fraction(value)
    upstairs = [v for v in symbols if numerator.has(v)]
    downstairs = [v for v in symbols if denominator.has(v)]
    if len(upstairs) != 1 or len(downstairs) != len(logs) - 1:
        raise UnsupportedCondition(
            "one numerator log and at most one denominator log are required"
        )
    log = upstairs[0]
    den_log = downstairs[0] if downstairs else sp.S.One
    factor = sp.cancel(value * den_log / log)
    if factor.free_symbols - {S, C} or any(
        p.has(*symbols) and p != den_log for p in poles
    ):
        raise UnsupportedCondition(
            "uncancelled log powers or extra log denominators are unsupported"
        )
    poles = tuple(p for p in poles if not p.has(*symbols))
    if not set(poles) <= {S, C}:
        raise UnsupportedCondition(
            "log products retain only original sine/cosine ratio poles"
        )
    if any(not argument.free_symbols for argument in arguments):
        raise UnsupportedCondition(
            "a log argument must remain nonconstant on compilation"
        )
    for expression in (factor, *arguments):
        num, den = sp.fraction(expression)
        if (
            not num.is_polynomial(S, C)
            or sp.Poly(num, S, C).total_degree() > 4
            or not den.is_polynomial(S, C)
            or sp.Poly(den, S, C).total_degree() > 2
        ):
            raise UnsupportedCondition(
                "bounded rational unit-circle log factors are required"
            )
        circle = S * S + C * C - 1
        reduced_den = sp.rem(den, circle, S)
        if (
            reduced_den == 0
            or not sp.cancel(sp.rem(num, circle, S) / reduced_den).free_symbols
        ):
            raise UnsupportedCondition(
                "a constant unit-circle factor requires a complete-domain method"
            )
    if factor == 0 or not factor.free_symbols:
        raise UnsupportedCondition("a nonconstant nonzero algebraic factor is required")
    index = symbols.index(log)
    other = symbols.index(den_log) if downstairs else None
    data = LogProduct(
        factor,
        logs[index][1],
        arguments[index],
        (logs[other][1], arguments[other]) if other is not None else None,
    )
    raw = sp.expand(sp.fraction(factor)[0] * sp.fraction(data.argument - 1)[0])
    return Equation(raw, identities, sp.S.One, poles=poles, log_product=data)


def conditions(compiled):
    data = compiled.log_product
    result = [(p, "nonzero") for p in compiled.poles]
    result.append((data.argument, "positive"))
    if data.denominator:
        argument = data.denominator[1]
        result.extend(((argument, "positive"), (argument - 1, "nonzero")))
    return tuple(result)


def failed(compiled, q):
    substitution = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
    for expression, relation in conditions(compiled):
        value = sp.simplify(expression.subs(substitution))
        if value.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
            return expression, relation, value
        sign = compare(value, sp.S.Zero)
        if (relation == "positive" and sign <= 0) or (
            relation == "nonzero" and sign == 0
        ):
            return expression, relation, value
    return None


def ratio_factor(value):
    value = sp.cancel(value)
    if sp.fraction(value)[1].has(C):
        ratio = sp.cancel(value.subs(S, T * C))
        if ratio.free_symbols == {T}:
            return ratio
    if sp.fraction(value)[1].has(S):
        ratio = sp.cancel(value.subs(C, U * S))
        if ratio.free_symbols == {U}:
            return ratio
    return sp.fraction(value)[0]


def branches(compiled, preferred, allow_inverse=False):
    from .exam_trigonometric_radical_product import factor_branches

    data = compiled.log_product
    result = []
    for factor in (
        ratio_factor(data.factor / data.divide),
        ratio_factor(data.argument - 1),
    ):
        for b in factor_branches(factor, preferred, allow_inverse):
            residues = tuple(q for q in b.residues if failed(compiled, q) is None)
            result.append(replace(b, residues=residues))
    return tuple(result)


def prepare(compiled, parent_html):
    from bs4 import BeautifulSoup

    data = compiled.log_product
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    if "наибольшее значение аргумента" in text or any(
        f.strip().startswith(r"\log_") and "=0" in f for f in formulas
    ):
        raise UnsupportedCondition(
            "a different parent log-case order or nonzero bound needs its own proof"
        )
    if r"\left[" not in parent_html or not (
        r"\log_" in parent_html or r"\begin{cases}" in parent_html
    ):
        raise UnsupportedCondition(
            "the parent must show the reviewed zero-factor cases and domain"
        )
    if "разделить обе части уравнения на" in text:
        for pole in compiled.poles:
            if data.factor.is_polynomial(pole) and data.factor.subs(pole, 0) == 0:
                return replace(compiled, log_product=replace(data, divide=pole))
        raise UnsupportedCondition(
            "the parent's division needs an original nonzero factor"
        )
    return compiled
