"""Certify the parent's order, nonzero log bound and original multiple-angle factor."""

import re
from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S
from .power_arithmetic import ScalarParser, clean


def upper_bound(argument):
    if argument is None or argument.free_symbols not in ({S}, {C}):
        raise UnsupportedCondition(
            "the nonzero log proof needs one affine sine/cosine argument"
        )
    variable = next(iter(argument.free_symbols))
    if not argument.is_polynomial(variable) or sp.degree(argument, variable) != 1:
        raise UnsupportedCondition(
            "an affine argument is required for the reviewed maximum"
        )
    maximum = sp.simplify(abs(argument.coeff(variable)) + argument.subs(variable, 0))
    if maximum.is_positive is not True or (1 - maximum).is_positive is not True:
        raise UnsupportedCondition(
            "the complete positive argument must stay strictly below one"
        )
    return maximum


def double_factor(compiled, formulas):
    data = compiled.log_product
    matches = [
        m for f in formulas for m in re.findall(r"\\sin(\d+)x\(\\cos\1x[+-]", clean(f))
    ]
    if not matches:
        return None
    if len(set(matches)) != 1:
        raise UnsupportedCondition("one reviewed multiple-angle factor is required")
    multiple = sp.Integer(matches[0])
    sine, cosine = None, None
    for text, value in compiled.identities:
        if clean(text) == r"\sin(" + str(multiple) + "x)":
            sine = value
        if clean(text) == r"\cos(" + str(multiple) + "x)":
            cosine = value
    if sine is None or cosine is None:
        raise UnsupportedCondition(
            "the numerator must retain both original angle functions"
        )
    residual = sp.cancel(data.factor / sine - cosine)
    num, den = sp.fraction(residual)
    constant = sp.cancel(
        sp.rem(num, S * S + C * C - 1, S) / sp.rem(den, S * S + C * C - 1, S)
    )
    if constant.free_symbols or (abs(constant) - 1).is_positive is not True:
        raise UnsupportedCondition(
            "the remaining cosine factor must be provably nonzero on the circle"
        )
    return multiple, constant


def level_order(formulas):
    values = {"sin": [], "cos": []}
    for formula in formulas:
        text = clean(formula)
        for match in re.finditer(r"\\(sin|cos)x&?=", text):
            right = re.split(
                r"\\\\|\\(?:end|quad|iff|Leftrightarrow)|,",
                text[match.end() :],
                maxsplit=1,
            )[0].removesuffix(".")
            try:
                value = ScalarParser(right).parse()
            except UnsupportedCondition:
                continue
            if (
                not value.free_symbols
                and value.is_real is True
                and value not in values[match[1]]
            ):
                values[match[1]].append(value)
    pair = next((v for v in values.values() if len(v) >= 2), None)
    return compare(pair[0], pair[1]) < 0 if pair else None


def prepare(compiled, parent_html):
    data = compiled.log_product
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    first = any(f.strip().startswith(r"\log_") and "=0" in f for f in formulas)
    bound = (
        upper_bound(data.argument) if "наибольшее значение аргумента" in text else None
    )
    doubled = double_factor(compiled, formulas)
    if first and data.argument is None:
        raise UnsupportedCondition(
            "a denominator-only log has no numerator-log zero case"
        )
    domain = r"\begin{cases}" in parent_html or any(
        word in text
        for word in ("определено", "область", "аргумент", "имеет смысл", "при условиях")
    )
    if not domain or not (
        r"\left[" in parent_html or first or bound is not None or doubled
    ):
        raise UnsupportedCondition(
            "the parent must show its reviewed zero cases and original domain"
        )
    images = soup.find_all("img")
    second_part = images[1].find_parent("li") if len(images) == 2 else None
    if len(images) == 2 and second_part is None:
        raise UnsupportedCondition("the second source figure needs an explicit subpart")
    selection_position = (
        "after-steps"
        if second_part is not None and second_part.get("data-list-marker") == "а)"
        else "selection"
    )
    data = replace(
        data,
        log_first=first,
        nonzero_bound=bound,
        double_angle=doubled,
        selection_image_position=selection_position,
        level_ascending=level_order(formulas),
        domain_labels="(*)" in parent_html and "(**)" in parent_html,
    )
    if "разделить обе части уравнения на" in text:
        for pole in compiled.poles:
            if data.factor.is_polynomial(pole) and data.factor.subs(pole, 0) == 0:
                return replace(compiled, log_product=replace(data, divide=pole))
        raise UnsupportedCondition(
            "the parent's division needs an original nonzero factor"
        )
    return replace(compiled, log_product=data)
