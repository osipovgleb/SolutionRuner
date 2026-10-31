"""Solve symmetric absolute values after a nonnegative cotangent substitution."""

import re

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import S, U
from .exam_trigonometric_methods import ExamAngleParser
from .logarithm_parser import Node
from .power_arithmetic import balanced, clean

R = sp.Symbol("r", real=True)
PARAMETER = sp.Symbol("t", nonnegative=True)


class RootPlaceholderParser(ExamAngleParser):
    def _nested(self, text):
        return RootPlaceholderParser(
            text, self.atoms, self.denominators, self.depth + 1
        ).parse()

    def _primary(self):
        if self.text[self.index : self.index + 1] == "r":
            self.index += 1
            return Node(R, "r")
        return super()._primary()


def side(text, atoms, denominators):
    roots = []
    start = 0
    while (index := text.find(r"\sqrt{", start)) >= 0:
        inner, end = balanced(text, index + 5)
        if "x" in inner:
            roots.append((index, inner, end))
        start = end
    if len(roots) != 1:
        raise UnsupportedCondition("each absolute value needs one variable square root")
    index, radicand, end = roots[0]
    body = text[:index] + "(r)" + text[end:]
    value = (
        RootPlaceholderParser(body.replace("x", r"\alpha"), atoms, denominators)
        .parse()
        .value
    )
    root = (
        ExamAngleParser(radicand.replace("x", r"\alpha"), atoms, denominators)
        .parse()
        .value
    )
    return value, root


def compile_absolute(formula):
    from .exam_trigonometric_methods import Equation

    text = clean(formula)
    if "|" not in text:
        return None
    plain = re.sub(r"\\[A-Za-z]+", "", text).replace("x", "")
    if re.search(r"[A-Za-z]", plain) or re.search(r"\\(?:alpha|beta|gamma)", text):
        raise UnsupportedCondition("the original absolute equation may contain only x")
    match = re.fullmatch(r"\|([^|]+)\|=\|([^|]+)\|", text)
    if not match:
        raise UnsupportedCondition(
            "one equality of two complete absolute values is required"
        )
    atoms, denominators = {}, []
    left, left_root = side(match[1], atoms, denominators)
    right, right_root = side(match[2], atoms, denominators)
    if not atoms or denominators:
        raise UnsupportedCondition(
            "the absolute-value method has no additional denominators"
        )
    scale = next(iter(atoms.values())).coefficient
    if scale <= 0 or any(
        a.function != "ctg"
        or a.coefficient != scale
        or not a.shift.is_Integer
        or a.variable != r"\alpha"
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "one positive multiple of the cotangent angle is required"
        )
    replacements = dict.fromkeys(atoms, -PARAMETER)
    if (
        left_root.xreplace(replacements) != PARAMETER
        or right_root.xreplace(replacements) != PARAMETER
    ):
        raise UnsupportedCondition(
            "both radicals must become the same nonnegative parameter"
        )
    left, right = (sp.expand(v.xreplace(replacements)) for v in (left, right))
    common = sp.expand((left + right) / 2)
    coefficient = sp.cancel((left - right) / (2 * R))
    if (
        not common.is_polynomial(PARAMETER)
        or sp.degree(common, PARAMETER) != 2
        or common.coeff(PARAMETER) != 0
        or common.has(R)
        or coefficient.free_symbols
        or coefficient == 0
    ):
        raise UnsupportedCondition(
            "the two sides must be a quadratic plus and minus the same radical term"
        )
    a, c = common.coeff(PARAMETER, 2), common.subs(PARAMETER, 0)
    value = sp.sqrt(sp.cancel(-c / a))
    if compare(value, sp.S.Zero) <= 0:
        raise UnsupportedCondition(
            "the reviewed quadratic must have one positive parameter root"
        )
    return Equation(U * (U + value), (), scale, (S,), absolute=(a, c, coefficient))


def proof(a):
    from .exam_trigonometric_proof import formula, series_lines
    from .exam_trigonometric_variants import argument

    coefficient, constant, radical = a.absolute
    t = PARAMETER
    angle = argument(a.scale)
    common = coefficient * t * t + constant
    term = radical * sp.sqrt(t)
    html = "<p>Котангенс определён, а подкоренное выражение неотрицательно:</p>"
    html += line(r"\sin(" + angle + r")\ne0")
    html += line("t=-" + formula(U, angle) + r",\quad t\ge0")
    html += line(
        r"\left|"
        + sp.latex(common + term)
        + r"\right|=\left|"
        + sp.latex(common - term)
        + r"\right|"
    )
    html += "<p>Модули равны тогда и только тогда, когда выражения под ними совпадают или противоположны. Рассмотрим оба случая:</p>"
    html += line(sp.latex(common + term) + "=" + sp.latex(common - term))
    html += line("2(" + sp.latex(term) + ")=0")
    html += line(sp.latex(common + term) + "=-(" + sp.latex(common - term) + ")")
    html += line("2(" + sp.latex(common) + ")=0")
    html += line(r"t=0\quad\text{или}\quad " + sp.latex(common) + "=0")
    value = sp.sqrt(sp.cancel(-constant / coefficient))
    html += line(r"t=\pm " + sp.latex(value))
    html += "<p>Отрицательное значение исключаем условием t ≥ 0. Получаем t = 0 или положительное значение:</p>"
    html += line("t=" + sp.latex(value))
    for level in (sp.S.Zero, -value):
        html += line(formula(U, angle) + "=" + sp.latex(level))
        for text in series_lines(
            tuple((q / a.scale, p / a.scale) for q, p in series((level,)))
        ):
            html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Решим равенство модулей заменой тригонометрической функции:</p>", html


def series(values):
    from .exam_trigonometric_inverse import level_series

    return tuple(
        (q - period if compare(value, sp.S.Zero) < 0 else q, period)
        for value in sorted(values, key=abs)
        for q, period in level_series(U, value)
    )
