"""Preserve variable-base rationalization and positive squared-log denominators."""

import hashlib
import json
from pathlib import Path

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_quadratic_proof import expression
from .inequality_plan import repair
from .logarithm_product_cancellation_proof import logarithm
from .logarithm_rationalization import (
    parts,
    ratio,
    scalar_text,
    square_denominator,
    square_image,
)
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import fraction
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/logarithmic-inequalities/rationalization.json"
    ).read_text()
)


def text(value, name):
    return sp.latex(value) if name == "x" else expression(value, name)


def log(base, value, name="x"):
    return logarithm(base.subs(X, sp.Symbol(name, real=True)), text(value, name))


def ref_log(a, value):
    name = a.coordinate.working
    return (
        a.style + r"\left(" + text(value, name) + r"\right)"
        if a.style
        else log(a.reference, value, name)
    )


def choices(name, solution):
    rows = [
        name + r"\in\mathbb R"
        if part == sp.S.Reals
        else alternatives(name, part, scalar_text)
        for part in parts(solution)
    ]
    if not rows:
        return r"\varnothing"
    return (
        rows[0]
        if len(rows) == 1
        else r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right."
    )


def system(rows):
    return line(r"\begin{cases}" + r"\\".join(rows) + r"\end{cases}")


def ratio_setup(a):
    name = a.coordinate.working
    html = ""
    if a.coordinate.shift is not None:
        radicand = X + a.coordinate.shift
        html += "<p>Сделаем замену, учитывая неотрицательность арифметического квадратного корня:</p>"
        html += line(
            name + "=" + sp.latex(sp.sqrt(radicand)) + r",\quad " + name + r"\ge0"
        )
        html += line("x=" + text(X**2 - a.coordinate.shift, name))
    html += "<p>Используя свойства логарифмов, упростим правую часть и логарифм степени в знаменателе:</p>"
    html += line(a.right_text + "=" + sp.latex(sp.Rational(1, a.power)))
    html += line(
        ref_log(a, sp.Pow(a.B, a.power, evaluate=False))
        + "="
        + str(a.power)
        + ref_log(a, a.B)
    )
    html += line(
        r"\frac{"
        + ref_log(a, a.A)
        + "}{"
        + str(a.power)
        + ref_log(a, a.B)
        + "}"
        + RELATION[a.operator]
        + sp.latex(sp.Rational(1, a.power))
    )
    html += (
        "<p>Умножим на положительное число "
        + str(a.power)
        + " и перейдём к переменному основанию на исходной области определения:</p>"
    )
    html += line(log(a.B, a.A, name) + RELATION[a.operator] + "1")
    html += line(log(a.B, sp.cancel(a.A / a.B), name) + RELATION[a.operator] + "0")
    return html


def ratio_constraints(a):
    name = a.coordinate.working
    rows = [text(a.B, name) + ">0", text(a.B, name) + r"\ne1", text(a.A, name) + ">0"]
    if a.coordinate.shift is not None:
        rows.append(name + r"\ge0")
    return rows


def ratio_systems(a):
    name = a.coordinate.working
    relation = RELATION[a.operator] + "0"
    html = "<p>Применим метод рационализации. При положительных аргументах знак логарифма по переменному основанию совпадает со знаком произведения разностей с единицей:</p>"
    raw = sp.Mul(a.B - 1, sp.Add(a.A / a.B, -1, evaluate=False), evaluate=False)
    html += system([*ratio_constraints(a), text(raw, name) + relation])
    html += "<p>На этой области знаменатель аргумента положителен. Уберём его и разложим произведение на множители:</p>"
    html += system(
        [*ratio_constraints(a), text(sp.factor(a.full_stage.original), name) + relation]
    )
    if a.removed:
        html += "<p>Общий квадрат положителен на исходной области, поэтому его можно сократить, сохраняя исключённые точки:</p>"
        for factor in a.removed:
            html += line(text(factor, name) + ">0")
    scalar = sp.cancel(a.stage.original / a.stage.expression)
    if scalar != 1:
        html += (
            "<p>Разделим на "
            + ("отрицательный" if scalar < 0 else "положительный")
            + " множитель "
            + sp.latex(scalar)
            + (
                " и изменим знак сравнения:</p>"
                if scalar < 0
                else ", сохраняя знак сравнения:</p>"
            )
        )
    if a.removed or scalar != 1:
        html += system(
            [
                *ratio_constraints(a),
                text(sp.factor(a.stage.expression), name)
                + RELATION[a.stage.sign_operator]
                + "0",
            ]
        )
    return html


