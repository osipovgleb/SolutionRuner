"""Keep the parent's two denominator-sign systems and justified root squaring."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_quadratic_proof import expression
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_radical import analyze
from .logarithm_rationalization_proof import choices, system
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (Path(__file__).parent / "assets/logarithmic-inequalities/radical.json").read_text()
)


def render(a):
    log = logarithm(a.base, "x")
    scaled = (sp.latex(a.scale) + r"\cdot" if a.scale != 1 else "") + log
    q = expression(a.radicand, "t")
    side = expression(a.side, "t")
    root = r"\sqrt{" + q + "}"
    numerator = side + "-" + root
    html = "<p>Логарифмы определены при x&gt;0. После замены</p>" + line("t=" + scaled)
    html += (
        "<p>исходная область определения требует неотрицательности подкоренного выражения и ненулевого знаменателя:</p>"
        + system([q + r"\ge0", r"t\ne0"])
    )
    html += "<p>Перенесём правую часть в числитель дроби:</p>" + line(
        r"\frac{1-"
        + root
        + r"}{t}<"
        + sp.latex(a.bound)
        + r"\iff\frac{"
        + numerator
        + r"}{t}<0"
    )
    html += "<p>Значит, получаем две системы в зависимости от знака знаменателя:</p>"
    html += (
        system([numerator + ">0", "t<0"])
        + "<p>или</p>"
        + system([numerator + "<0", "t>0"])
    )
    html += "<p>Решим первую систему. При t&lt;0 правая часть при переносе корня положительна, поэтому сравнение можно возвести в квадрат равносильно:</p>"
    html += system([root + "<" + side, "t<0"])
    html += system([q + r"<\left(" + side + r"\right)^2", q + r"\ge0", "t<0"])
    html += line(expression(sp.factor(a.negative_stage.original), "t") + "<0")
    html += line(choices("t", a.negative))
    html += (
        "<p>Возвращаясь к исходной переменной в первом случае, получаем:</p>"
        + line(choices(scaled, a.negative))
        + line(alternatives("x", a.negative_image))
    )
    html += "<p>Решим вторую систему. При t&gt;0 на исходной области определения правая часть также неотрицательна:</p>"
    html += line(
        (sp.latex(a.bound) if a.bound != 1 else "")
        + r"t\le "
        + sp.latex(a.bound / sp.sqrt(a.coefficient))
        + r"\le1"
    )
    html += system([root + ">" + side, "t>0"])
    html += system([q + r">\left(" + side + r"\right)^2", q + r"\ge0", "t>0"])
    html += line(expression(sp.factor(a.positive_stage.original), "t") + ">0")
    html += line(choices("t", a.positive))
    html += (
        "<p>Возвращаясь к исходной переменной во втором случае, получаем:</p>"
        + line(choices(scaled, a.positive))
        + line(alternatives("x", a.positive_image))
    )
    return (
        html
        + "<p>Объединяя два случая с сохранением исключённого знаменателем значения x=1, получаем решение исходного неравенства:</p>"
        + line(alternatives("x", a.solution))
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    if (
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
        not in SOURCES["parents"]
    ):
        raise UnsupportedCondition(
            "the complete reviewed logarithmic-root quotient parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition(
            "the reviewed logarithmic-root quotient has no source figures"
        )
    a = analyze(formula)
    return repair(condition, answer, solution, a.answer, render(a))
