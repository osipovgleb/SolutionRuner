"""Preserve substitution, all logarithm domains, absolute values and the correct back exponent."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .inequality_plan import repair
from .logarithm_factored_power import analyze
from .logarithm_factored_power_input import read_context
from .logarithm_rationalization_proof import system

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/factored-powers.json"
    ).read_text()
)


def power(base, exponent):
    return sp.latex(base) + "^{" + str(exponent) + "}"


def logarithm(base, argument):
    return r"\log_{" + sp.latex(base) + r"}\left(" + argument + r"\right)"


def pieces(a):
    P = "t-" + sp.latex(a.left_constant)
    Q = power(a.base, a.high_shift) + "t-1"
    R = power(a.base, a.middle_shift) + "t-" + sp.latex(a.right_constant)
    bound = power(a.base, -a.high_shift)
    return P, Q, R, bound


def domain_proof(a):
    P, Q, R, bound = pieces(a)
    html = "<p>Сделаем замену:</p>" + line(
        "t=" + power(a.base, "-x^2") + r",\qquad 0<t\le1"
    )
    html += "<p>Исходное неравенство принимает вид:</p>"
    html += line(
        logarithm(a.log_base, "(" + P + ")(" + Q + ")")
        + "+"
        + logarithm(a.log_base, r"\frac{" + P + "}{" + Q + "}")
        + ">"
        + logarithm(a.log_base, "(" + R + ")^2")
    )
    html += "<p>Сохраняем области всех трёх логарифмов и исходный знаменатель:</p>"
    html += system(
        [
            "(" + P + ")(" + Q + ")>0",
            r"\frac{" + P + "}{" + Q + "}>0",
            Q + r"\ne0",
            "(" + R + ")^2>0",
            r"0<t\le1",
        ]
    )
    html += "<p>Первый множитель отрицателен, поэтому положительность произведения и частного требует отрицательности второго:</p>"
    html += line(
        "t"
        + r"\le1<"
        + sp.latex(a.left_constant)
        + r"\quad\Longrightarrow\quad "
        + P
        + "<0"
    )
    html += line(Q + r"<0\iff 0<t<" + bound)
    html += "<p>Показатель средней степени меньше старшего, поэтому на этом промежутке третья разность также отрицательна:</p>"
    html += line(
        power(a.base, a.middle_shift)
        + "t<"
        + power(a.base, a.middle_shift - a.high_shift)
        + r"<1\le"
        + sp.latex(a.right_constant)
        + r"\quad\Longrightarrow\quad "
        + R
        + "<0"
    )
    return html


def comparison_proof(a):
    P, Q, R, bound = pieces(a)
    html = "<p>На найденной области оба слагаемых определены. Складываем логарифмы и сокращаем только ненулевой множитель:</p>"
    html += line(
        logarithm(a.log_base, "(" + P + ")(" + Q + ")")
        + "+"
        + logarithm(a.log_base, r"\frac{" + P + "}{" + Q + "}")
        + "="
        + logarithm(a.log_base, "(" + P + ")^2")
    )
    html += "<p>Основание логарифма больше единицы. Сравним квадраты, затем модули:</p>"
    html += system(
        [
            logarithm(a.log_base, "(" + P + ")^2")
            + ">"
            + logarithm(a.log_base, "(" + R + ")^2"),
            "0<t<" + bound,
        ]
    )
    html += line("(" + P + ")^2>(" + R + r")^2\iff |" + P + "|>|" + R + "|")
    html += "<p>Обе разности отрицательны на исходной области, поэтому раскрываем модули:</p>"
    html += line(
        sp.latex(a.left_constant)
        + "-t>"
        + sp.latex(a.right_constant)
        + "-"
        + power(a.base, a.middle_shift)
        + r"t\iff ("
        + power(a.base, a.middle_shift)
        + "-1)t>"
        + sp.latex(a.right_constant - a.left_constant)
    )
    html += "<p>Левая часть строго положительна, а правая неположительна. Это сравнение не добавляет ограничений:</p>"
    html += line(
        "("
        + power(a.base, a.middle_shift)
        + r"-1)t>0\ge"
        + sp.latex(a.right_constant - a.left_constant)
    )
    return html


def render(a):
    html = domain_proof(a) + comparison_proof(a)
    html += (
        "<p>Возвращаемся к исходной переменной. Показательная функция возрастает:</p>"
    )
    html += line(
        power(a.base, "-x^2")
        + "<"
        + power(a.base, -a.high_shift)
        + r"\iff -x^2<-"
        + sp.latex(a.high_shift)
        + r"\iff x^2>"
        + sp.latex(a.high_shift)
    )
    if a.poles:
        html += "<p>Исключаем также все исходные запрещённые точки:</p>" + line(
            r",\quad ".join(r"x\ne" + sp.latex(p) for p in a.poles)
        )
    return html + line(alternatives("x", a.solution))


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed factored logarithm-power parent is required"
        )
    (content, condition, answer, solution), formula = read_context(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "the reviewed factored logarithm powers have no source figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
