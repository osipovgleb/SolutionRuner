"""One polynomial motion family evaluates velocity or solves for its time."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition, finish, line
from .common import T, answer, polynomial, read, real_roots

_NUMBER = r"[−-]?\d+(?:[,.]\d+)?"
_DEFINITIONS = (
    r"\(где x — расстояние от точки отсчета в метрах, t — время в секундах, измеренное с начала движения\)\.",
    r"где x — расстояние от точки отсчета в метрах, t — время в секундах, прошедшее с начала движения\.",
    r", где x — расстояние от точки отсчета \(в метрах\), t — время движения \(в секундах\)\.",
)


def _question(text):
    pattern = (
        r"Материальная точка движется прямолинейно по закону x\(t\)\s*=\s*(?P<law>.+?)\s*(?P<definition>"
        + "|".join(_DEFINITIONS)
        + r") (?P<query>.+)"
    )
    match = re.fullmatch(pattern, text)
    if not match:
        raise UnsupportedCondition("unsupported complete polynomial motion question")
    query = match["query"].replace(r"\,\mathrm{с}", " с")
    evaluate = re.fullmatch(
        r"Найдите ее скорость \((?:в м/[сc]|в метрах в секунду)\) в момент времени t\s*=\s*(?P<value>"
        + _NUMBER
        + r")\s*[сc]\.",
        query,
    )
    solve = re.fullmatch(
        r"В какой момент времени \(в секундах\) ее скорость была равна (?P<value>"
        + _NUMBER
        + r") м/[сc]\?",
        query,
    )
    if not evaluate and not solve:
        raise UnsupportedCondition(
            "a velocity value or its nonnegative time must be requested"
        )
    value = sp.Rational(
        (evaluate or solve)["value"].replace(",", ".").replace("−", "-")
    )
    return polynomial(match["law"], T), value, bool(evaluate)


def build_context_repair_plan(context):
    condition, current_answer, solution, text = read(context)
    law, value, evaluate = _question(text)
    velocity = sp.diff(law, T)
    html = "<p>Скорость найдём как производную данного закона движения по времени:</p>"
    html += line(r"v(t)=x'(t),\quad (t^n)'=nt^{n-1}")
    html += line("x(t)=" + sp.latex(law))
    html += line("v(t)=" + sp.latex(velocity))
    if evaluate:
        if value < 0:
            raise UnsupportedCondition(
                "time measured from the start cannot be negative"
            )
        result = sp.simplify(velocity.subs(T, value))
        substitution = sp.latex(velocity, symbol_names={T: "(" + sp.latex(value) + ")"})
        html += "<p>Подставим заданный момент времени:</p>" + line(
            "t=" + sp.latex(value)
        )
        html += line("v(" + sp.latex(value) + ")=" + substitution)
        html += line(substitution + "=" + sp.latex(result) + r"\;\mathrm{м}/\mathrm{с}")
    else:
        equation = sp.expand(velocity - value)
        roots = real_roots(equation, T)
        valid = [r for r in roots if r.is_nonnegative is True]
        if len(valid) != 1:
            raise UnsupportedCondition(
                "the motion question does not determine one nonnegative time"
            )
        result = valid[0]
        html += "<p>Приравняем скорость заданному значению и решим уравнение:</p>"
        html += line(sp.latex(velocity) + "=" + sp.latex(value))
        html += line(sp.latex(equation) + "=0")
        html += line(r"t\in\{" + ",".join(sp.latex(r) for r in roots) + r"\}")
        html += "<p>Оставим время, не меньшее нуля, поскольку оно отсчитывается от начала движения:</p>"
        html += line(r"t\ge0,\quad t=" + sp.latex(result) + r"\;\mathrm{с}")
    return finish(condition, current_answer, solution, answer(result), html)
