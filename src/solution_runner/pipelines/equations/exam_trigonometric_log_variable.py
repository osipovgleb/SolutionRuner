"""Retain variable log bases and use their reviewed polynomial definitions."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import ExamAngleParser
from .logarithm_parser import Node
from .power_arithmetic import balanced, clean


@dataclass(frozen=True)
class VariableLog:
    base: sp.Expr
    base_text: str
    argument_text: str
    multiplier: sp.Expr
    level: sp.Expr
    method: str
    candidate_series: tuple = ()
    image_after_definition: bool = False


def reviewed(formula):
    text = clean(formula)
    for m in re.finditer(r"\\log_\{", text):
        base, _ = balanced(text, m.end() - 1)
        if any(f in base for f in (r"\sin", r"\cos", r"\tg", r"\ctg")):
            return True
    return False


class Parser(ExamAngleParser):
    implicit_prefixes = (*ExamAngleParser.implicit_prefixes, r"\log")

    def __init__(self, text, atoms, denominators, logs, depth=0):
        super().__init__(text, atoms, denominators, depth)
        self.logs = logs

    def _nested(self, text):
        return Parser(
            text, self.atoms, self.denominators, self.logs, self.depth + 1
        ).parse()

    def _primary(self):
        if not self.text.startswith(r"\log_", self.index):
            return super()._primary()
        self.index += 5
        if self.text[self.index : self.index + 1] != "{":
            raise UnsupportedCondition("an explicit trigonometric log base is required")
        base_text, self.index = balanced(self.text, self.index)
        base = ExamAngleParser(base_text, self.atoms, self.denominators).parse().value
        before = len(self.logs)
        start = self.index
        arg = self._factor()
        if len(self.logs) != before or before >= 2:
            raise UnsupportedCondition(
                "at most two unnested variable-base logs are reviewed"
            )
        symbol = sp.Symbol("L" + str(before), real=True)
        self.logs.append(
            (symbol, base, arg.value, base_text, self.text[start : self.index])
        )
        return Node(symbol, self.text[start : self.index], "log")


def parent_method(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    forms = [clean(n["data-inline-latex"]) for n in soup.select("[data-inline-latex]")]
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    domain_definition = (
        any(re.fullmatch(r"0<\\(?:sin|cos)x<1", f.replace(r"\lt", "<")) for f in forms)
        and "уравнение равносильно" in text
    )
    if (
        not (any(reviewed(f) for f in forms) or domain_definition)
        or any(
            s in text
            for s in (
                "другое решение",
                "ещё одно решение",
                "еще одно решение",
                "изложим решение",
                "другим способом",
            )
        )
        or any(re.search(r"(?<![A-Za-z])[tyuzv]=", f) for f in forms)
    ):
        raise UnsupportedCondition(
            "one reviewed variable-base definition without an extra method is required"
        )
    if any(r"\ctg2x" in f for f in forms):
        return "cot_double"
    if any(r"\cos^{2}2x" in f or r"\cos^22x" in f for f in forms):
        return "cos_double"
    if any(r"\ctgx" in f for f in forms):
        return "cot"
    if any("D=" in f or r"\pm" in f or r"\sinx=\frac{2}{3}" in f for f in forms):
        return "quadratic"
    raise UnsupportedCondition(
        "the parent's variable-log polynomial method needs review"
    )


def style(parent_html, formula):
    from .exam_trigonometric_log_equality import presentation
    from .exam_trigonometric_style import preference

    if not reviewed(formula):
        return None
    method = parent_method(parent_html)
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    function, _ = preference(parent_html)
    preferred = (
        C
        if method == "cos_double" or (method == "quadratic" and function == "cos")
        else S
    )
    images = soup.find_all("img")
    if images:
        position, _ = presentation(parent_html)
        image_stage(parent_html)
        if "окружност" not in text:
            raise UnsupportedCondition(
                "the original variable-log figure needs its circle method"
            )
        selection = "circle"
    else:
        position = "none"
        selection = (
            "inequalities"
            if re.search(r"двойн\w*\s+неравенств", text)
            else "progressions"
            if "длина отрезка" in text or "расстояние между" in text
            else None
        )
        if selection is None:
            raise UnsupportedCondition(
                "an unillustrated variable-log selection needs its original interval method"
            )
    return preferred, False, False, position, None, selection


def image_stage(parent_html):
    from .exam_trigonometric_log_equality import presentation

    soup = BeautifulSoup(parent_html, "html.parser")
    if not soup.img:
        return False
    _, after = presentation(parent_html)
    if not after:
        return False
    preceding = []
    for n in soup.img.find_parent("li").descendants:
        if n is soup.img:
            break
        if getattr(n, "attrs", {}).get("data-inline-latex"):
            preceding.append(n["data-inline-latex"])
    if (
        len(preceding) != 1
        or not reviewed(preceding[0])
        or r"\begin{cases}" not in preceding[0]
    ):
        raise UnsupportedCondition(
            "the variable-log figure must follow its original definition system"
        )
    return True


def operands(nodes, logs, values):
    symbols = tuple(e[0] for e in logs)
    value = sp.expand(nodes[0].value - nodes[1].value)
    level = -value.subs(dict.fromkeys(symbols, 0))
    if value != symbols[0] - level - (symbols[1] if len(logs) == 2 else 0):
        raise UnsupportedCondition(
            "one complete log definition or same-base log difference is required"
        )
    if level.is_Integer is not True or not 0 <= level <= 4:
        raise UnsupportedCondition(
            "a reviewed integer variable-log level between zero and four is required"
        )
    pairs = tuple(zip(values[::2], values[1::2], strict=True))
    base, argument = pairs[0]
    multiplier = sp.S.One
    if len(logs) == 2:
        other_base, multiplier = pairs[1]
        if (
            other_base != base
            or multiplier.free_symbols
            or multiplier.is_positive is not True
        ):
            raise UnsupportedCondition(
                "the second log must have the same original base and a positive constant argument"
            )
    if (
        base.free_symbols not in ({S}, {C})
        or not base.is_polynomial(S, C)
        or sp.Poly(base, S, C).total_degree() != 1
        or base.subs({S: 0, C: 0}) != 0
        or argument.free_symbols - {S, C}
        or not argument.is_polynomial(S, C)
        or not 1 <= sp.Poly(argument, S, C).total_degree() <= 4
    ):
        raise UnsupportedCondition(
            "one sine/cosine base and a polynomial argument of degree at most four are required"
        )
    return base, argument, multiplier, level


def compile_variable(formula, parent_html):
    from .exam_trigonometric_log_equality import LogEquality, original_text
    from .exam_trigonometric_log_product import LogProduct
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_radical_equation import compile_values

    text = clean(formula).removesuffix(".")
    if not reviewed(text):
        return None
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete variable-base equality is required")
    atoms, denominators, logs = {}, [], []
    nodes = tuple(
        Parser(p.replace("x", r"\alpha"), atoms, denominators, logs).parse()
        for p in text.split("=")
    )
    if not 1 <= len(logs) <= 2:
        raise UnsupportedCondition(
            "one variable log and an optional constant-argument log are required"
        )
    values, poles, identities = compile_values(
        [v for e in logs for v in e[1:3]],
        atoms,
        denominators,
        extra_symbols=tuple(e[0] for e in logs),
    )
    if poles or any(
        a.coefficient != 1 and a.coefficient != 2 and a.coefficient != 4
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "these variable-log definitions require unshifted first, second or fourth angles without original poles"
        )
    if any(a.shift for a in atoms.values()):
        raise UnsupportedCondition(
            "a shifted original variable-log angle needs a separate reviewed definition"
        )
    base, argument, multiplier, level = operands(nodes, logs, values)
    raw = sp.expand(argument - multiplier * base**level)
    method = parent_method(parent_html)
    from .exam_trigonometric_log_variable_methods import candidate_notation, certify

    certify(raw, base, method)
    data = VariableLog(
        base,
        original_text(logs[0][3]),
        original_text(logs[0][4]),
        multiplier,
        level,
        method,
        candidate_notation(raw, base, method, parent_html),
        image_stage(parent_html),
    )
    return Equation(
        raw,
        identities,
        sp.S.One,
        poles=poles,
        log_product=LogProduct(
            raw,
            base,
            argument,
            None,
            equality=LogEquality(
                "variable_definition",
                level,
                None,
                data.argument_text,
                "",
                variable=data,
            ),
        ),
    )
