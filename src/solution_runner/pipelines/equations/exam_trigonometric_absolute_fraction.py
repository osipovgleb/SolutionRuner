"""Keep both strict sign cases of an absolute sine denominator."""

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_absolute import R, RootPlaceholderParser
from .exam_trigonometric_compile import C, S
from .power_arithmetic import clean


def reviewed(html):
    text = " ".join(
        BeautifulSoup(html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
        .split()
    )
    return "рассмотрим оба случая" in text and "дробь" in text and "1 или −1" in text


def compile_fraction(formula):
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_poles import compile_atoms

    text = clean(formula)
    if text.count("|") != 2 or text.count("=") != 1:
        raise UnsupportedCondition(
            "one absolute denominator and one complete equality are required"
        )
    start, end = (i for i, c in enumerate(text) if c == "|")
    argument = text[start + 1 : end]
    body = text[:start] + "r" + text[end + 1 :]
    atoms, denominators = {}, []
    values = [
        RootPlaceholderParser(part.replace("x", r"\alpha"), atoms, denominators)
        .parse()
        .value
        for part in body.split("=")
    ]
    domain = (
        RootPlaceholderParser(argument.replace("x", r"\alpha"), atoms, denominators)
        .parse()
        .value
    )
    if any(d.free_symbols and d.free_symbols != {R} for d in denominators):
        raise UnsupportedCondition("no additional variable denominator is reviewed")
    compiled, poles = compile_atoms(atoms)
    if poles:
        raise UnsupportedCondition(
            "the absolute fraction requires sine/cosine functions only"
        )
    numerator = sp.cancel(values[0].xreplace(compiled) * R)
    right = sp.cancel(values[1].xreplace(compiled))
    domain = sp.expand(domain.xreplace(compiled))
    if (
        numerator.free_symbols - {S, C}
        or right.free_symbols
        or not numerator.is_polynomial(S, C)
        or sp.Poly(numerator, S, C).total_degree() > 8
    ):
        raise UnsupportedCondition(
            "a bounded polynomial numerator divided by the sole absolute sine is required"
        )
    for scale, sine, cosine in ((1, S, C), (2, 2 * S * C, C * C - S * S)):
        multiplier = sp.cancel(domain / sine)
        if multiplier.free_symbols or multiplier == 0:
            continue
        weight = sp.cancel(numerator / (sine * cosine))
        if weight.is_polynomial(S, C):
            weight = sp.expand(sp.rem(weight, S * S + C * C - 1, S))
        if weight.free_symbols or weight.is_real is not True or weight == 0:
            continue
        level = sp.simplify(right * abs(multiplier) / weight)
        if level.is_real is not True or not 0 < abs(level) < 1:
            continue
        return Equation(
            C * C - level * level,
            (),
            sp.Integer(scale),
            poles=(S,),
            domain=level * S * C,
            strict_domain=True,
            absolute_fraction=(numerator, domain, weight, multiplier, level),
        )
    raise UnsupportedCondition(
        "the numerator and absolute pole must have the exact sine-cosine double-angle certificate"
    )


def proof(a):
    from .exam_trigonometric_proof import families, formula
    from .exam_trigonometric_variants import argument

    numerator, domain, weight, _multiplier, level = a.absolute_fraction
    angle = argument(a.scale)
    html = line(a.original)
    html += "<p>Исходный знаменатель должен быть ненулевым. Преобразуем числитель по формулам кратных углов:</p>"
    html += line(formula(domain) + r"\ne0")
    html += line(
        formula(numerator) + "=" + sp.latex(weight) + r"\," + formula(S * C, angle)
    )
    html += line(formula(S, angle) + r"\ne0")
    html += line(
        r"\frac{"
        + formula(S, angle)
        + "}{"
        + r"\left|"
        + formula(S, angle)
        + r"\right|}"
        + formula(C, angle)
        + "="
        + sp.latex(level)
    )
    html += "<p>Дробь равна 1 или −1. Рассмотрим оба строгих случая:</p>"
    for sign in (1, -1):
        html += line(formula(S, angle) + (">0" if sign == 1 else "<0"))
        html += line(formula(C, angle) + "=" + sp.latex(sign * level))
        for i, (q, p) in enumerate(a.series):
            value = sp.simplify(sp.sin(a.scale * q * sp.pi))
            if sp.sign(value) != sign:
                continue
            name = a.family_parameters[i] if a.family_parameters else "k"
            text = families(a)[i]
            html += line(text + r",\quad " + name + r"\in\mathbb Z")
    return "<p>Сохраним знак синуса при раскрытии модуля знаменателя:</p>", html
