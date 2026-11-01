"""Keep nonperiodic radical domains in the complete answer, before interval selection."""

import re
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_global_indices import (
    IndexedFamily,
    X,
    positive_intervals,
    real_roots,
    selected,
    windows,
)
from .exam_trigonometric_methods import Equation, ExamAngleParser
from .exam_trigonometric_radical_equation import compile_values
from .logarithm_parser import Node
from .power_arithmetic import balanced, clean

ROOT = sp.Symbol("global_root", real=True)


@dataclass(frozen=True)
class GlobalRadical:
    polynomial: sp.Expr
    periodic: sp.Expr
    factor: sp.Expr
    denominator: bool
    points: tuple
    families: tuple = ()
    case_order: bool = False


class Parser(ExamAngleParser):
    implicit_prefixes = (*ExamAngleParser.implicit_prefixes, r"\alpha", r"\pi")

    def _nested(self, text):
        return Parser(text, self.atoms, self.denominators, self.depth + 1).parse()

    def _primary(self):
        if self.text.startswith(r"\alpha", self.index):
            self.index += 6
            return Node(X, "x")
        if self.text.startswith(r"\pi", self.index):
            self.index += 3
            return Node(sp.pi, r"\pi")
        if self.text[self.index : self.index + 1] == "r":
            self.index += 1
            return Node(ROOT, "r")
        return super()._primary()


def reviewed(html):
    from .exam_trigonometric_radical_style import normalized, variable_roots

    soup = BeautifulSoup(html, "html.parser")
    if soup.find("img"):
        return ""
    text = normalized(soup)
    formulas = " ".join(
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    )
    physical = any(
        not any(t in v for t in (r"\sin", r"\cos", r"\tg", r"\ctg", r"\log"))
        for v in variable_roots(formulas)
    )
    physical = physical or (
        r"\sqrt{a}" in formulas and bool(re.search(r"x\^(?:[24]|\{[24]\})", formulas))
    )
    if physical and "случай" in text and "неравенства" in text:
        return "cases"
    if physical and "отберем" in text and "заметим" in text:
        return "product"
    if (
        "найдем корни числителя" in text
        and r"\tgx" in formulas
        and r"x\gt0" in formulas
        and r"x\lt0" in formulas
    ):
        return "quotient"
    return ""


def read(formula):
    text = clean(formula)
    if (
        text.count("=") != 1
        or re.search(r"[A-Za-z]", re.sub(r"\\[A-Za-z]+", "", text).replace("x", ""))
        or re.search(r"\\(?:alpha|beta|gamma)", text)
    ):
        raise UnsupportedCondition(
            "one original global-radical equality in x is required"
        )
    found = []
    start = 0
    while (index := text.find(r"\sqrt{", start)) >= 0:
        inside, end = balanced(text, index + 5)
        if "x" in inside:
            found.append((index, inside, end))
        start = end
    if len(found) != 1:
        raise UnsupportedCondition("one complete original variable radical is required")
    index, inside, end = found[0]
    body = text[:index] + "(r)" + text[end:]
    atoms = {}
    poles = []
    left, right = (
        Parser(v.replace("x", r"\alpha"), atoms, poles).parse().value
        for v in body.split("=")
    )
    radicand = Parser(inside.replace("x", r"\alpha"), atoms, poles).parse().value
    numerator, denominator = sp.fraction(sp.cancel(left - right))
    if denominator == ROOT and not numerator.has(ROOT):
        quotient = True
        factor = numerator
    elif (
        not denominator.free_symbols
        and numerator.subs(ROOT, 0) == 0
        and sp.degree(numerator, ROOT) == 1
        and not any(p.has(ROOT) for p in poles)
    ):
        quotient = False
        factor = sp.cancel(numerator / ROOT)
    else:
        raise UnsupportedCondition(
            "the radical must be one zero factor or the complete denominator"
        )
    poles = [p for p in poles if not p.has(ROOT)]
    (factor, radicand), poles, _ = compile_values(
        [factor, radicand], atoms, poles, extra_symbols=(X,)
    )
    if (
        factor.free_symbols - {S, C}
        or not factor.is_polynomial(S, C)
        or not 1 <= sp.Poly(factor, S, C).total_degree() <= 2
    ):
        raise UnsupportedCondition(
            "a unit-angle polynomial factor of degree one or two is required"
        )
    if quotient:
        periodic = sp.cancel(radicand / X)
        weights = (sp.cancel(periodic * C / S), sp.cancel(periodic * S / C))
        if periodic.free_symbols - {S, C} or not any(
            not v.free_symbols and v.is_real is True and v != 0 for v in weights
        ):
            raise UnsupportedCondition(
                "the reviewed denominator radicand is x times one unit tangent ratio"
            )
        polynomial = X
        points = ()
    else:
        if (
            radicand.free_symbols - {X}
            or not radicand.is_polynomial(X)
            or sp.degree(radicand, X) not in (2, 4)
            or poles
        ):
            raise UnsupportedCondition(
                "the zero radical factor needs a quadratic or quartic polynomial in physical x without poles"
            )
        polynomial = radicand
        periodic = sp.S.One
        points = real_roots(polynomial)
    if set(poles) - {S, C}:
        raise UnsupportedCondition("only original unit sine/cosine poles are reviewed")
    data = GlobalRadical(polynomial, periodic, factor, quotient, points)
    return Equation(factor, (), sp.S.One, poles=poles, global_radical=data)


