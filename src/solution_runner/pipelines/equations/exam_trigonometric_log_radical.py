"""Certify a root times one log, retaining a strictly positive root denominator."""

from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_log_parser import Parser
from .exam_trigonometric_methods import ExamAngleParser
from .logarithm_parser import Node
from .power_arithmetic import balanced, clean


@dataclass(frozen=True)
class RadicalLog:
    denominator: sp.Expr | None
    divide: bool
    alternative: bool


def inverse_power(formula):
    text = clean(formula).removesuffix(".")
    parts = text.split("=")
    if len(parts) != 2 or r"\log_" not in parts[1] or "^{" not in parts[1]:
        return None
    left, right = parts
    if not left.startswith(r"\sqrt{"):
        return None
    _inside, end = balanced(left, 5)
    if end != len(left):
        raise UnsupportedCondition(
            "the inverse-log identity needs one complete left radical"
        )
    atoms, denominators, logs = {}, [], []
    node = Parser(right.replace("x", r"\alpha"), atoms, denominators, logs).parse()
    if (
        len(logs) != 1
        or any(d.free_symbols or d == 0 for d in denominators)
        or node.kind != "power"
        or len(node.children) != 2
        or node.children[0].value != logs[0][1]
        or node.children[1].value != logs[0][0]
        or logs[0][1].is_Rational is not True
        or not 0 < logs[0][1] <= 1000000
        or logs[0][1] == 1
    ):
        raise UnsupportedCondition(
            "one whole positive constant power of its own logarithm is required"
        )
    from .exam_trigonometric_radical_equation import compile_values

    values, poles, _identities = compile_values([logs[0][2]], atoms, denominators)
    argument = values[0]
    if poles or argument not in (S, C):
        raise UnsupportedCondition(
            "one original unit sine or cosine log argument is required"
        )
    return (
        left + "=" + (r"\sin x" if argument == S else r"\cos x"),
        logs[0][1],
        argument,
    )


def compile_inverse(formula, parent_html):
    from dataclasses import replace

    from .exam_trigonometric_radical_equation import compile_radical
    from .exam_trigonometric_radical_style import kind

    identity = inverse_power(formula)
    if identity is None:
        raise UnsupportedCondition(
            "one complete inverse-power logarithm identity is required"
        )
    normalized, base, argument = identity
    if kind(parent_html) != "safe_square":
        raise UnsupportedCondition(
            "the inverse-log radical requires its reviewed equivalent-square method"
        )
    equation = compile_radical(normalized, "safe_square")
    return replace(
        equation,
        radical_equation=replace(
            equation.radical_equation,
            positive_arguments=(argument,),
            inverse_identity=(base, argument),
        ),
    )


class RootParser(Parser):
    def __init__(self, text, atoms, denominators, logs, roots, depth=0):
        super().__init__(text, atoms, denominators, logs, depth)
        self.roots = roots

    def _nested(self, text):
        return RootParser(
            text, self.atoms, self.denominators, self.logs, self.roots, self.depth + 1
        ).parse()

    def _primary(self):
        if self.text.startswith(r"\sqrt{", self.index):
            inside, end = balanced(self.text, self.index + 5)
            if r"\alpha" in inside:
                if len(self.roots) >= 2:
                    raise UnsupportedCondition(
                        "at most two original variable radicals are reviewed"
                    )
                radicand = (
                    ExamAngleParser(inside, self.atoms, self.denominators).parse().value
                )
                symbol = sp.Symbol("Q" + str(len(self.roots)), real=True)
                self.roots.append((symbol, radicand))
                self.index = end
                return Node(symbol, "", "root")
        return super()._primary()


