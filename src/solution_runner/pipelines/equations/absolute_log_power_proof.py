"""Preserve the parent's common-power reductions on the full nonzero domain."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .absolute_log_power import analyze
from .exponential_inequality_preimage_proof import alternatives
from .inequality_plan import repair
from .logarithm_rationalization_proof import system
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/absolute-powers.json"
    ).read_text()
)


def logarithm(base, argument):
    return r"\log_{" + sp.latex(base) + r"}\left(" + sp.latex(argument) + r"\right)"


def power(base, exponent):
    return r"\left(" + sp.latex(base) + r"\right)^{" + exponent + "}"


def term(coefficient, value):
    return ("" if coefficient == 1 else sp.latex(coefficient) + r"\cdot ") + value


def left_reduction(a):
    L = logarithm(a.reference, X**2)
    scalar_log = logarithm(a.reference, a.base)
    abs_log = logarithm(a.reference, a.base**2)
    common = power(a.base, L)
    html = "<p>Преобразуем левую часть неравенства. При ненулевом x модуль положителен, а его квадрат равен квадрату x:</p>"
    html += line(
        r"|x|^{"
        + abs_log
        + r"}=|x|^{2"
        + scalar_log
        + r"}=(x^2)^{"
        + scalar_log
        + "}="
        + common
    )
    first_exponent = (sp.latex(a.shift) + "+" if a.shift else "") + L
    c1, c2 = a.coefficients
    html += line(
        term(c1, power(a.base, first_exponent))
        + "+"
        + term(c2, r"|x|^{" + abs_log + "}")
        + "="
        + term(c1 * a.base**a.shift, common)
        + "+"
        + term(c2, common)
        + "="
        + term(a.total, common)
    )
    return html


def right_reduction(a):
    L = logarithm(a.reference, a.argument)
    inverse_log = logarithm(1 / a.reference, a.argument)
    html = "<p>Преобразуем правую часть. При положительном аргументе переход к обратному основанию меняет знак логарифма:</p>"
    html += line(inverse_log + "=-" + L)
    html += line(
        term(a.total, power(1 / a.base, inverse_log))
        + "="
        + term(a.total, power(a.base, "-" + inverse_log))
        + "="
        + term(a.total, power(a.base, L))
    )
    return html


def render(a):
    extra = [r"x\ne" + sp.latex(p) for p in a.poles if p != 0]
    html = "<p>Учтём исходную область определения логарифмов:</p>"
    html += system([r"x^2>0", sp.latex(a.argument) + ">0", *extra])
    html += system([r"x\ne0", sp.latex(a.argument) + ">0", *extra])
    html += left_reduction(a) + right_reduction(a)
    html += "<p>Делим обе части на общий положительный коэффициент. Показательная и логарифмическая функции имеют основания больше единицы и возрастают:</p>"
    first = logarithm(a.reference, X**2)
    second = logarithm(a.reference, a.argument)
    html += line(
        power(a.base, first)
        + r"\le"
        + power(a.base, second)
        + r"\iff "
        + first
        + r"\le"
        + second
    )
    html += system(
        [
            r"x^2\le " + sp.latex(a.argument),
            r"x\ne0",
            sp.latex(a.argument) + ">0",
            *extra,
        ]
    )
    html += "<p>Перенесём всё влево и разложим квадратный трёхчлен на множители:</p>"
    html += line(
        sp.latex(a.stage.original)
        + r"\le0\iff "
        + sp.latex(sp.factor(a.stage.original))
        + r"\le0"
    )
    html += line(alternatives("x", a.stage.solution))
    html += "<p>Пересекаем полученный промежуток с исходной областью определения, исключая нуль и все исходные запрещённые точки:</p>"
    return html + line(alternatives("x", a.solution))


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed modulus/logarithmic power parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition("the reviewed power identity has no source figures")
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