def ratio_finish(a):
    name = a.coordinate.working
    frame = sp.S.Reals if a.coordinate.shift is None else sp.Interval(0, sp.oo)
    html = "<p>Решим условия положительности аргументов и учтём запрещённые значения основания:</p>"
    html += line(choices(name, a.domains[1].intersect(frame)))
    holes = [point for point in a.holes if frame.contains(point) is sp.true]
    if holes:
        html += line(
            r",\quad ".join(name + r"\ne" + scalar_text(point) for point in holes)
        )
    if a.domains[0] != sp.S.Reals:
        html += line(choices(name, a.domains[0].intersect(frame)))
    html += "<p>Решим полученное неравенство и пересечём решение со всеми исходными ограничениями:</p>"
    html += line(choices(name, a.stage.solution.intersect(frame)))
    html += line(choices(name, a.working_solution))
    if a.coordinate.shift is not None:
        html += "<p>Вернёмся к исходной переменной. На неотрицательной полуоси возведение в квадрат сохраняет порядок и открытость границ:</p>"
        html += line(
            choices(sp.latex(sp.sqrt(X + a.coordinate.shift)), a.working_solution)
        )
        if a.coordinate.shift != 0:
            html += line(
                choices(
                    sp.latex(X + a.coordinate.shift),
                    square_image(a.working_solution, 0),
                )
            )
        html += line(choices("x", a.solution))
    return html


def render_square(a):
    k = -a.level
    T = log(a.base, X**2)
    numerator = log(a.base, a.A) + "-" + log(a.base, a.B)
    square = r"\left(" + T + "+" + sp.latex(k) + r"\right)^2"
    html = "<p>Преобразуем знаменатель, используя свойство логарифма степени:</p>"
    html += line(log(a.base, X**4) + "=2" + T)
    html += line(
        r"\left("
        + T
        + r"\right)^2+"
        + sp.latex(2 * k)
        + T
        + "+"
        + sp.latex(k**2)
        + "="
        + square
    )
    html += line(
        r"\frac{" + numerator + "}{" + square + "}" + RELATION[a.operator] + "0"
    )
    html += line(log(a.base, a.threshold) + "=" + sp.latex(a.level))
    html += line(
        r"\frac{"
        + numerator
        + r"}{\left("
        + T
        + "-"
        + log(a.base, a.threshold)
        + r"\right)^2}"
        + RELATION[a.operator]
        + "0"
    )
    root = sp.sqrt(a.threshold)
    html += "<p>Исходный знаменатель не определён при x=0, равен нулю в двух указанных точках и положителен при остальных допустимых значениях:</p>"
    html += line(
        r"x\ne0,\quad x\ne-" + scalar_text(root) + r",\quad x\ne" + scalar_text(root)
    )
    html += "<p>Рационализируем разность логарифмов. Основание больше единицы, а оба квадратных знаменателя положительны и имеют одинаковые нули:</p>"
    rows = [sp.latex(a.A) + ">0", sp.latex(a.B) + ">0", r"x^2>0"]
    html += system(
        [
            fraction(a.A - a.B, sp.Pow(X**2 - a.threshold, 2, evaluate=False))
            + RELATION[a.operator]
            + "0",
            *rows,
        ]
    )
    denominator = sp.Mul((X - root) ** 2, (X + root) ** 2, evaluate=False)
    html += system(
        [fraction(a.A - a.B, denominator) + RELATION[a.operator] + "0", *rows]
    )
    html += (
        "<p>Остаётся решить линейное сравнение и сохранить все исключённые точки:</p>"
    )
    html += system(
        [
            sp.latex(a.A - a.B) + RELATION[a.operator] + "0",
            sp.latex(a.A) + ">0",
            sp.latex(a.B) + ">0",
            r"x\ne0",
            r"x\ne-" + scalar_text(root),
            r"x\ne" + scalar_text(root),
        ]
    )
    return html + line(choices("x", a.solution))


def build_context_repair_plan(
    context, *, parent_solution_html="", method="ratio_rationalization"
):
    if (
        SOURCES["parents"].get(
            hashlib.sha256(parent_solution_html.encode()).hexdigest()
        )
        != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed rationalization parent is required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    if content.get("assets"):
        raise UnsupportedCondition("these rationalization parents have no figures")
    if method == "ratio_rationalization":
        a = ratio(formula)
        html = ratio_setup(a) + ratio_systems(a) + ratio_finish(a)
    elif method == "square_denominator":
        a = square_denominator(formula)
        html = render_square(a)
    else:
        raise UnsupportedCondition("unknown rationalization parent method")
    return repair(condition, answer, solution, a.answer, html)
