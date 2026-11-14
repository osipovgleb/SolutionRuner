"""Keep the parent complete square and prepare a visible verified condition fix."""

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
from .logarithm_square_factor import analyze
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/square-factor.json"
    ).read_text()
)


def render(a):
    logA = logarithm(a.base, sp.latex(a.A))
    logB = logarithm(a.base, sp.latex(a.B))
    html = "<p>Область определения неравенства задаётся условиями:</p>"
    html += system([sp.latex(arg.value) + ">0" for arg in a.arguments])
    html += line(choices("x", a.domain))
    html += "<p>Для таких значений переменной перейдём к общему основанию. Логарифм по обратному основанию меняет знак, а его квадрат остаётся прежним:</p>"
    if a.atoms[0].base != a.base:
        html += line(logarithm(a.atoms[0].base, sp.latex(a.A)) + "=-" + logA)
    html += line(
        sp.latex(a.atoms[1].argument) + "=" + sp.latex(sp.Pow(a.A, 2, evaluate=False))
    )
    html += line(logarithm(a.base, sp.latex(a.atoms[1].argument)) + "=2" + logA)
    log_square = (
        r"\log_{" + sp.latex(a.base) + r"}^{2}\left(" + sp.latex(a.A) + r"\right)"
    )
    html += line(r"\left(" + log_square + "-2" + logA + r"+1\right)" + logB + r"\le0")
    html += "<p>Выделим полный квадрат:</p>"
    html += line(r"\left(" + logA + r"-1\right)^2" + logB + r"\le0")
    html += "<p>Квадрат неотрицателен и обращается в нуль, когда первый логарифм равен единице. Знак второго логарифма на исходной области совпадает со знаком разности его аргумента и единицы. Поэтому применим рационализацию:</p>"
    html += line(
        r"\left("
        + sp.latex(a.A - a.base)
        + r"\right)^2\left("
        + sp.latex(a.B - 1)
        + r"\right)\le0"
    )
    html += "<p>Сохраняя исходную область определения, сначала учитываем равенство нулю квадратного множителя, затем неположительность второго логарифма:</p>"
    rows = [
        choices("x", part) for part in (a.zero_case, a.log_case) if part != sp.EmptySet
    ]
    result = (
        (r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right.")
        if len(rows) > 1
        else rows[0]
        if rows
        else r"\varnothing"
    )
    return html + line(result)


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed square-factor parent is required"
        )
    (_, original_condition, _, _), _ = read_formula(context)
    prepared, fixed_html = transcribe_condition(
        context,
        original_condition,
        SOURCES["condition_transcriptions"],
        validate=read_formula,
    )
    (content, condition, answer, solution), formula = read_formula(prepared)
    if content.get("assets") or condition.get("asset_keys"):
        raise UnsupportedCondition("the reviewed complete-square parent has no figures")
    a = analyze(formula)
    plan = repair(condition, answer, solution, a.answer, render(a))
    change = (
        rewrite(original_condition, "condition", "Условие", fixed_html)
        if fixed_html is not None
        else None
    )
    return with_condition_repair(plan, change)
