"""Strip reviewed positive same-base powers before the shared log polynomial."""

import re
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_log_equality import original_text
from .exam_trigonometric_log_parser import Parser
from .logarithm_arithmetic import power
from .logarithm_parser import Node
from .power_arithmetic import clean


@dataclass(frozen=True)
class LogPowers:
    base: sp.Expr
    left: sp.Expr
    right: sp.Expr
    denominator_exponents: tuple
    image_after_log: bool = False


class PowerParser(Parser):
    def __init__(self, text, atoms, denominators, logs, bases, depth=0):
        super().__init__(text, atoms, denominators, logs, depth)
        self.bases = bases

    def _nested(self, text):
        return PowerParser(
            text, self.atoms, self.denominators, self.logs, self.bases, self.depth + 1
        ).parse()

    def _factor(self):
        token = self.text[self.index : self.index + 1]
        if token in ("+", "-"):
            self.index += 1
            node = self._factor()
            return node if token == "+" else Node(-node.value, "", "negative", (node,))
        node = self._primary()
        if self.text[self.index : self.index + 1] != "^":
            return node
        exponent = self._exponent()
        if not exponent.value.free_symbols:
            return Node(
                power(node.value, exponent.value), "", "power", (node, exponent)
            )
        if (
            node.value.is_Rational is not True
            or not sp.Rational(1, 1000) <= node.value <= 1000
            or node.value == 1
            or exponent.value.free_symbols - {e[0] for e in self.logs}
            or len(self.bases) >= 4
        ):
            raise UnsupportedCondition(
                "one bounded positive exponential base and log-only exponents are required"
            )
        self.bases.append(node.value)
        return Node(
            sp.Pow(node.value, exponent.value, evaluate=False),
            "",
            "power",
            (node, exponent),
        )


def reviewed(formula):
    text = clean(formula).removesuffix(".")
    return (
        bool(re.match(r"(?:\d{1,4}|\([^()]+\)|\\frac\{\d{1,4}\}\{\d{1,4}\})\^\{", text))
        and text.count("=") == 1
        and r"\log_" in text
    )


def log_text(node):
    if node.kind == "log":
        return node.text
    return next((value for child in node.children if (value := log_text(child))), "")


def exponents(nodes, base, logs):
    from .exam_trigonometric_log_polynomial import L

    result = []
    for node in nodes:
        value = sp.expand(
            sp.cancel(sp.expand_log(sp.log(node.value), force=False) / sp.log(base))
        )
        value = sp.expand(value.subs(dict.fromkeys((e[0] for e in logs), L)))
        if (
            value.free_symbols - {L}
            or not value.is_polynomial(L)
            or sp.degree(value, L) > 2
            or any(
                c.is_Rational is not True or abs(c) > 100 or c.q > 100
                for c in sp.Poly(value, L).all_coeffs()
            )
        ):
            raise UnsupportedCondition(
                "each complete side must be a same-base power of a bounded log polynomial"
            )
        result.append(value)
    return tuple(result)


def image_stage(soup, substitution):
    images = soup.find_all("img")
    if len(images) != 1:
        raise UnsupportedCondition(
            "one original circle is required for the common-base log method"
        )
    image = images[0]
    part = image.find_parent("li")
    if part is None or part.get("data-list-marker") not in ("а)", "a)"):
        raise UnsupportedCondition(
            "the original figure must retain its derivation subpart"
        )
    preceding = []
    for n in part.descendants:
        if n is image:
            break
        if getattr(n, "attrs", {}).get("data-inline-latex"):
            preceding.append(n["data-inline-latex"])
    if preceding and not (
        substitution and clean(preceding[-1]).count(substitution + "=") >= 2
    ):
        raise UnsupportedCondition(
            "the source figure must be before derivation or after the solved log substitution"
        )
    return bool(preceding)


def compile_powers(formula, parent_html):
    from .exam_trigonometric_log_polynomial import L, compile_polynomial
    from .exam_trigonometric_radical_equation import compile_values

    text = clean(formula).removesuffix(".")
    if not reviewed(formula):
        raise UnsupportedCondition("one reviewed exponential log equality is required")
    soup = BeautifulSoup(parent_html, "html.parser")
    parent = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    if not any(s in parent for s in ("одному основанию", "равными основаниями")) or any(
        s in parent
        for s in (
            "другое решение",
            "еще одно решение",
            "ещё одно решение",
            "другим способом",
        )
    ):
        raise UnsupportedCondition(
            "the parent must retain the common-base method and its log levels"
        )
    atoms, denominators, logs, bases = {}, [], [], []
    nodes = [
        PowerParser(p.replace("x", r"\alpha"), atoms, denominators, logs, bases).parse()
        for p in text.split("=")
    ]
    if not bases or len(set(bases)) != 1 or not logs:
        raise UnsupportedCondition(
            "all original variable powers need the same positive constant base"
        )
    arguments, poles, _ = compile_values([e[2] for e in logs], atoms, [])
    if poles or len({(e[1], v) for e, v in zip(logs, arguments, strict=True)}) != 1:
        raise UnsupportedCondition(
            "one exact log base and argument without original trig poles are required"
        )
    symbols = {e[0] for e in logs}
    if any(d.is_positive is not True or d.free_symbols - symbols for d in denominators):
        raise UnsupportedCondition(
            "every original denominator must be certified strictly positive"
        )
    left, right = exponents(nodes, bases[0], logs)
    polynomial = sp.expand(left - right)
    if polynomial == 0 or not 1 <= sp.degree(polynomial, L) <= 2:
        raise UnsupportedCondition(
            "the common-base equation must leave a nonconstant quadratic log polynomial"
        )
    argument = original_text(next(v for n in nodes if (v := log_text(n))))
    log = r"\log_{" + sp.latex(logs[0][1]) + r"}\left(" + argument + r"\right)"
    normalized = sp.latex(polynomial, symbol_names={L: "(" + log + ")"}) + "=0"
    compiled = compile_polynomial(normalized, parent_html)
    if compiled is None:
        raise UnsupportedCondition(
            "the reduced equation needs the reviewed single-log polynomial method"
        )
    denominator_exponents = tuple(
        sp.expand(d.exp.subs(dict.fromkeys(symbols, L)))
        for d in denominators
        if d.is_Pow and d.base == bases[0]
    )
    return replace(
        compiled,
        log_polynomial=replace(
            compiled.log_polynomial,
            powers=LogPowers(
                bases[0],
                left,
                right,
                denominator_exponents,
                image_stage(soup, compiled.log_polynomial.substitution),
            ),
        ),
    )
