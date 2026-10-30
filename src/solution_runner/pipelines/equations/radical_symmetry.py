"""Prove symmetric ratios and antisymmetric sums of real odd-root functions."""

import re

from ..probability.common import UnsupportedCondition, finish, line
from ..triangles.isosceles.planner import _section
from .expression_condition import read_math_markup
from .power_arithmetic import clean


def _read(context, ratio):
    content, condition, formulas, text = read_math_markup(context, indexed=True)
    pattern = r"Найдите \ufff00, если \ufff01(?:,? при \ufff02)?\.?"
    if (
        content.get("assets")
        or condition.get("asset_keys")
        or len(formulas) != (3 if ratio else 2)
        or not re.fullmatch(pattern, text)
    ):
        raise UnsupportedCondition("a complete root-function question is required")
    return content, condition, [clean(f) for f in formulas]


def _root(n, text):
    return rf"\sqrt[{n}]{{{text}}}"


def build_symmetric_ratio_plan(context):
    content, condition, formulas = _read(context, True)
    query = re.fullmatch(r"\\frac\{g\((\d+)-x\)\}\{g\((\d+)\+x\)\}", formulas[0])
    definition = re.fullmatch(r"g\(x\)=\\sqrt\[(\d+)\]\{x\((\d+)-x\)\}", formulas[1])
    exclusion = re.fullmatch(r"\|x\|\\ne(\d+)", formulas[2])
    if not query or not definition or not exclusion:
        raise UnsupportedCondition("unsupported symmetric root-function ratio")
    d, n, c = int(query[1]), int(definition[1]), int(definition[2])
    if (
        d != int(query[2])
        or d != int(exclusion[1])
        or c != 2 * d
        or not 1 <= d <= 10**6
        or not 3 <= n <= 99
        or n % 2 != 1
    ):
        raise UnsupportedCondition(
            "the odd-root symmetry and nonzero domain do not match"
        )
    a = rf"({d}-x)({d}+x)"
    b = rf"({d}+x)({d}-x)"
    html = "<p>Подставим оба аргумента в определение функции:</p>"
    html += line(rf"g({d}-x)=" + _root(n, rf"({d}-x)({c}-({d}-x))") + "=" + _root(n, a))
    html += line(rf"g({d}+x)=" + _root(n, rf"({d}+x)({c}-({d}+x))") + "=" + _root(n, b))
    html += "<p>Подкоренные произведения равны. Корень нечётной степени определён для любого вещественного подкоренного числа:</p>"
    html += line(a + "=" + b)
    html += line(rf"g({d}-x)=g({d}+x)")
    html += (
        "<p>По условию знаменатель не равен нулю, поэтому отношение равно единице:</p>"
    )
    html += line(rf"|x|\ne {d}\ \Longrightarrow\ ({d}+x)({d}-x)\ne0")
    html += line(formulas[0] + rf"=\frac{{g({d}+x)}}{{g({d}+x)}}=1")
    return finish(
        condition, _section(content, "answer"), _section(content, "solution"), "1", html
    )


def build_antisymmetric_sum_plan(context):
    content, condition, formulas = _read(context, False)
    query = re.fullmatch(r"h\((\d+)\+x\)\+h\((\d+)-x\)", formulas[0])
    definition = re.fullmatch(
        r"h\(x\)=\\sqrt\[(\d+)\]\{x\}\+\\sqrt\[(\d+)\]\{x-(\d+)\}", formulas[1]
    )
    if not query or not definition:
        raise UnsupportedCondition("unsupported antisymmetric root-function sum")
    d, n, c = int(query[1]), int(definition[1]), int(definition[3])
    if (
        d != int(query[2])
        or n != int(definition[2])
        or c != 2 * d
        or not 1 <= d <= 10**6
        or not 3 <= n <= 99
        or n % 2 != 1
    ):
        raise UnsupportedCondition("the odd-root antisymmetry does not hold")
    plus = _root(n, rf"x+{d}")
    minus = _root(n, rf"x-{d}")
    html = "<p>Подставим аргументы в формулу функции:</p>"
    html += line(rf"h({d}+x)=" + _root(n, rf"{d}+x") + "+" + _root(n, rf"{d}+x-{c}"))
    html += line(rf"h({d}+x)={plus}+{minus}")
    html += line(rf"h({d}-x)=" + _root(n, rf"{d}-x") + "+" + _root(n, rf"{d}-x-{c}"))
    html += (
        "<p>Корень нечётной степени меняет знак при смене знака подкоренного числа:</p>"
    )
    html += line(r"\sqrt[2k+1]{-u}=-\sqrt[2k+1]{u}")
    html += line(rf"h({d}-x)=-{minus}-{plus}")
    html += "<p>Сложим выражения и сократим противоположные слагаемые:</p>"
    html += line(formulas[0] + rf"=({plus}+{minus})+(-{minus}-{plus})=0")
    return finish(
        condition, _section(content, "answer"), _section(content, "solution"), "0", html
    )
