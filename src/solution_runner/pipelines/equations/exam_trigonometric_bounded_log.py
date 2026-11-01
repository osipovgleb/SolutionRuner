"""Keep a squared radical's finite original domain when reducing a trig logarithm."""

from dataclasses import dataclass, replace
from functools import cmp_to_key

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S
from .logarithm_arithmetic import power
from .logarithm_parser import LogarithmParser, Node, combined
from .power_arithmetic import balanced

L = sp.Symbol("l", real=True)


@dataclass(frozen=True)
class BoundedLog:
    base: sp.Expr
    variable: sp.Symbol
    polynomial: sp.Expr
    levels: tuple
    targets: tuple
    radicand: sp.Expr
    bounds: tuple


class Parser(LogarithmParser):
    def __init__(self, text, logs, domains, depth=0):
        super().__init__(text, depth)
        self.logs, self.domains = logs, domains

    def _nested(self, text):
        return Parser(text, self.logs, self.domains, self.depth + 1).parse()

    @staticmethod
    def _combine(kind, left, right):
        if kind == "divide" and right.value.free_symbols:
            raise UnsupportedCondition(
                "the bounded logarithm has no additional variable denominator"
            )
        return combined(kind, left, right)

    def _factor(self):
        node = super()._factor()
        if (
            node.kind == "power"
            and node.children[0].kind == "root"
            and node.children[0].value.free_symbols
            and node.children[1].value != 2
        ):
            raise UnsupportedCondition(
                "the original variable radical is reviewed only as its complete square"
            )
        if (
            node.kind == "power"
            and node.children[1].value.is_negative
            and node.children[0].value.free_symbols
        ):
            raise UnsupportedCondition(
                "negative variable powers require their own original domain"
            )
        return node

    def _primary(self):
        if self.text[self.index : self.index + 1] == "x":
            self.index += 1
            return Node(X, "x")
        for name, variable in ((r"\sinx", S), (r"\cosx", C)):
            if self.text.startswith(name, self.index):
                self.index += len(name)
                return Node(variable, name)
        if self.text.startswith(r"\sqrt{", self.index):
            text, self.index = balanced(self.text, self.index + 5)
            value = self._nested(text).value
            if not value.is_polynomial(X) or value.free_symbols - {X}:
                raise UnsupportedCondition(
                    "the original squared radical needs a polynomial in x"
                )
            if value.free_symbols:
                self.domains.append(value)
            elif value.is_nonnegative is not True:
                raise UnsupportedCondition("a constant square root must be real")
            return Node(sp.sqrt(value), r"\sqrt{" + text + "}", "root")
        return super()._primary()

    def _log(self):
        self.index += 5
        if self.text[self.index : self.index + 1] == "{":
            text, self.index = balanced(self.text, self.index)
        elif (
            self.index < len(self.text)
            and self.text[self.index : self.index + 1] in "23456789"
        ):
            text = self.text[self.index]
            self.index += 1
        else:
            raise UnsupportedCondition(
                "an unambiguous numeric logarithm base is required"
            )
        base = self._nested(text).value
        if base.free_symbols or base.is_positive is not True or base == 1:
            raise UnsupportedCondition(
                "the logarithm base must be a positive constant different from one"
            )
        exponent = (
            self._exponent().value
            if self.text[self.index : self.index + 1] == "^"
            else sp.S.One
        )
        argument = self._factor().value
        if argument not in (S, C) or exponent not in (1, 2):
            raise UnsupportedCondition(
                "one unit sine/cosine logarithm with degree at most two is required"
            )
        self.logs.append((base, argument))
        return Node(
            L**exponent, r"\log_{" + sp.latex(base) + "}(" + str(argument) + ")"
        )


def reviewed(html):
    soup = BeautifulSoup(html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    from .exam_trigonometric_radical_style import variable_roots

    formulas = " ".join(
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    )
    return (
        r"\log_" in formulas
        and any(v in formulas for v in (r"(\sinx)", r"(\cosx)"))
        and "область определения" in text
        and any(
            not any(f in r for f in (r"\sin", r"\cos", r"\tg", r"\ctg", r"\log"))
            for r in variable_roots(formulas)
        )
    )


def compile_log(formula):
    from .exam_trigonometric_methods import Equation

    logs, domains = [], []
    if formula.count("=") != 1:
        raise UnsupportedCondition(
            "one complete bounded logarithm equality is required"
        )
    left, right = [
        Parser(part, logs, domains).parse().value for part in formula.split("=")
    ]
    expression = sp.expand(left - right)
    if (
        len(domains) != 1
        or not logs
        or len(set(logs)) != 1
        or not expression.is_polynomial(L)
        or expression.free_symbols - {L}
    ):
        raise UnsupportedCondition(
            "one logarithm and one fully squared radical must cancel the original x terms exactly"
        )
    radicand = domains[0]
    if sp.degree(radicand, X) != 2 or sp.Poly(radicand, X).LC() >= 0:
        raise UnsupportedCondition(
            "a finite quadratic original radical domain is required"
        )
    bounds = tuple(sorted(roots(radicand), key=cmp_to_key(compare)))
    if len(bounds) != 2:
        raise UnsupportedCondition(
            "the original radical domain must have two distinct finite endpoints"
        )
    if sp.degree(expression, L) not in (1, 2):
        raise UnsupportedCondition("the logarithm equation must have degree one or two")
    levels = roots(expression.subs(L, X))
    base, variable = logs[0]
    targets = tuple(power(base, v) for v in levels)
    valid = tuple(
        t for t in targets if compare(t, sp.S.Zero) > 0 and compare(t, sp.S.One) <= 0
    )
    if not valid:
        raise UnsupportedCondition(
            "no reviewed positive trigonometric logarithm level remains"
        )
    data = BoundedLog(base, variable, expression, levels, targets, radicand, bounds)
    return Equation(
        sp.prod(variable - t for t in valid),
        (),
        sp.S.One,
        domain=variable,
        strict_domain=True,
        bounded_log=data,
    )


def prepare(a):
    from .exam_trigonometric import select
    from .exam_trigonometric_affine_selection import isolated

    if a.bounded_log is None:
        return a
    lo, hi = a.bounded_log.bounds
    full = select(a.series, (lo / sp.pi, hi / sp.pi, True, True))[0]
    selected = isolated(tuple(q * sp.pi for q in full), a.bounds)
    return replace(a, finite_roots=full, selected=selected)