def compile_global(formula, method):
    if method not in ("product", "cases", "quotient"):
        raise UnsupportedCondition("unknown global radical parent method")
    compiled = read(formula)
    if compiled.global_radical.denominator != (method == "quotient"):
        raise UnsupportedCondition(
            "the original radical position does not match the parent method"
        )
    return replace(
        compiled,
        global_radical=replace(compiled.global_radical, case_order=method == "cases"),
    )


def branches(compiled, preferred, allow_inverse):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_domain import without_poles

    reduced, result = solve_branches(compiled.raw, preferred, allow_inverse)
    return reduced, without_poles(result, compiled.poles)


def prepare(a, parent_html):
    if a.global_radical is None:
        return a
    from .exam_trigonometric_affine_selection import combine
    from .exam_trigonometric_parameters import affine_families
    from .exam_trigonometric_selection import equivalent_series

    source = tuple(
        dict.fromkeys(
            (q, p, letter)
            for q, p, letter in affine_families(parent_html)
            if equivalent_series((*a.series, (q, p)), a.series)
        )
    )
    nominal = tuple((q, p) for q, p, _ in source)
    if not nominal or not equivalent_series(nominal, a.series):
        raise UnsupportedCondition(
            "the parent nominal families must match the computed trigonometric factor"
        )
    data = a.global_radical
    families = []
    for q, p, letter in source:
        if p not in (1, 2):
            raise UnsupportedCondition(
                "a unit-angle family needs a pi or two-pi period"
            )
        coefficients = tuple(
            sp.simplify(
                data.periodic.subs(
                    {S: sp.sin((q + p * k) * sp.pi), C: sp.cos((q + p * k) * sp.pi)}
                )
            )
            for k in range(int(2 / p))
        )
        if any(
            c.has(sp.zoo, sp.nan)
            or c.is_real is not True
            or c == 0
            or sp.simplify(c - coefficients[0]) != 0
            for c in coefficients
        ):
            raise UnsupportedCondition(
                "the periodic radicand ratio must have one nonzero value on the entire family"
            )
        intervals = positive_intervals(sp.expand(data.polynomial * coefficients[0]))
        families.append(
            IndexedFamily(
                q, p, letter, windows(intervals, q, p), intervals, coefficients[0]
            )
        )
    periodic = tuple(q for family in families for q in selected(family, a.bounds))
    selected_roots = combine(periodic, data.points, a.bounds)
    if data.case_order:
        from .exam_trigonometric_affine_selection import isolated

        selected_roots = tuple(
            dict.fromkeys((*isolated(data.points, a.bounds), *periodic))
        )
    return replace(
        a,
        global_radical=replace(data, families=tuple(families)),
        series=nominal,
        selected=selected_roots,
        selections=(),
        family_parameters=(),
    )
