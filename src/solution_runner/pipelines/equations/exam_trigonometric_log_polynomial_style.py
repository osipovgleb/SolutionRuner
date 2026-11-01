"""Read only the parent's substitution, branch order and alternate selection method."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_log_parent import small_fractions
from .exam_trigonometric_log_parser import Parser
from .power_arithmetic import ScalarParser, clean


def declared_levels(formulas):
    levels, substitution = [], None
    for formula in formulas:
        text = clean(small_fractions(formula))
        for match in re.finditer(r"\\log_", text):
            logs = []
            parser = Parser(text[match.start() :].replace("x", r"\alpha"), {}, [], logs)
            try:
                node = parser._primary()
            except UnsupportedCondition:
                continue
            if len(logs) != 1 or node.value != logs[0][0]:
                continue
            before, after = text[: match.start()], parser.text[parser.index :]
            name = re.search(r"([tyuz])=$", before) or re.match(
                r"=([tyuz])(?:$|\\)", after
            )
            if name:
                if substitution is not None and substitution != name[1]:
                    raise UnsupportedCondition(
                        "one reviewed log substitution is required"
                    )
                substitution = name[1]
            if after.startswith("&="):
                after = after[1:]
            if not after.startswith("="):
                continue
            right = re.split(
                r"\\\\|\\(?:end|iff|Leftrightarrow|quad)|,", after[1:], maxsplit=1
            )[0].removesuffix(".")
            try:
                value = ScalarParser(right).parse()
            except UnsupportedCondition:
                continue
            if value.free_symbols or value.is_Rational is not True:
                continue
            target = sp.simplify(logs[0][1] ** value)
            if target not in levels:
                levels.append(target)
    return levels, substitution


def review(base, argument, polynomial, levels, parent_html):
    from .exam_trigonometric_log_polynomial import L, LogPolynomial

    soup = BeautifulSoup(parent_html, "html.parser")
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    declared, substitution = declared_levels(formulas)
    trig = [
        m[1] or m[2]
        for f in formulas
        for m in re.finditer(
            r"([tyuz])=\\(?:sin|cos)x|\\(?:sin|cos)x=([tyuz])", clean(f)
        )
    ]
    trig_substitution = trig[0] if trig else None
    if len(set(trig)) > 1:
        raise UnsupportedCondition(
            "one reviewed trigonometric substitution is required"
        )
    degree = sp.degree(polynomial, L)
    if degree == 2 and len(declared) < 2:
        raise UnsupportedCondition("the parent must show both reviewed log levels")
    if degree == 1 and not (
        trig_substitution and "=1" in "".join(clean(f) for f in formulas)
    ):
        raise UnsupportedCondition(
            "a bare-log zero needs the reviewed argument-one method"
        )
    alternative = "другое решение пункта б" in text
    if "другое решение" in text and not alternative:
        raise UnsupportedCondition(
            "the alternative log method must retain its reviewed stage"
        )
    if alternative and (
        len(soup.find_all("img")) != 2
        or "числовой оси" not in text
        or "окружност" not in text
    ):
        raise UnsupportedCondition(
            "both number-line and circle selection methods are required"
        )
    first_log = next((f for f in formulas if r"\log_" in f), "")
    factor_before = (
        r"\begin{cases}" in first_log
        and first_log.count(r"\log_") >= 2
        and polynomial.subs(L, 0) == 0
    )
    discriminant = any(re.search(r"\\pm\s*\\sqrt", f) for f in formulas)
    return LogPolynomial(
        base,
        argument,
        polynomial,
        levels,
        substitution,
        trig_substitution,
        factor_before,
        discriminant,
        alternative,
    ), compare(declared[0], declared[1]) < 0 if len(declared) >= 2 else False
