"""Keep the parents' positive reciprocal substitution and two sign cases."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .absolute_inequality_proof import absolute, alternative_rows
from .absolute_power_inequality import reciprocal, signed_exponent
from .exponential_inequality_preimage_proof import alternatives
from .inequality_plan import repair
from .logarithm_rationalization_proof import system
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION

SOURCES = json.loads(
    (Path(__file__).parent / "assets/absolute-inequalities/powers.json").read_text()
)


def reciprocal_proof(a):
    power = absolute(a.argument) + "^{" + sp.latex(a.exponent) + "}"
    html = "<p>Обе степени имеют смысл одновременно только при ненулевом основании. На этой области модуль строго положителен:</p>"
    html += line(absolute(a.argument) + r"\ne0\iff " + sp.latex(a.argument) + r"\ne0")
    html += line(r",\quad ".join(r"x\ne" + sp.latex(p) for p in a.poles))
    html += "<p>Сделаем замену:</p>" + line("t=" + power + r",\quad t>0")
    html += "<p>Вторая степень обратна первой, поэтому получаем:</p>"
    html += line(
        r"t+\frac{1}{t}\le2\iff\frac{t^2-2t+1}{t}\le0\iff\frac{(t-1)^2}{t}\le0"
    )
    html += "<p>Знаменатель положителен, а квадрат неотрицателен. Неравенство выполняется только при t=1:</p>"
    html += line("t=1")
    html += "<p>Положительная степень равна единице, если её основание равно единице или показатель равен нулю. Сохраняем исходные ограничения:</p>"
    html += line(power + "=1")
    html += alternative_rows(
        [
            absolute(a.argument) + "=1",
            r"\begin{cases}"
            + sp.latex(a.exponent)
            + r"=0\\"
            + sp.latex(a.argument)
            + r"\ne0\end{cases}",
        ]
    )
    html += alternative_rows(
        [
            sp.latex(a.argument) + "=1",
            sp.latex(a.argument) + "=-1",
            sp.latex(a.exponent) + "=0",
        ]
    )
    html += "<p>Решим полученные линейные уравнения:</p>"
    html += alternative_rows([alternatives("x", s.solution) for s in a.branches])
    return (
        html
        + "<p>Объединяем решения и исключаем все исходные запрещённые точки:</p>"
        + line(alternatives("x", a.solution))
    )


def signed_proof(a):
    exponent = a.exponent.subs(a.symbol, sp.Abs(X, evaluate=False))
    power = sp.latex(a.base) + "^{" + sp.latex(exponent) + "}"
    direction = "возрастает" if a.base > 1 else "убывает"
    html = (
        "<p>Запишем единицу как нулевую степень того же основания. Показательная функция "
        + direction
        + ":</p>"
    )
    html += line(
        power
        + RELATION[a.operator]
        + sp.latex(a.base)
        + "^0"
        + r"\iff "
        + sp.latex(exponent)
        + RELATION[a.exponent_operator]
        + "0"
    )
    for sign, stage, solution in a.cases:
        domain = r"x\ge0" if sign == 1 else r"x\le0"
        modulus = "x" if sign == 1 else "-x"
        html += (
            "<p>Рассмотрим "
            + ("первый" if sign == 1 else "второй")
            + " случай. При "
            + ("неотрицательном" if sign == 1 else "неположительном")
            + " x модуль равен "
            + modulus
            + ":</p>"
        )
        restrictions = [r"x\ne" + sp.latex(p) for p in stage.poles]
        html += system(
            [
                domain,
                sp.latex(stage.original) + RELATION[a.exponent_operator] + "0",
                *restrictions,
            ]
        )
        numerator, denominator = sp.fraction(stage.original)
        html += system(
            [
                domain,
                fraction(sp.factor(numerator), sp.factor(denominator))
                + RELATION[a.exponent_operator]
                + "0",
                *restrictions,
            ]
        )
        html += line(alternatives("x", solution))
    return (
        html
        + "<p>Объединяя результаты двух случаев, получаем:</p>"
        + line(alternatives("x", a.solution))
    )


def build_context_repair_plan(context, *, method, parent_solution_html=""):
    if (
        method not in SOURCES["parents"]
        or hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"][method]
    ):
        raise UnsupportedCondition(
            "the complete reviewed absolute-power parent method is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "these absolute-power parents have no source figures"
        )
    a = reciprocal(formula) if method == "reciprocal" else signed_exponent(formula)
    html = reciprocal_proof(a) if method == "reciprocal" else signed_proof(a)
    return repair(condition, answer, solution, a.answer, html)
