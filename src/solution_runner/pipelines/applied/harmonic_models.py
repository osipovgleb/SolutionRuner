"""Exact spring velocity and kinetic energy for sine and cosine oscillations."""

import re
from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..probability.common import UnsupportedCondition, finish, line
from . import common
from .physical_questions import VALUE, scalar

_QUESTION = re.compile(
    rf"Груз массой (?P<mass>{VALUE}) кг колеблется на пружине\. Его скорость v меняется по закону v=(?P<velocity>.+?), где t — время с момента начала колебаний, T=(?P<period>{VALUE}) с — период колебаний, v_0=(?P<amplitude>{VALUE}) м/с\. Кинетическая энергия E\(в джоулях\)груза вычисляется по формуле E=(?P<energy>.+?), где m — масса груза в килограммах, v — скорость груза в м/с\. Найдите кинетическую энергию груза через (?P<time>{VALUE}) секунд(?:у|ы)? после начала колебаний\. Ответ дайте в джоулях\."
)


@dataclass(frozen=True)
class Question:
    mass: sp.Rational
    period: sp.Rational
    amplitude: sp.Rational
    time: sp.Rational
    function: str
    source: dict[str, str]


@dataclass(frozen=True)
class Analysis:
    question: Question
    phase: sp.Expr
    factor: sp.Expr
    velocity: sp.Expr
    result: sp.Rational


def parse(text):
    match = _QUESTION.fullmatch(text)
    if not match:
        raise UnsupportedCondition(
            "the complete spring-energy question must be recognized"
        )
    velocity = re.fullmatch(
        r"v_0\\(?P<function>sin|cos)\\frac\{2\\pit\}\{T\}",
        re.sub(r"\s+", "", match["velocity"]),
    )
    energy = re.sub(r"\s+", "", match["energy"])
    if not velocity or energy not in [r"\frac{mv^{2}}{2}", r"\frac{mv^2}{2}"]:
        raise UnsupportedCondition(
            "the formulas must be the spring velocity and kinetic-energy laws"
        )
    source = {
        key: match[key].replace("{,}", ",").replace(",", "{,}")
        for key in ["mass", "period", "amplitude", "time"]
    }
    values = {key: scalar(value) for key, value in source.items()}
    if (
        any(values[key] <= 0 for key in ["mass", "period", "amplitude"])
        or values["time"] < 0
    ):
        raise UnsupportedCondition(
            "positive spring parameters and nonnegative time are required"
        )
    return Question(**values, function=velocity["function"], source=source)


def analyze(q):
    phase = 2 * sp.pi * q.time / q.period
    factor = {"sin": sp.sin, "cos": sp.cos}[q.function](phase)
    velocity = sp.simplify(q.amplitude * factor)
    energy = sp.simplify(q.mass * velocity**2 / 2)
    if energy.is_Rational is not True:
        raise UnsupportedCondition("the exact energy must be rational without rounding")
    return Analysis(q, phase, factor, velocity, energy)


def proof(a):
    q = a.question
    source = q.source
    trig = chr(92) + q.function
    html = "<p>Найдём скорость груза в указанный момент после начала колебаний:</p>"
    html += line(r"v=v_0" + trig + r"\frac{2\pi t}{T}")
    html += line(
        r"\frac{2\pi t}{T}=\frac{2\pi\cdot ("
        + source["time"]
        + ")}{"
        + source["period"]
        + "}="
        + sp.latex(a.phase)
    )
    html += line(
        "v=("
        + source["amplitude"]
        + r")\cdot"
        + trig
        + r"\left("
        + sp.latex(a.phase)
        + r"\right)"
    )
    html += line(
        "v=("
        + source["amplitude"]
        + r")\cdot\left("
        + sp.latex(a.factor)
        + r"\right)="
        + sp.latex(a.velocity)
        + r"\,\mathrm{м}/\mathrm{с}"
    )
    html += "<p>Найдём кинетическую энергию груза. В формулу подставляем квадрат полученной скорости:</p>"
    html += line(r"E=\frac{mv^2}{2}")
    html += line(
        r"E=\frac{("
        + source["mass"]
        + r")\cdot\left("
        + sp.latex(a.velocity)
        + r"\right)^2}{2}"
    )
    return html + line("E=" + sp.latex(a.result) + r"\,\mathrm{Дж}")


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, analysis = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(analysis.result), proof(analysis))