def style(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    alternative = "изложим решение пункта а) иначе" in text
    images = soup.find_all("img")
    if "окружност" not in text or len(images) != (2 if alternative else 1):
        raise UnsupportedCondition(
            "the radical-log methods require all original circles"
        )
    parts = [n.find_parent("li") for n in images]
    expected = ["а)", "б)"] if alternative else ["а)"]
    if [p.get("data-list-marker") if p else None for p in parts] != expected:
        raise UnsupportedCondition(
            "each radical-log circle must retain its original subpart"
        )
    if any(
        s in text for s in ("другое решение", "ещё одно решение", "еще одно решение")
    ):
        raise UnsupportedCondition("an unknown extra radical-log method is unsupported")
    first = images[0]
    while first.parent is not parts[0]:
        first = first.parent
    position = (
        "before-intro"
        if not any(str(n).strip() for n in first.previous_siblings)
        else "after-intro"
    )
    return soup, text, alternative, position


def certify(root, argument, denominator, text):
    if not root.is_polynomial(S) or sp.degree(root, S) != 1:
        raise UnsupportedCondition("an affine sine radicand is required")
    a, d = root.coeff(S), root.subs(S, 0)
    if (
        root.free_symbols - {S}
        or a.is_positive is not True
        or d.is_positive is not True
    ):
        raise UnsupportedCondition(
            "the root must have positive affine sine coefficients"
        )
    if denominator is None:
        if (
            sp.cancel(argument / C).is_positive is not True
            or (1 - d / a).is_positive is not True
            or "совокупност" not in text
        ):
            raise UnsupportedCondition(
                "the zero-root method needs its reviewed nonstrict sine boundary"
            )
        return False
    k, b = sp.cancel(-denominator * C / S), sp.cancel(argument / C)
    if (
        k.free_symbols
        or k.is_positive is not True
        or b.free_symbols
        or b.is_negative is not True
        or "сократ" not in text
    ):
        raise UnsupportedCondition(
            "cancelling radicals needs cos<0, sin>0 and a strict original denominator"
        )
    return True


def compile_product(formula, parent_html):
    from .exam_trigonometric_log_product import LogProduct
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_radical_equation import compile_values

    text = clean(formula).removesuffix(".")
    if text.count("=") != 1 or not text.endswith("=0"):
        raise UnsupportedCondition("one complete radical-log zero product is required")
    atoms, denominators, logs, roots = {}, [], [], []
    value = (
        RootParser(text[:-2].replace("x", r"\alpha"), atoms, denominators, logs, roots)
        .parse()
        .value
    )
    if len(logs) != 1 or not roots:
        raise UnsupportedCondition(
            "one original numerator log and one or two radicals are required"
        )
    symbols = [logs[0][0], *(s for s, _ in roots)]
    values, poles, identities = compile_values(
        [value, logs[0][2], *(v for _, v in roots)],
        atoms,
        denominators,
        extra_symbols=symbols,
    )
    value, argument, *radicands = values
    num, den = sp.fraction(value)
    upstairs = [i for i, (s, _) in enumerate(roots) if num.has(s)]
    downstairs = [i for i, (s, _) in enumerate(roots) if den.has(s)]
    if (
        len(upstairs) != 1
        or len(downstairs) > 1
        or len(upstairs) + len(downstairs) != len(roots)
    ):
        raise UnsupportedCondition(
            "exactly one numerator radical and at most one denominator radical are required"
        )
    top = roots[upstairs[0]][0]
    bottom = roots[downstairs[0]][0] if downstairs else sp.S.One
    coefficient = sp.cancel(value * bottom / (top * logs[0][0]))
    if (
        coefficient.free_symbols
        or coefficient == 0
        or coefficient.is_real is not True
        or any(p.has(logs[0][0]) for p in poles)
    ):
        raise UnsupportedCondition(
            "the entire expression must be a root times a log over its original radical"
        )
    if any(p.has(*symbols) and p != bottom for p in poles):
        raise UnsupportedCondition(
            "an extra cancelled radical denominator is unsupported"
        )
    poles = tuple(p for p in poles if not p.has(*symbols))
    if (
        not set(poles) <= {S, C}
        or argument.free_symbols - {C}
        or sp.cancel(argument / C).free_symbols
    ):
        raise UnsupportedCondition(
            "the original log must be proportional to cosine with only original ratio poles"
        )
    root = radicands[upstairs[0]]
    denominator = radicands[downstairs[0]] if downstairs else None
    _, parent_text, alternative, _ = style(parent_html)
    divide = certify(root, argument, denominator, parent_text)
    if alternative and (divide or "совокупност" not in parent_text):
        raise UnsupportedCondition(
            "the alternative must retain both zero-factor systems"
        )
    data = LogProduct(
        root,
        logs[0][1],
        argument,
        None,
        radical=RadicalLog(denominator, divide, alternative),
    )
    raw = sp.expand((sp.S.One if divide else root) * (argument - 1))
    return Equation(raw, identities, sp.S.One, poles=poles, log_product=data)
