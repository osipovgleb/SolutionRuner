"""Retain strict radical denominators and the parent's numerator reduction."""

import re
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T
from .power_arithmetic import balanced, clean


@dataclass(frozen=True)
class StrictQuotient:
    numerator_text: str
    radicand_text: str
    radicand: sp.Expr
    method: str
    stage: str
    variable: sp.Expr | None
    polynomial: sp.Expr


def operands(formula):
    text = clean(formula).removesuffix(".")
    if not text.startswith(r"\frac{"):
        return None
    numerator, end = balanced(text, 5)
    denominator, end = balanced(text, end)
    if not denominator.startswith(r"\sqrt{"):
        return None
    radicand, last = balanced(denominator, 5)
    if "x" not in radicand:
        return None
    if last != len(denominator) or text[end:] != "=0":
        return None
    return numerator, radicand


def method(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    forms = " ".join(
        clean(n["data-inline-latex"]).replace(r"\lt", "<").replace(r"\gt", ">")
        for n in soup.select("[data-inline-latex]")
    )
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    if any(
        s in text
        for s in (
            "другое решение",
            "ещё одно решение",
            "еще одно решение",
            "другим способом",
        )
    ):
        raise UnsupportedCondition(
            "an additional strict-denominator method needs review"
        )
    if re.search(r"(?<![A-Za-z])[tyuzv]=", forms):
        raise UnsupportedCondition(
            "a new substitution in a radical quotient needs review"
        )
    if r"\tg2x=" in forms and "числител" in text and r"2\cos^{2}x-1=\cos2x" in forms:
        return "tangent_double"
    if r"\sin^{2}x(" in forms and r"\sinx\cosx>0" in forms:
        return "grouping"
    if r"\sinx\ne1" in forms or r"-1<\sinx<0" in forms:
        return "quadratic"
    return None


def reviewed(formula, parent_html):
    return (
        r"\log_" not in formula
        and operands(formula) is not None
        and method(parent_html) is not None
    )


def stage(parent_html, kind):
    soup = BeautifulSoup(parent_html, "html.parser")
    images = soup.find_all("img")
    if not images:
        return "none"
    if len(images) != 1:
        raise UnsupportedCondition("one original strict-denominator circle is required")
    image = images[0]
    part = image.find_parent("li")
    forms = []
    for n in (part or soup).descendants:
        if n is image:
            break
        if getattr(n, "attrs", {}).get("data-inline-latex"):
            forms.append(clean(n["data-inline-latex"]))
    if part is None and not forms:
        return "outside"
    if part is None or part.get("data-list-marker") != "а)" or len(forms) != 1:
        raise UnsupportedCondition(
            "the original radical-quotient figure stage needs review"
        )
    if kind == "quadratic" and r"\tgx" in forms[0] and r"\ne0" in forms[0]:
        return "domain"
    if kind == "tangent_double" and forms[0] == r"2\cos^{2}x-1=\cos2x":
        return "double_identity"
    raise UnsupportedCondition(
        "the circle must retain its original domain or identity stage"
    )


def affine(radicand):
    return (
        radicand.free_symbols in ({S}, {C})
        and radicand.is_polynomial(S, C)
        and sp.Poly(radicand, S, C).total_degree() == 1
    )


def reduction(raw, domain, poles, kind):
    from .exam_trigonometric_log_variable_methods import quadratic
    from .exam_trigonometric_sine_double import linear_double

    if kind == "tangent_double":
        a, b = linear_double(raw)
        return T, sp.expand(b * T + a)
    if kind == "quadratic":
        return quadratic(raw)
    weight = sp.cancel(domain / (S * C))
    if weight.free_symbols or weight.is_positive is not True:
        raise UnsupportedCondition(
            "the grouping requires a strict positive sine/cosine product domain"
        )
    for variable, other in ((C, S), (S, C)):
        if variable not in poles:
            continue
        p = sp.rem(raw, S * S + C * C - 1, other)
        factor = sp.cancel(p / variable**2)
        if (
            factor.free_symbols == {variable}
            and factor.is_polynomial(variable)
            and sp.degree(factor, variable) == 1
        ):
            return variable, factor if sp.Poly(
                factor, variable
            ).LC().is_positive else -factor
    raise UnsupportedCondition(
        "the original pole must justify cancelling the complete square factor"
    )


def compile_quotient(formula, parent_html):
    from .exam_trigonometric_log_equality import original_text
    from .exam_trigonometric_methods import Equation, ExamAngleParser
    from .exam_trigonometric_radical_equation import compile_values

    numerator, text = operands(formula)
    kind = method(parent_html)
    atoms, denominators = {}, []
    values = [
        ExamAngleParser(p.replace("x", r"\alpha"), atoms, denominators).parse().value
        for p in (numerator, text)
    ]
    (raw, radicand), poles, identities = compile_values(values, atoms, denominators)
    if any(
        abs(a.coefficient) not in (1, 2) or (2 * a.shift).is_Integer is not True
        for a in atoms.values()
    ) or not set(poles) <= {S, C}:
        raise UnsupportedCondition(
            "strict quotients require first/double angles and original sine/cosine poles"
        )
    weights = (sp.cancel(radicand * C / S), sp.cancel(radicand * S / C))
    if not affine(radicand) and not any(
        not w.free_symbols and w.is_real is True and w != 0 for w in weights
    ):
        raise UnsupportedCondition(
            "one affine function or homogeneous tangent/cotangent radicand is required"
        )
    if not raw.is_polynomial(S, C) or not 1 <= sp.Poly(raw, S, C).total_degree() <= 4:
        raise UnsupportedCondition("one bounded polynomial numerator is required")
    num, den = sp.fraction(radicand)
    domain = sp.expand(num * den)
    variable, polynomial = reduction(raw, domain, poles, kind)
    data = StrictQuotient(
        original_text(numerator),
        original_text(text),
        radicand,
        kind,
        stage(parent_html, kind),
        variable,
        polynomial,
    )
    return Equation(
        raw,
        identities,
        sp.S.One,
        poles=poles,
        domain=domain,
        strict_domain=True,
        strict_quotient=data,
    )


def source_branches(compiled, allow_inverse):
    from .exam_trigonometric_inverse import ordered
    from .exam_trigonometric_radical_product import factor_branches
    from .exam_trigonometric_ratios import ratio_branch

    d = compiled.strict_quotient
    if d.method != "tangent_double":
        return factor_branches(d.polynomial, d.variable, allow_inverse)
    _, source = ratio_branch(d.polynomial, T)
    return tuple(
        replace(
            b,
            residues=ordered((q + 2 * k) / 2 for q in b.residues for k in range(2)),
            angle_scale=sp.Integer(2),
            original=compiled.raw,
        )
        for b in source
    )


def branches(compiled, allow_inverse):
    from .exam_trigonometric_domain import restrict, without_poles

    return without_poles(
        restrict(
            source_branches(compiled, allow_inverse), compiled.domain, strict=True
        ),
        compiled.poles,
    )
