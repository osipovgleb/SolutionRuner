"""Read a parent's exponential substitution and retain its root order."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T, U
from .exam_trigonometric_power_parser import PositivePowerParser
from .exam_trigonometric_radical_equation import compile_values, same, trig_polynomial
from .power_arithmetic import clean


@dataclass(frozen=True)
class UnitShape:
    variable: sp.Symbol
    scale: sp.Rational = sp.S.One
    power: int = 1
    product: bool = False

    @property
    def argument(self):
        if self.product:
            return S * C
        if self.variable in (T, U):
            return S / C if self.variable == T else C / S
        name = "sin" if self.variable == S else "cos"
        return trig_polynomial(name, sp.Rational(self.scale)) ** self.power


@dataclass(frozen=True)
class PolynomialStyle:
    shape: UnitShape
    substitution: str | None
    below_one: bool
    exponent_multiplier: bool
    ascending: bool
    figure_after_polynomial: bool = False
    positive_trig_first: bool = False


def pieces(html):
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        text = clean(node["data-inline-latex"])
        for token in (
            r"\left[",
            r"\right.",
            r"\begin{aligned}",
            r"\end{aligned}",
            r"\begin{cases}",
            r"\end{cases}",
            "&",
        ):
            text = text.replace(token, "")
        for term in re.split(r"\\(?:iff|Leftrightarrow)|\\\\", text):
            yield (
                re.split(r"\\(?:quad|gt|ge|lt|le|ne)|[<>]", term)[0]
                .rstrip(".,")
                .strip("[]")
            )


def parse(text):
    atoms, poles = {}, []
    node = PositivePowerParser(text.replace("x", r"\alpha"), atoms, poles).parse()
    return node, atoms, poles


def constant(text):
    text = re.sub(
        r"\\sqrt\[4\]\{(\d{1,3})\}", lambda m: "(" + m[1] + r"^{\frac{1}{4}})", text
    )
    node, atoms, poles = parse(text)
    if (
        atoms
        or any(p.free_symbols or p == 0 for p in poles)
        or node.value.free_symbols
        or node.value.is_real is not True
    ):
        raise UnsupportedCondition("one closed real parent power root is required")
    return node.value


def compare_roots(first, second):
    difference = sp.simplify(first - second)
    if difference == 0:
        return 0
    if difference.is_positive is True:
        return 1
    if difference.is_negative is True:
        return -1
    return compare(first, second)


def quadratic_figure(html, name):
    if name is None:
        return False
    soup = BeautifulSoup(html, "html.parser")
    images = soup.find_all("img")
    if len(images) != 1:
        return False
    image = images[0]
    part = image.find_parent("li")
    if part is None or part.get("data-list-marker") not in ("а)", "a)"):
        return False
    before, after = [], []
    seen = False
    for node in part.descendants:
        if node is image:
            seen = True
        elif getattr(node, "attrs", {}).get("data-inline-latex"):
            (after if seen else before).append(clean(node["data-inline-latex"]))
    return bool(
        before
        and after
        and len(re.findall(r"(?<![A-Za-z])" + name + "=", before[-1])) >= 2
        and not any(
            re.search(r"\\(?:sin|cos|tg|ctg)(?:\^\{?2\}?)?x=", v) for v in before
        )
        and any(
            "^{" in v and any(f in v for f in (r"\sin", r"\cos", r"\tg", r"\ctg"))
            for v in after
        )
    )


def power_hint(text):
    node, atoms, poles = parse(text)
    if node.kind != "power" or node.children[0].value.is_Rational is not True:
        return None
    if not node.children[1].value.free_symbols:
        return None
    values, _, _ = compile_values([node.children[1].value], atoms, poles)
    return node.children[0].value, values[0]


def shape_of(argument, source):
    product = r"\sinx" in source and r"\cosx" in source
    candidates = (
        (UnitShape(S, scale=sp.Integer(2), product=True),) if product else ()
    ) + tuple(
        UnitShape(v, scale, power)
        for v, scale, power in (
            (S, 1, 1),
            (C, 1, 1),
            (S, 1, 2),
            (C, 1, 2),
            (S, 2, 1),
            (C, 2, 1),
            (T, 1, 1),
            (U, 1, 1),
        )
    )
    for shape in candidates:
        multiple = sp.cancel(argument / shape.argument)
        if multiple.is_Rational and multiple != 0 and abs(multiple) <= 100:
            return shape, multiple != 1
    raise UnsupportedCondition("one reviewed trigonometric power unit is required")


def evidence(terms):
    for term in terms:
        if term.count("=") != 1:
            continue
        try:
            left, right = (parse(v)[0].value for v in term.split("="))
        except UnsupportedCondition:
            continue
        value = sp.expand(left - right)
        if len(sp.Add.make_args(value)) >= 3 and any(
            v.is_Pow and v.base.is_Rational and v.exp.free_symbols
            for v in sp.preorder_traversal(value)
        ):
            return True
    return False


def review(html):
    terms = tuple(pieces(html))
    hints, named, values = [], [], []
    for term in terms:
        if term.count("=") != 1:
            continue
        left, right = term.split("=")
        try:
            hint = power_hint(right if left in ("t", "y") else left)
        except UnsupportedCondition:
            continue
        if hint is not None:
            if left in ("t", "y"):
                named.append((left, hint, right))
            else:
                try:
                    values.append((hint, constant(right)))
                except UnsupportedCondition:
                    continue
                hints.append((None, hint, left))
    if not named and not evidence(terms):
        return None
    text = BeautifulSoup(html, "html.parser").get_text(" ").replace("\xad", "").lower()
    if (
        any(
            v in text
            for v in (
                "случа",
                "другое решение",
                "ещё одно решение",
                "второй способ",
                "другой способ",
            )
        )
        or len({v[0] for v in named}) > 1
    ):
        raise UnsupportedCondition(
            "one parent exponential quadratic method is required"
        )
    if not (named or hints):
        raise UnsupportedCondition("the parent must identify its exponential unit")
    name, (base, argument), source = (named or hints)[0]
    shape, multiplier = shape_of(argument, source)
    roots = []
    for term in terms:
        if name is not None and term.startswith(name + "="):
            try:
                roots.append(constant(term[len(name) + 1 :]))
            except UnsupportedCondition:
                continue
    if name is None:
        roots = [v for (b, a), v in values if b == base and same(a, argument)]
    roots = list(dict.fromkeys(roots))
    ascending = len(roots) >= 2 and compare_roots(roots[0], roots[1]) < 0
    positive_first = False
    for term in terms:
        match = re.fullmatch(r"\\(?:sin|cos)x=(.+)", term)
        if match:
            try:
                value = constant(match[1])
            except UnsupportedCondition:
                continue
            if value != 0:
                positive_first = compare_roots(value, sp.S.Zero) > 0
                break
    return PolynomialStyle(
        shape,
        name,
        bool(base < 1),
        multiplier,
        ascending,
        quadratic_figure(html, name),
        positive_first,
    )


def shapes(style, formula):
    shape = style.shape
    if shape.power == 2:
        explicit = set(re.findall(r"\\(sin|cos)\^(?:2|\{2\})x", clean(formula)))
        if len(explicit) == 1:
            shape = UnitShape(S if "sin" in explicit else C, power=2)
    result = [shape]
    if not shape.product:
        other = {S: C, C: S, T: U, U: T}[shape.variable]
        result.append(UnitShape(other, shape.scale, shape.power))
    return tuple(result)
