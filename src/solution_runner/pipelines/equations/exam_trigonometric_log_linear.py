"""Combine two affine fixed-base logs, retaining both original positive arguments."""

import re
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_log_equality import LogEquality, original_text, presentation
from .exam_trigonometric_log_parser import Parser
from .logarithm_arithmetic import log_ratio, power
from .power_arithmetic import clean


@dataclass(frozen=True)
class LinearLogs:
    bases: tuple
    multipliers: tuple
    common: sp.Expr
    sign: int
    level: sp.Expr
    implication: bool
    domain_first: bool
    projection: sp.Expr | None
    product_identity: tuple
    image_after_candidates: bool


def log_texts(nodes):
    result = []
    for n in nodes:
        if n.kind == "log":
            result.append(original_text(n.text))
        else:
            result.extend(log_texts(n.children))
    return tuple(result)


def affine_expression(nodes, logs):
    symbols = tuple(e[0] for e in logs)
    value = sp.expand(nodes[0].value - nodes[1].value)
    if (
        value.free_symbols - set(symbols)
        or not value.is_polynomial(*symbols)
        or sp.Poly(value, *symbols).total_degree() != 1
    ):
        return None
    return value


def coefficients(value, logs):
    symbols = tuple(e[0] for e in logs)
    weights = tuple(value.coeff(s) for s in symbols)
    multipliers = tuple(log_ratio(e[1], logs[0][1]) for e in logs)
    if any(
        v.is_Rational is not True or v == 0 or abs(v) > 12 or v.q > 12
        for v in (*weights, *multipliers)
    ):
        raise UnsupportedCondition(
            "bounded nonzero rational log weights and base ratios are required"
        )
    common = weights[0] * multipliers[0]
    sign = sp.cancel(weights[1] * multipliers[1] / common)
    level = sp.cancel(-value.subs(dict.fromkeys(symbols, 0)) / common)
    if (
        sign not in (-1, 1)
        or level.is_Rational is not True
        or abs(level) > 20
        or level.q > 12
    ):
        raise UnsupportedCondition(
            "two equal-magnitude log weights and one bounded rational level are required"
        )
    return multipliers, common, int(sign), level


def product_identity(logs, atoms):
    if any(e[2] not in atoms for e in logs):
        return ()
    first, second = (atoms[e[2]] for e in logs)
    if any(a.function != "sin" or a.coefficient != 1 for a in (first, second)):
        return ()
    delta = (first.shift - second.shift) * sp.pi
    total = 2 * X + (first.shift + second.shift) * sp.pi
    product = (
        r"\frac12\left(\cos\left("
        + sp.latex(delta)
        + r"\right)-\cos\left("
        + sp.latex(total)
        + r"\right)\right)"
    )
    y = sp.Symbol("y", real=True)
    shifted = sp.expand_trig(sp.cos(y + (first.shift + second.shift) * sp.pi)).subs(
        y, 2 * X
    )
    return (
        product,
        r"\cos\left(" + sp.latex(delta) + r"\right)=" + sp.latex(sp.cos(delta)),
        r"\cos\left(" + sp.latex(total) + r"\right)=" + sp.latex(shifted),
    )


def division(raw, other, sign):
    if sign == -1:
        for variable in (S, C):
            coefficient = sp.cancel(other / variable)
            reduced = sp.rem(raw, S * S + C * C - 1, C if variable == S else S)
            if (
                not coefficient.free_symbols
                and coefficient.is_real is True
                and coefficient != 0
                and reduced.subs(variable, 0) == 0
            ):
                return variable, sp.expand(reduced)
    return sp.S.One, raw


def circle_reduction(arguments, poles, base, sign, level):
    first, second = arguments
    target = power(base, level)
    raw = sp.expand(first * second - target if sign == 1 else first - target * second)
    if (
        not set(poles) <= {S, C}
        or any(
            a.free_symbols - {S, C}
            or not a.is_polynomial(S, C)
            or not 1 <= sp.Poly(a, S, C).total_degree() <= 2
            for a in arguments
        )
        or not raw.is_polynomial(S, C)
        or not 1 <= sp.Poly(raw, S, C).total_degree() <= 2
        or not sp.rem(raw, S * S + C * C - 1, S).free_symbols
    ):
        raise UnsupportedCondition(
            "two nonconstant polynomial log arguments and a quadratic circle reduction are required"
        )
    divisor, factor = division(raw, second, sign)
    if sign == -1 and divisor == 1:
        raise UnsupportedCondition(
            "the reviewed log difference needs a nonzero original sine/cosine factor"
        )
    return raw, divisor, factor


