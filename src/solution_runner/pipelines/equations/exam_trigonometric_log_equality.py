"""Reduce log definitions exactly before solving the shared unit-circle polynomial."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_log_parser import Parser
from .logarithm_arithmetic import power
from .logarithm_parser import Node
from .power_arithmetic import clean

if TYPE_CHECKING:
    from .exam_trigonometric_log_identity import LogIdentity
    from .exam_trigonometric_log_linear import LinearLogs
    from .exam_trigonometric_log_variable import VariableLog


@dataclass(frozen=True)
class LogEquality:
    kind: str
    target: sp.Expr
    other_argument: sp.Expr | None
    argument_text: str
    right_text: str
    power_text: str = ""
    grouping: bool = False
    centre_inverse: bool = False
    image_after_reduction: bool = False
    first_factor: str | None = None
    linear: "LinearLogs | None" = None
    variable: "VariableLog | None" = None
    identity: "LogIdentity | None" = None


class EqualityParser(Parser):
    implicit_prefixes = (*Parser.implicit_prefixes, r"\alpha")

    def __init__(self, text, atoms, denominators, logs, powers, depth=0):
        super().__init__(text, atoms, denominators, logs, depth)
        self.powers = powers

    def _nested(self, text):
        return EqualityParser(
            text, self.atoms, self.denominators, self.logs, self.powers, self.depth + 1
        ).parse()

    def _primary(self):
        if self.text.startswith(r"\alpha", self.index):
            self.index += 6
            return Node(X, "x")
        return super()._primary()

    def _factor(self):
        token = self.text[self.index : self.index + 1]
        if token in ("+", "-"):
            self.index += 1
            node = self._factor()
            return node if token == "+" else Node(-node.value, "", "negative", (node,))
        start = self.index
        node = self._primary()
        if self.text[self.index : self.index + 1] != "^":
            return node
        exponent = self._exponent().value
        if exponent.has(X):
            coefficient = sp.cancel(exponent / X)
            if (
                node.value.free_symbols
                or node.value.is_positive is not True
                or node.value == 1
                or coefficient.is_Rational is not True
                or abs(coefficient) > 12
                or coefficient.q > 12
                or len(self.powers) >= 1
            ):
                raise UnsupportedCondition(
                    "one positive constant power with a bounded pure multiple of x is required"
                )
            symbol = sp.Symbol("E" + str(len(self.powers)), positive=True)
            text = self.text[start : self.index].replace(r"\alpha", "x")
            self.powers.append((symbol, node.value, coefficient, text))
            return Node(symbol, text, "exponential")
        return Node(power(node.value, exponent), "", "power", (node,))


def reviewed(formula):
    text = clean(formula).removesuffix(".")
    return (
        text.count("=") == 1 and text.startswith(r"\log_") and not text.endswith("=0")
    )


def original_text(text):
    import re

    return re.sub(
        r"\\(sin|cos|tg|ctg)(?=x)",
        lambda m: "\\" + m[1] + " ",
        text.replace(r"\alpha", "x"),
    )


def first_factor(parent_html):
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    ]
    return next(
        (m[1] for f in formulas for m in re.finditer(r"\\(sin|cos)x\(", clean(f))), None
    )


def order_branches(data, branches):
    preferred = {"sin": S, "cos": C}.get(data.first_factor)
    return (
        tuple(
            sorted(
                branches,
                key=lambda b: (b.candidates != (sp.S.Zero,), b.variable != preferred),
            )
        )
        if preferred is not None
        else tuple(branches)
    )


def presentation(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    if any(
        marker in text
        for marker in (
            "другое решение",
            "ещё одно решение",
            "еще одно решение",
            "изложим решение",
            "другим способом",
        )
    ):
        raise UnsupportedCondition(
            "an unreviewed extra log-definition method cannot be discarded"
        )
    images = soup.find_all("img")
    if len(images) != 1:
        raise UnsupportedCondition(
            "one original circle is required for the log-definition method"
        )
    image = images[0]
    part = image.find_parent("li")
    if part is None:
        return "outside", False
    if part.get("data-list-marker") == "б)":
        return "selection", False
    if part.get("data-list-marker") != "а)":
        raise UnsupportedCondition("the source figure needs its original exam subpart")
    preceding = []
    for node in part.descendants:
        if node is image:
            break
        preceding.append(node)
    reduced = any(getattr(n, "attrs", {}).get("data-inline-latex") for n in preceding)
    return ("after-intro" if reduced else "before-intro"), reduced


def reduce_definition(nodes, logs, powers, values):
    argument = values[0]
    right = nodes[1].value
    other = None
    power_text = ""
    if len(logs) == 2 and nodes[1].kind == "log" and right == logs[1][0]:
        if logs[0][1] != logs[1][1] or powers:
            raise UnsupportedCondition(
                "both logarithms must have the same constant base and trig-only arguments"
            )
        kind, target, other = "two_logs", values[1], values[1]
        right_text = original_text(nodes[1].text)
    elif len(logs) == 1 and not right.free_symbols:
        if powers or right.is_Rational is not True or abs(right) > 20 or right.q > 12:
            raise UnsupportedCondition("one bounded rational log level is required")
        kind, target = "constant", power(logs[0][1], right)
        right_text = sp.latex(right)
    elif len(logs) == 1 and right == X and len(powers) == 1:
        symbol, base, coefficient, power_text = powers[0]
        if sp.simplify(base**coefficient - logs[0][1]) != 0:
            raise UnsupportedCondition(
                "the original exponential must equal the log base to x exactly"
            )
        kind, target = "exponential", symbol
        right_text = "x"
    else:
        raise UnsupportedCondition(
            "a constant, x with its matching power, or a same-base log is required"
        )
    raw = sp.expand(argument - target)
    divisor = sp.S.One
    if kind == "two_logs":
        coefficient = sp.cancel(other / C)
        if (
            coefficient.free_symbols
            or coefficient.is_real is not True
            or coefficient == 0
            or not raw.is_polynomial(S, C)
            or raw.subs(C, 0) != 0
        ):
            raise UnsupportedCondition(
                "the reviewed equal logs require a nonzero cosine from their original positive argument"
            )
        divisor = C
    if (
        raw.free_symbols - {S, C}
        or not raw.is_polynomial(S, C)
        or not 1 <= sp.Poly(raw, S, C).total_degree() <= 2
        or not sp.rem(raw, S * S + C * C - 1, S).free_symbols
    ):
        raise UnsupportedCondition(
            "the log definition must leave one nonconstant quadratic unit-circle polynomial"
        )
    return kind, raw, divisor, other, right_text, power_text


def compile_equality(formula, parent_html):
    from .exam_trigonometric_log_methods import level_order
    from .exam_trigonometric_log_parent import definition_chain
    from .exam_trigonometric_log_product import LogProduct
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_radical_equation import compile_values
    from .exam_trigonometric_style import grouping_method

    text = clean(formula).removesuffix(".")
    if not reviewed(formula):
        raise UnsupportedCondition(
            "one reviewed complete logarithmic equality is required"
        )
    atoms, denominators, logs, powers = {}, [], [], []
    nodes = [
        EqualityParser(
            part.replace("x", r"\alpha"), atoms, denominators, logs, powers
        ).parse()
        for part in text.split("=")
    ]
    if not logs or nodes[0].kind != "log" or nodes[0].value != logs[0][0]:
        raise UnsupportedCondition(
            "one whole first-power logarithm must be the left side"
        )
    values, poles, identities = compile_values(
        [*(e[2] for e in logs)],
        atoms,
        denominators,
        extra_symbols=(*[p[0] for p in powers], X),
    )
    if not set(poles) <= {S, C}:
        raise UnsupportedCondition(
            "log definitions retain only original sine/cosine poles"
        )
    argument = values[0]
    kind, raw, divisor, other, right_text, power_text = reduce_definition(
        nodes, logs, powers, values
    )
    if powers:
        argument = argument.subs(powers[0][0], logs[0][1] ** X)
    soup = BeautifulSoup(parent_html, "html.parser")
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    if not any(
        (r"\log_" in f and "=" in f)
        or (kind == "exponential" and re.search(r"=\d+\^\{?x\}?", clean(f)))
        for f in formulas
    ) and not (kind == "constant" and definition_chain(formulas)):
        raise UnsupportedCondition("the parent must show the log-definition method")
    data = LogProduct(
        raw,
        logs[0][1],
        argument,
        None,
        divide=divisor,
        level_ascending=level_order(formulas),
        equality=LogEquality(
            kind,
            nodes[1].value,
            other,
            original_text(nodes[0].text),
            right_text,
            power_text,
            grouping_method(parent_html)
            or any(
                re.search(r"\\(?:sin|cos)x(\([^()]+\))[+-][^()]+\1", clean(f))
                for f in formulas
            ),
            any(r"-\pi+\arccos" in clean(f) for f in formulas),
            presentation(parent_html)[1],
            first_factor(parent_html),
        ),
    )
    return Equation(raw, identities, sp.S.One, poles=poles, log_product=data)
