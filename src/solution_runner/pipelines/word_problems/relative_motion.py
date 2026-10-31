"""Relative displacement is relative speed multiplied by elapsed time."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..probability.common import finish, line
from . import math_common, relative_motion_questions
from .common import UnsupportedCondition
from .math_common import fraction as frac
from .math_common import number as n


@dataclass(frozen=True)
class Analysis:
    question: relative_motion_questions.Question
    rate: sp.Rational
    displacement: sp.Rational
    result: sp.Rational


def cargo_analysis(q):
    displacement = sum(q.values.values()) / 1000
    rate = displacement * 3600 / q.time.total_seconds
    return Analysis(q, rate, displacement, rate)


def lap_speed_analysis(q):
    rate = q.values["distance"] * 3600 / q.time.total_seconds
    result = q.values["first"] - rate
    if result <= 0:
        raise UnsupportedCondition("positive speed for the overtaken car is required")
    return Analysis(q, rate, q.values["distance"], result)


def lap_chase_analysis(q):
    v = q.values
    rate = 60 * v["distance"] / v["lap_minutes"]
    bicycle = rate * v["catch_minutes"] / v["lag_minutes"]
    if bicycle * v["lag_minutes"] / 60 >= v["distance"]:
        raise UnsupportedCondition(
            "the cyclist must not have completed a lap before the motorcycle starts"
        )
    return Analysis(q, rate, v["distance"], bicycle + rate)


DIRECT_ANALYSES = {
    "cargo_pass": cargo_analysis,
    "lap_speed": lap_speed_analysis,
    "lap_chase": lap_chase_analysis,
}


def analyze(q):
    if q.kind in DIRECT_ANALYSES:
        return DIRECT_ANALYSES[q.kind](q)
    v = q.values
    if q.kind in {"pole", "forest"}:
        rate = v["speed"]
    elif q.kind in {"walk_gap", "opposite_points"}:
        rate = v["gap"]
    elif q.kind == "opposite_trains":
        rate = v["first"] + v["second"]
    else:
        rate = v["first"] - v["second"]
    if rate <= 0:
        raise UnsupportedCondition(
            "positive relative speed in the stated direction is required"
        )
    if q.kind in {"walk_gap", "opposite_points"}:
        displacement = v["distance"] / (1000 if q.kind == "walk_gap" else 2)
        result = 60 * displacement / rate
    else:
        displacement = rate * q.time.total_seconds / 3600
        result = (
            displacement
            if q.kind == "car_gap"
            else 1000 * displacement - v.get("obstacle", 0)
        )
    if result <= 0:
        raise UnsupportedCondition("positive train length or displacement is required")
    return Analysis(q, rate, displacement, result)


def calculate(context):
    data = math_common.read(context)
    return data, analyze(relative_motion_questions.parse(data[3]))


def rate_step(a, *, seconds=False):
    q, v = a.question, a.question.values
    if q.kind in {"pole", "forest"}:
        html = "<p>Скорость поезда переведём в нужные единицы:</p>"
    else:
        sign = "+" if q.kind == "opposite_trains" else "-"
        expression = n(v["first"]) + sign + n(v["second"])
        html = (
            "<p>При встречном движении скорости складываются:</p>"
            if sign == "+"
            else "<p>Скорость сближения равна разности скоростей:</p>"
        )
        html += line("u=" + expression + "=" + n(a.rate) + r"\,\mathrm{км}/\mathrm{ч}")
    if seconds:
        return html + line(
            n(a.rate)
            + r"\,\mathrm{км}/\mathrm{ч}="
            + frac(n(1000 * a.rate), "3600")
            + r"\,\mathrm{м}/\mathrm{с}="
            + n(a.rate * sp.Rational(5, 18))
            + r"\,\mathrm{м}/\mathrm{с}"
        )
    return html + line(
        n(a.rate)
        + r"\,\mathrm{км}/\mathrm{ч}="
        + frac(n(a.rate), "60")
        + r"\,\mathrm{км}/\mathrm{мин}="
        + n(a.rate / 60)
        + r"\,\mathrm{км}/\mathrm{мин}"
    )


def minute_proof(a):
    q = a.question
    seconds = q.time.total_seconds
    minutes = seconds / 60
    html = rate_step(a)
    if q.time.seconds:
        html += "<p>Выразим указанное время в минутах:</p>" + line(
            "t="
            + n(q.time.minutes)
            + "+"
            + frac(n(q.time.seconds), "60")
            + "="
            + n(minutes)
        )
    reference = "лесополосы" if q.kind == "forest" else "товарного поезда"
    html += (
        f"<p>За это время поезд сместится относительно {reference} на расстояние:</p>"
    )
    html += line(
        "S="
        + n(a.rate / 60)
        + r"\cdot"
        + n(minutes)
        + "="
        + n(a.displacement)
        + r"\,\mathrm{км}"
    )
    html += line(
        "S="
        + n(a.displacement)
        + r"\cdot1000="
        + n(1000 * a.displacement)
        + r"\,\mathrm{м}"
    )
    lengths = "поезда и лесополосы" if q.kind == "forest" else "двух поездов"
    html += f"<p>При полном прохождении расстояние равно сумме длин {lengths}. Поэтому искомая длина равна:</p>"
    return html + line(
        "L="
        + n(1000 * a.displacement)
        + "-"
        + n(q.values["obstacle"])
        + "="
        + n(a.result)
        + r"\,\mathrm{м}"
    )


def second_proof(a):
    q = a.question
    seconds = q.time.total_seconds
    rate_ms = a.rate * sp.Rational(5, 18)
    html = rate_step(a, seconds=True)
    if q.time.minutes:
        html += "<p>Переведём время в секунды:</p>" + line(
            "t="
            + n(q.time.minutes)
            + r"\cdot60+"
            + n(q.time.seconds)
            + "="
            + n(seconds)
        )
    if q.kind == "pole":
        html += "<p>За это время поезд проходит мимо придорожного столба расстояние, равное своей длине:</p>"
        return html + line(
            "L="
            + n(rate_ms)
            + r"\cdot"
            + n(seconds)
            + "="
            + n(a.result)
            + r"\,\mathrm{м}"
        )
    obstacle = n(q.values["obstacle"])
    html += "<p>Пусть длина искомого поезда равна x метрам. Чтобы один поезд полностью прошёл мимо другого, относительное смещение должно равняться сумме их длин:</p>"
    html += line("x+" + obstacle + "=" + n(rate_ms) + r"\cdot" + n(seconds))
    html += line("x+" + obstacle + "=" + n(1000 * a.displacement))
    return html + line(
        "x=" + n(1000 * a.displacement) + "-" + obstacle + "=" + n(a.result)
    )


def walking_proof(a):
    q = a.question
    distance = n(a.displacement)
    html = (
        "<p>Пусть v км/ч — скорость второго пешехода, тогда скорость первого равна:</p>"
    )
    html += line("v+" + n(a.rate))
    html += "<p>Переведём указанное расстояние в километры. Пусть через t часов расстояние между пешеходами станет равным этому значению:</p>"
    html += line(frac(n(q.values["distance"]), "1000") + "=" + distance)
    html += line(distance + "=(v+" + n(a.rate) + ")t-vt")
    html += line(distance + "=" + n(a.rate) + "t")
    hours = a.result / 60
    html += line("t=" + frac(distance, n(a.rate)) + "=" + n(hours) + r"\,\mathrm{ч}")
    return (
        html
        + "<p>Выразим полученное время в минутах:</p>"
        + line(n(hours) + r"\cdot60=" + n(a.result) + r"\,\mathrm{мин}")
    )


def car_proof(a):
    q = a.question
    html = "<p>Скорость удаления автомобилей друг от друга равна:</p>"
    html += line(
        "u="
        + n(q.values["first"])
        + "-"
        + n(q.values["second"])
        + "="
        + n(a.rate)
        + r"\,\mathrm{км}/\mathrm{ч}"
    )
    html += "<p>Переведём время после обгона в часы:</p>"
    hours = q.time.total_seconds / 3600
    conversion = frac(n(q.time.minutes), "60")
    if q.time.seconds:
        conversion += "+" + frac(n(q.time.seconds), "3600")
    html += line("t=" + conversion + "=" + n(hours) + r"\,\mathrm{ч}")
    return (
        html
        + "<p>Умножим скорость удаления на время:</p>"
        + line(
            "S="
            + n(a.rate)
            + r"\cdot"
            + n(hours)
            + "="
            + n(a.result)
            + r"\,\mathrm{км}"
        )
    )


def proof(a):
    from .relative_circle_proof import PROOFS
    from .water_relative_proof import cargo_pass

    kind = a.question.kind
    if kind == "cargo_pass":
        return cargo_pass(a)
    if kind in PROOFS:
        return PROOFS[kind](a)
    if kind == "walk_gap":
        return walking_proof(a)
    if kind == "car_gap":
        return car_proof(a)
    if kind == "same_trains":
        return (
            '<section data-content-kind="solution" data-solution-title="Решение">'
            + minute_proof(a)
            + '</section><section data-content-kind="solution" data-solution-title="Приведём другое решение">'
            + second_proof(a)
            + "</section>"
        )
    return minute_proof(a) if kind == "forest" else second_proof(a)


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(a.result), proof(a))
