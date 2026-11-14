"""Keep the parent's reciprocal-sum method followed by its square method."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..core.condition_transcriptions import transcribe_condition
from ..probability.common import UnsupportedCondition, line
from ..word_problems.common import rewrite
from .expression_repair import with_condition_repair
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .logarithm_reciprocal_square import analyze
from .rational_inequality import set_latex
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/reciprocal-square.json"
    ).read_text()
)


def return_to_x(a, log):
    return (
        line(log + "=1")
        + line(sp.latex(a.argument) + "=" + sp.latex(a.base))
        + line(choices("x", a.solution))
    )


def render(a):
    log = logarithm(a.base, sp.latex(a.argument))
    inverse = r"\frac{1}{" + log + "}"
    log_square = r"\left(" + log + r"\right)^2"
    inverse_square = r"\frac{1}{" + log_square + "}"
    html = '<section data-content-kind="solution" data-solution-title="Решение">'
    html += "<p>Область определения исходных логарифмов:</p>"
    html += system([sp.latex(a.argument) + ">0", sp.latex(a.argument) + r"\ne1"])
    html += line(choices("x", a.domain))
    html += "<p>Перейдём к одному основанию, сохраняя исходную область:</p>"
    html += line(logarithm(a.argument, sp.latex(a.base)) + "=" + inverse)
    html += line(logarithm(a.base, sp.latex(a.argument**2)) + "=2" + log)
    html += line(logarithm(a.argument, sp.latex(a.base**2)) + "=2" + inverse)
    html += "<p>Пусть:</p>" + line("t=" + log + "+" + inverse)
    html += line(log_square + "+" + inverse_square + "=t^2-2")
    html += "<p>Тогда исходное неравенство равносильно:</p>"
    stage = a.outer_stage.original.subs(X, sp.Symbol("t", real=True))
    html += line(sp.latex(stage) + r"\le0")
    html += line(sp.latex(sp.factor(stage)) + r"\le0")
    html += line(choices("t", a.outer_stage.solution))
    html += "<p>Для ненулевого вещественного числа сумма с обратным числом не меньше двух при положительном числе и не больше минус двух при отрицательном. Поэтому:</p>"
    html += line(
        r"t\in\left((-\infty;-2]\cup[2;+\infty)\right)\cap"
        + set_latex(a.outer_stage.solution)
        + r"=\{2\}"
    )
    html += line(
        log + "+" + inverse + r"=2\iff\frac{(" + log + r"-1)^2}{" + log + "}=0"
    )
    html += return_to_x(a, log)
    html += "<p><b>Замечание.</b> Найденное значение удовлетворяет исходной области определения.</p></section>"
    html += '<section data-content-kind="solution" data-solution-title="Приведём другое решение:">'
    html += "<p>Преобразуем левую часть неравенства, выделив полные квадраты:</p>"
    if a.coefficient == 2:
        html += line(
            r"\left(" + log + r"-1\right)^2+\left(" + inverse + r"-1\right)^2\le0"
        )
        html += "<p>Оба квадрата неотрицательны, поэтому их сумма не превосходит нуля только тогда, когда каждый равен нулю:</p>"
        html += system([log + "-1=0", inverse + "-1=0"])
    else:
        html += line(r"\left(" + log + "+" + inverse + r"-2\right)^2\le0")
        html += "<p>Квадрат неотрицателен, поэтому выражение в скобках равно нулю:</p>"
        html += line(
            log + "+" + inverse + r"=2\iff\frac{(" + log + r"-1)^2}{" + log + "}=0"
        )
    return html + return_to_x(a, log) + "</section>"


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed two-method reciprocal-square parent is required"
        )
    (_, original, _, _), _ = read_formula(context)
    prepared, fixed = transcribe_condition(
        context, original, SOURCES["condition_transcriptions"], validate=read_formula
    )
    (content, condition, answer, solution), formula = read_formula(prepared)
    if content.get("assets") or condition.get("asset_keys"):
        raise UnsupportedCondition(
            "the reviewed reciprocal-square group has no figures"
        )
    a = analyze(formula)
    plan = repair(condition, answer, solution, a.answer, render(a))
    change = (
        rewrite(original, "condition", "Условие", fixed) if fixed is not None else None
    )
    return with_condition_repair(plan, change)