def review_parent(parent_html, sign):
    soup = BeautifulSoup(parent_html, "html.parser")
    forms = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    parent = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    if not forms or r"\log_" not in " ".join(forms):
        raise UnsupportedCondition(
            "the parent must show the reviewed combination of logarithms"
        )
    if any(re.search(r"(?<![A-Za-z])[tyuzv]\s*=", f) for f in forms):
        raise UnsupportedCondition(
            "an additional parent substitution needs its own reviewed steps"
        )
    implication = any(r"\Rightarrow" in f for f in forms)
    domain_first = "уравнение определено" in parent
    if sign == 1 and not (implication or domain_first):
        raise UnsupportedCondition(
            "a log product needs the parent's implication check or original domain first"
        )
    _, after = presentation(parent_html)
    if after and not implication:
        raise UnsupportedCondition(
            "this figure stage requires the reviewed implication and candidate check"
        )
    if after:
        preceding = []
        for n in soup.img.find_parent("li").descendants:
            if n is soup.img:
                break
            if getattr(n, "attrs", {}).get("data-inline-latex"):
                preceding.append(n["data-inline-latex"])
        if not preceding or clean(preceding[-1]).replace("&=", "=").count("x=") < 2:
            raise UnsupportedCondition(
                "the source figure must follow the candidate families before domain checking"
            )
    return implication, domain_first, after


def compile_linear(formula, parent_html):
    from .exam_trigonometric_log_product import LogProduct
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_radical_equation import compile_values
    from .exam_trigonometric_sine_double import project

    text = clean(formula).removesuffix(".")
    if text.count(r"\log_") != 2 or text.count("=") != 1:
        return None
    atoms, denominators, logs = {}, [], []
    nodes = tuple(
        Parser(p.replace("x", r"\alpha"), atoms, denominators, logs).parse()
        for p in text.split("=")
    )
    if len(logs) != 2:
        return None
    if all(n.kind == "log" for n in nodes) and logs[0][1] == logs[1][1]:
        return None
    value = affine_expression(nodes, logs)
    if value is None:
        return None
    arguments, poles, identities = compile_values(
        [e[2] for e in logs],
        atoms,
        denominators,
        extra_symbols=tuple(e[0] for e in logs),
    )
    if len({(e[1], a) for e, a in zip(logs, arguments, strict=True)}) == 1:
        return None
    if any(
        a.coefficient.is_Integer is not True or abs(a.coefficient) > 12
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "the original log arguments need bounded integer-angle periodicity"
        )
    multipliers, common, sign, level = coefficients(value, logs)
    first, second = arguments
    raw, divisor, factor = circle_reduction(arguments, poles, logs[0][1], sign, level)
    implication, domain_first, after = review_parent(parent_html, sign)
    texts = log_texts(nodes)
    if len(texts) != 2:
        raise UnsupportedCondition(
            "two identifiable original log arguments are required"
        )
    data = LogProduct(
        factor,
        logs[0][1],
        first,
        None,
        divide=divisor,
        equality=LogEquality(
            "linear_logs",
            level,
            second,
            texts[0],
            texts[1],
            linear=LinearLogs(
                tuple(e[1] for e in logs),
                multipliers,
                common,
                sign,
                level,
                implication,
                domain_first,
                project(sp.cancel(factor / divisor)),
                product_identity(logs, atoms) if sign == 1 else (),
                after,
            ),
        ),
    )
    return Equation(raw, identities, sp.S.One, poles=poles, log_product=data)


def branches(compiled, preferred, allow_inverse):
    from .exam_trigonometric_inverse import ordered
    from .exam_trigonometric_radical_product import factor_branches

    data = compiled.log_product
    projected = data.equality.linear.projection
    if projected is None:
        return factor_branches(
            sp.cancel(data.factor / data.divide), preferred, allow_inverse
        )
    return tuple(
        replace(
            b,
            residues=ordered((q + 2 * k) / 2 for q in b.residues for k in range(2)),
            angle_scale=sp.Integer(2),
            original=data.factor,
        )
        for b in factor_branches(projected, S, allow_inverse)
    )
