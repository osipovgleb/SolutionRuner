"""Keep the parent's equality case, negative case and rationalization note."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization_proof import choices, system
from .logarithm_reciprocal_sum import analyze
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/reciprocal-sum.json"
    ).read_text()
)


def render(a):
    log = logarithm(a.G, sp.latex(a.A))
    constraints = [
        sp.latex(a.G) + ">0",
        sp.latex(a.A) + ">0",
        *(r"x\ne" + sp.latex(p) for p in a.poles),
    ]
    html = "<p>Сделаем замену. На исходной области определения второе слагаемое обратно первому:</p>"
    html += system(constraints)
    html += line("y=" + log + r",\quad y\ne0")
    html += line(
        r"y+\frac{1}{y}\le2\iff\frac{(y-1)^2}{y}\le0\iff\left[\begin{aligned}y<0\\y=1\end{aligned}\right."
    )
    html += "<p>Возвращаясь к исходной переменной, рассматриваем два случая:</p>"
    html += line(log + "=1")
    html += system([sp.latex(a.G) + "=" + sp.latex(a.A), *constraints])
    html += line(choices("x", a.equality))
    html += (
        "<p>Или логарифм отрицателен. На исходной области применим рационализацию:</p>"
    )
    html += line(log + "<0")
    html += system(
        [sp.latex(sp.Mul(a.A - 1, a.G - 1, evaluate=False)) + "<0", *constraints]
    )
    html += system(
        [sp.latex(sp.factor(a.negative_stage.original)) + "<0", choices("x", a.domain)]
    )
    html += line(choices("x", a.negative))
    html += "<p>Объединим решения двух случаев:</p>" + line(choices("x", a.solution))
    html += '<p>Примечание. На области определения неравенство <span data-inline-latex="\\log_a b&lt;0"></span> равносильно неравенству <span data-inline-latex="(a-1)(b-1)&lt;0"></span>.</p>'
    return html


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed reciprocal-logarithm parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets") or condition.get("asset_keys"):
        raise UnsupportedCondition(
            "the reviewed reciprocal-logarithm parent has no figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
