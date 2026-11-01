"""Certify original ratio poles before cancellation or difference-of-squares cases."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .power_arithmetic import clean


@dataclass(frozen=True)
class OriginalQuotient:
    method: str
    left: sp.Expr
    right: sp.Expr
    numerator: sp.Expr
    denominator: sp.Expr
    divide: sp.Expr
    variable: sp.Expr | None
    polynomial: sp.Expr
    stage: str
    source_right: sp.Expr
    half: tuple = ()
    square: sp.Expr | None = None


def method(parent):
    soup = BeautifulSoup(parent, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    forms = " ".join(
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    )
    if "сокращать" in text and "правую часть" in text and r"\sinx\ne0" in forms:
        return "cancel_ratio"
    if "приравнять числители" in text and r"\sin^{4}" in forms and r"\cos^{4}" in forms:
        return "half_fourth"
    if r"\cos^22x-\sin^2x" in forms and r"\cos2x\ne0" in forms:
        return "double_square"
    return None


def reviewed(formula, parent):
    return (r"\tg" in formula or r"\operatorname{tg}" in clean(formula)) and method(
        parent
    ) is not None


def stage(parent):
    soup = BeautifulSoup(parent, "html.parser")
    images = soup.find_all("img")
    if len(images) != 1:
        raise UnsupportedCondition("one original quotient figure is required")
    image = images[0]
    part = image.find_parent("li")
    preceding = []
    for n in (part or soup).descendants:
        if n is image:
            break
        if getattr(n, "attrs", {}).get("data-inline-latex"):
            preceding.append(n)
    if preceding:
        raise UnsupportedCondition("the original quotient figure stage needs review")
    if part is None:
        return "outside"
    if part.get("data-list-marker") not in ("а)", "a)"):
        raise UnsupportedCondition("the quotient figure must precede the first subpart")
    return "before-intro"


def nonzero(variable, poles):
    return any(
        p.is_polynomial(S, C) and sp.Poly(p, S, C).length() == 1 and p.has(variable)
        for p in poles
    )


def reduce_fraction(value):
    numerator, denominator = sp.fraction(sp.cancel(value))
    return sp.cancel(sp.rem(numerator, S * S + C * C - 1, C) / denominator)


def half_fourth(values, atoms, denominators):
    from .exam_trigonometric_radical_equation import compile_values

    parts = [sp.fraction(v) for v in values]
    if not all(d in atoms for _, d in parts):
        raise UnsupportedCondition(
            "both sides must have the same original unit tangent denominator"
        )
    ratios = [atoms[d] for _, d in parts]
    if any(a.function != "tg" or a.coefficient != 1 or a.shift != 0 for a in ratios):
        raise UnsupportedCondition(
            "one common unshifted tangent denominator is required"
        )
    half = {
        a.function: (symbol, a)
        for symbol, a in atoms.items()
        if a.coefficient == sp.Rational(1, 2)
    }
    if set(half) != {"sin", "cos"} or any(a.shift != 0 for _, a in half.values()):
        raise UnsupportedCondition(
            "one matching unshifted half-angle fourth-power pair is required"
        )
    sine, cosine = half["sin"][0], half["cos"][0]
    weight = sp.cancel(parts[1][0] / (sine**4 - cosine**4))
    if weight.free_symbols or weight == 0:
        raise UnsupportedCondition(
            "the original numerator must be a complete fourth-power difference"
        )
    converted, poles, identities = compile_values(
        [v for v, _ in parts], atoms, denominators
    )
    if converted[1] != -weight * C:
        raise UnsupportedCondition(
            "the fourth-power identity must equal minus the doubled cosine"
        )
    return (
        converted,
        poles,
        identities,
        (
            half["sin"][1].text.replace(r"\alpha", "x"),
            half["cos"][1].text.replace(r"\alpha", "x"),
            weight,
        ),
    )


def division(numerator, poles):
    for variable, other in ((S, C), (C, S)):
        if not nonzero(variable, poles):
            continue
        polynomial = sp.cancel(numerator / variable)
        if (
            polynomial.is_polynomial(other)
            and polynomial.free_symbols == {other}
            and sp.degree(polynomial, other) == 1
        ):
            return variable, other, polynomial
    raise UnsupportedCondition(
        "only an original nonzero function may be cancelled before the linear case"
    )


def review_parent(parent):
    text = (
        BeautifulSoup(parent, "html.parser").get_text(" ").replace("\xad", "").lower()
    )
    if any(
        t in text
        for t in (
            "другое решение",
            "другим способом",
            "ещё одно решение",
            "еще одно решение",
        )
    ):
        raise UnsupportedCondition("an additional quotient method needs review")
    forms = " ".join(
        "".join(n["data-inline-latex"].split())
        for n in BeautifulSoup(parent, "html.parser").select("[data-inline-latex]")
    )
    if re.search(r"(?<![A-Za-z])[tyuzv]=", forms):
        raise UnsupportedCondition(
            "a new substitution in an original quotient needs review"
        )


def compile_quotient(formula, parent):
    from .exam_trigonometric_methods import Equation, parse_equation
    from .exam_trigonometric_radical_equation import compile_values

    kind = method(parent)
    values, atoms, denominators = parse_equation(formula)
    if not kind or any(
        abs(a.coefficient) not in (sp.Rational(1, 2), 1, 2)
        or (2 * a.shift).is_Integer is not True
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "a reviewed original quotient method with bounded angles is required"
        )
    review_parent(parent)
    half = ()
    if kind == "half_fourth":
        (left, right), poles, identities, half = half_fourth(
            values, atoms, denominators
        )
    else:
        (left, right), poles, identities = compile_values(values, atoms, denominators)
    if not poles or any(
        not p.is_polynomial(S, C) or sp.Poly(p, S, C).total_degree() > 2 for p in poles
    ):
        raise UnsupportedCondition(
            "the original quotient poles must be bounded function polynomials"
        )
    square = None
    source_right = right
    if kind == "cancel_ratio":
        left, right = map(reduce_fraction, (left, right))
        weight = sp.cancel(right * C / S)
        if weight.free_symbols or weight == 0:
            raise UnsupportedCondition(
                "the right fraction must reduce to a homogeneous unit tangent"
            )
    numerator, denominator = map(sp.expand, sp.fraction(sp.cancel(left - right)))
    if kind == "double_square":
        doubled = 2 * C * C - 1
        weight = sp.cancel(right * S / (doubled * C))
        if (
            weight.free_symbols
            or weight.is_positive is not True
            or sp.cancel(left - 2 * S * C / doubled) != 0
        ):
            raise UnsupportedCondition(
                "the double-angle ratio must yield a complete difference of squares"
            )
        square = sp.sqrt(2 / weight)
        factor = C * (doubled**2 - square**2 * S * S)
        if sp.cancel(numerator / factor).free_symbols:
            raise UnsupportedCondition(
                "the zero cosine case must be retained in the factor product"
            )
        divide, variable, polynomial = sp.S.One, None, numerator
    else:
        divide, variable, polynomial = division(numerator, poles)
    data = OriginalQuotient(
        kind,
        left,
        right,
        numerator,
        denominator,
        divide,
        variable,
        polynomial,
        stage(parent),
        source_right,
        half,
        square,
    )
    return Equation(
        numerator, identities, sp.S.One, poles=poles, original_quotient=data
    )


def source_branches(data, allow_inverse):
    from .exam_trigonometric_radical_product import factor_branches

    if data.method != "double_square":
        return factor_branches(data.polynomial, data.variable, allow_inverse)
    result = factor_branches(C, C, allow_inverse)
    for sign in (-1, 1):
        result += factor_branches(
            2 * S * S - sign * data.square * S - 1, S, allow_inverse
        )
    return result


def branches(compiled, allow_inverse):
    from .exam_trigonometric_domain import without_poles

    return without_poles(
        source_branches(compiled.original_quotient, allow_inverse), compiled.poles
    )


def series(data, branches):
    from .exam_trigonometric_inverse import centred
    from .exam_trigonometric_selection import periodic, restricted_series

    if data.method != "double_square":
        return centred(tuple(s for b in branches for s in restricted_series(b)))
    first = set(branches[0].residues)
    others = {q for b in branches[1:] for q in b.residues} - first
    rest = tuple((q - p if q > p / 2 else q, p) for q, p in periodic(others))
    return (*periodic(first), *rest)


def validate_circle(entry, a):
    from .exam_trigonometric_inverse import decode

    if "original_quotient_domain" in entry:
        data = a.original_quotient
        expected = (
            {
                "poles": list(map(str, a.poles)),
                "method": data.method,
                "figure_stage": data.stage,
            }
            if data is not None
            else None
        )
        if entry["original_quotient_domain"] != expected:
            raise UnsupportedCondition(
                "the source figure must retain the original quotient poles and method"
            )
    if entry.get("unselected_root_markers"):
        from .exam_trigonometric_inverse import turn

        selected = {turn(q) for q in a.selected}
        for point in entry["unselected_root_markers"]:
            q = decode(point["angle"])
            if (
                entry.get("point_scope") != "selected"
                or q not in a.residues
                or q in selected
            ):
                raise UnsupportedCondition(
                    "an open unselected point must be a valid root outside selection"
                )
