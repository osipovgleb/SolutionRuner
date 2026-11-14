"""Preserve the parent's two upper bounds and joint equality conditions."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .absolute_inequality_proof import absolute
from .exponential_inequality_preimage_proof import alternatives
from .exponential_log_bound import analyze
from .inequality_plan import repair
from .logarithm_rationalization_proof import system
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/exponential-inequalities/log-bound.json"
    ).read_text()
)


def logarithm(base, argument):
    return r"\log_{" + sp.latex(base) + r"}\left(" + sp.latex(argument) + r"\right)"


def render(a):
    power = sp.latex(a.base) + "^{" + "-" + absolute(a.absolute_argument) + "}"
    log = logarithm(a.log_base, a.argument)
    html = "<p>Покажем, что на области определения левая часть неравенства не больше единицы. Сначала учтём область определения логарифма и все исходные запрещённые точки:</p>"
    html += line(sp.latex(a.argument) + ">0")
    if a.poles:
        html += line(r",\quad ".join(r"x\ne" + sp.latex(p) for p in a.poles))
    html += line(alternatives("x", a.domain))
    html += (
        "<p>Показатель степени неположителен, а основание больше единицы, поэтому:</p>"
    )
    html += line("0<" + power + r"\le " + sp.latex(a.base) + "^0=1")
    html += "<p>Выделим квадрат в аргументе логарифма:</p>"
    square = sp.Pow(a.absolute_argument, 2, evaluate=False)
    html += line(
        sp.latex(a.argument)
        + "="
        + sp.latex(a.log_base)
        + "-"
        + sp.latex(square)
        + r"\le "
        + sp.latex(a.log_base)
    )
    html += line(log + r"\le " + logarithm(a.log_base, a.log_base) + "=1")
    html += "<p>Если логарифм неположителен, произведение также неположительно. Если он положителен, оба множителя положительны и не превосходят единицы. Следовательно, произведение не больше единицы, и исходное неравенство выполняется только при равенстве обоих множителей единице:</p>"
    html += system([log + "=1", power + "=1"])
    html += system(
        [
            sp.latex(a.log_base) + "-" + sp.latex(square) + "=" + sp.latex(a.log_base),
            absolute(a.absolute_argument) + "=0",
        ]
    )
    html += line(sp.latex(a.absolute_argument) + "=0" + r"\iff x=" + sp.latex(a.center))
    if a.solution == sp.EmptySet:
        html += "<p>Полученная точка запрещена исходным знаменателем, поэтому допустимых решений нет.</p>"
    else:
        html += "<p>Полученная точка принадлежит области определения: аргумент логарифма равен его основанию, показатель степени равен нулю, оба множителя равны единице.</p>"
    return html


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed product-bound parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "the reviewed upper-bound product has no source figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
