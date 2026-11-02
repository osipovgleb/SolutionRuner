"""Certify equality of two complete square roots with both original domains."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_absolute import R, side
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation, ExamAngleParser
from .exam_trigonometric_power_equality import parent_equations
from .exam_trigonometric_radical_equation import CIRCLE, RadicalEquation, compile_values
from .power_arithmetic import clean


def compile_equality(formula):
    text = clean(formula).removesuffix(".")
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete equality of square roots is required")
    plain = re.sub(r"\\[A-Za-z]+", "", text).replace("x", "")
    if re.search("[A-Za-z]", plain) or re.search(r"\\(?:alpha|beta|gamma)", text):
        raise UnsupportedCondition("the original square roots may contain only x")
    atoms, denominators, radicands = {}, [], []
    for part in text.split("="):
        value, radicand = side(part, atoms, denominators)
        if value != R:
            raise UnsupportedCondition(
                "each side must be one complete unscaled square root"
            )
        radicands.append(radicand)
    if not atoms or any(
        a.variable != r"\alpha" or a.coefficient != 1 or a.shift != 0
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "original unit unshifted trig arguments are required"
        )
    (left, right), poles, identities = compile_values(radicands, atoms, denominators)
    if poles or any(
        not v.is_polynomial(S, C) or sp.Poly(v, S, C).total_degree() > 2
        for v in (left, right)
    ):
        raise UnsupportedCondition(
            "two quadratic unit-circle radicands without poles are required"
        )
    squared = sp.expand(left - right)
    for variable, other in ((S, C), (C, S)):
        raw = sp.expand(sp.rem(squared, CIRCLE, other))
        if not raw.has(other) and sp.degree(raw, variable) in (1, 2):
            break
    else:
        raise UnsupportedCondition(
            "a finite nonconstant quadratic equation in one trig variable is required"
        )
    target = sp.sqrt(right)
    data = RadicalEquation(
        sp.S.One,
        left,
        target,
        squared,
        target,
        (left, right),
        "equal_roots",
        right_radicand=right,
    )
    return Equation(raw, identities, sp.S.One, radical_equation=data)


def reviewed_parent(html):
    soup = BeautifulSoup(html, "html.parser")
    forms = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    text = soup.get_text(" ").replace("\xad", "").lower()
    if any(
        re.search(r"(?<![A-Za-z])[tyuzv]=", "".join(f.split())) for f in forms
    ) or any(
        token in text
        for token in ("случа", "полный квадрат", "другое решение", "другим способом")
    ):
        return False
    for equation in parent_equations(forms):
        if equation.count(r"\sqrt{") < 2:
            continue
        try:
            compiled = compile_equality(equation)
        except UnsupportedCondition:
            continue
        radicand = compiled.radical_equation.right_radicand
        for form in forms:
            for part in re.split(
                r"\\(?:iff|Leftrightarrow)|\\(?:begin|end)\{cases\}|\\\\",
                form.replace("&", ""),
            ):
                if r"\ge" not in part:
                    continue
                atoms, denominators = {}, []
                try:
                    match = re.fullmatch(
                        r"([^=]+)\\ge([^=]+)", clean(part).strip(".,;")
                    )
                    if not match:
                        continue
                    values = [
                        ExamAngleParser(v.replace("x", r"\alpha"), atoms, denominators)
                        .parse()
                        .value
                        for v in match.groups()
                    ]
                    (first, second), poles, _ = compile_values(
                        values, atoms, denominators
                    )
                except UnsupportedCondition:
                    continue
                weight = sp.cancel((first - second) / radicand)
                if not poles and not weight.free_symbols and weight.is_positive is True:
                    return True
    return False
