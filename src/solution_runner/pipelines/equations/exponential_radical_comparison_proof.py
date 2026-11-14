"""Follow the parent's substitution, domain, two cases and inverse substitution."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic_proof import expression
from .exponential_radical_comparison import analyze
from .inequality_plan import repair
from .logarithm_rationalization_proof import choices, system
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/exponential-inequalities/root-comparison.json"
    ).read_text()
)


def render(a):
    q, r = expression(a.radicand, "t"), expression(a.right, "t")
    html = "<p>Пусть</p>" + line("t=" + power(a.base, a.exponent) + r",\quad t>0")
    html += "<p>Тогда данное неравенство принимает вид:</p>" + line(
        r"\sqrt{" + q + r"}\ge " + r
    )
    html += "<p>Область определения этого неравенства задаётся условием:</p>"
    html += line(q + r"\ge0\iff " + expression(sp.factor(a.radicand), "t") + r"\ge0")
    html += line(choices("t", a.domain))
    html += "<p>Рассмотрим два случая. В первом случае</p>" + line(
        choices("t", a.negative_case)
    )
    html += "<p>левая часть неравенства неотрицательна, а правая отрицательна, следовательно, неравенство выполняется при всех таких значениях.</p>"
    html += "<p>Во втором случае</p>" + line(choices("t", a.nonnegative_case))
    html += "<p>обе части неотрицательны, поэтому можно возвести их в квадрат, сохранив равносильность:</p>"
    html += system([r"\sqrt{" + q + r"}\ge " + r, choices("t", a.nonnegative_case)])
    html += system(
        [
            expression(sp.factor(a.radicand), "t") + r"\ge \left(" + r + r"\right)^2",
            choices("t", a.nonnegative_case),
        ]
    )
    html += system(
        [
            expression(sp.factor(a.radicand - a.right**2), "t") + r"\ge0",
            choices("t", a.nonnegative_case),
        ]
    )
    html += line(choices("t", a.nonnegative_case.intersect(a.square_stage.solution)))
    html += "<p>Объединяя решения двух случаев и возвращаясь к исходной переменной, получаем:</p>"
    html += line(choices(power(a.base, a.exponent), a.positive_solution))
    return html + line(alternatives("x", a.solution, a.endpoint))


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed exponential-root comparison parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "the reviewed exponential-root comparison has no source figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
