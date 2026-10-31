"""Average speed is total distance divided by total travel time."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from ..calculus.common import answer
from ..probability.common import finish, line
from . import math_common
from .common import UnsupportedCondition
from .math_common import fraction as frac
from .math_common import number as n
from .motion_questions import HOUR, duration

_END = r" Найдите среднюю скорость автомобиля на протяжении всего пути\. Ответ дайте в км/ч\."
_PATTERNS = {
    "equal_time": rf"Половину времени, затраченного на дорогу, автомобиль ехал со скоростью (?P<v1>{VALUE}) км/ч, а вторую половину времени — со скоростью (?P<v2>{VALUE}) км/ч\.",
    "equal_distance": rf"Первую треть трассы автомобиль ехал со скоростью (?P<v1>{VALUE}) км/ч, вторую треть — со скоростью (?P<v2>{VALUE}) км/ч, а последнюю — со скоростью (?P<v3>{VALUE}) км/ч\.",
    "time": rf"Перв(?:ые|ый) (?P<t1>{HOUR}) автомобиль ехал со скоростью (?P<v1>{VALUE}) км/ч, следующ(?:ий|ие) (?P<t2>{HOUR}) — со скоростью (?P<v2>{VALUE}) км/ч, а затем (?P<t3>{HOUR}) — со скоростью (?P<v3>{VALUE}) км/ч\.",
    "distance": rf"Первые (?P<s1>{VALUE}) км автомобиль ехал со скоростью (?P<v1>{VALUE}) км/ч, следующие (?P<s2>{VALUE}) км — со скоростью (?P<v2>{VALUE}) км/ч, а затем (?P<s3>{VALUE}) км — со скоростью (?P<v3>{VALUE}) км/ч\.",
}


@dataclass(frozen=True)
class Question:
    kind: str
    speeds: tuple
    weights: tuple

    @property
    def by_time(self):
        return self.kind in {"equal_time", "time"}


def parse(text):
    for kind, pattern in _PATTERNS.items():
        match = re.fullmatch(pattern + _END, text)
        if match:
            size = 2 if kind == "equal_time" else 3
            speeds = tuple(scalar(match[f"v{i}"]) for i in range(1, size + 1))
            if kind == "time":
                weights = tuple(
                    duration(match[f"t{i}"]).total for i in range(1, size + 1)
                )
            elif kind == "distance":
                weights = tuple(scalar(match[f"s{i}"]) for i in range(1, size + 1))
            else:
                weights = (sp.Integer(1),) * size
            if any(value <= 0 for value in speeds + weights):
                raise UnsupportedCondition(
                    "positive leg speeds and lengths or times are required"
                )
            return Question(kind, speeds, weights)
    raise UnsupportedCondition("the complete average-speed question must be recognized")


@dataclass(frozen=True)
class Analysis:
    question: Question
    distances: tuple
    times: tuple
    result: sp.Rational


def analyze(q):
    if q.by_time:
        distances = tuple(v * t for v, t in zip(q.speeds, q.weights, strict=True))
        times = q.weights
    else:
        distances = q.weights
        times = tuple(s / v for s, v in zip(q.weights, q.speeds, strict=True))
    return Analysis(q, distances, times, sum(distances) / sum(times))


def calculate(context):
    data = math_common.read(context)
    return data, analyze(parse(data[3]))


def equal_parts(a):
    q = a.question
    if q.by_time:
        html = "<p>Пусть автомобиль находился в пути 2t часов. На каждую половину времени приходится t часов. Найдём путь и среднюю скорость:</p>"
        html += line(r"S_{\mathrm{общ}}=" + "+".join(n(v) + "t" for v in q.speeds))
        html += line(r"t_{\mathrm{общ}}=2t")
        html += line(
            r"v_{\mathrm{ср}}=" + frac("+".join(n(v) + "t" for v in q.speeds), "2t")
        )
        return html + line(
            r"v_{\mathrm{ср}}="
            + frac("+".join(map(n, q.speeds)), "2")
            + "="
            + n(a.result)
        )
    html = "<p>Пусть 3S км — весь путь автомобиля. Каждая треть равна S км; время прохождения каждого участка найдём по формуле t=S/v:</p>"
    html += line(r"t_{\mathrm{общ}}=" + "+".join(frac("S", n(v)) for v in q.speeds))
    html += line(
        r"v_{\mathrm{ср}}=" + frac("3S", "+".join(frac("S", n(v)) for v in q.speeds))
    )
    html += line("+".join(frac("1", n(v)) for v in q.speeds) + "=" + n(sum(a.times)))
    return html + line(
        r"v_{\mathrm{ср}}=" + frac("3", n(sum(a.times))) + "=" + n(a.result)
    )


def specified_parts(a):
    q = a.question
    if q.by_time:
        html = "<p>Для каждого участка умножим скорость на время, затем сложим пути и времена движения:</p>"
        distances = "+".join(
            n(t) + r"\cdot" + n(v) for t, v in zip(q.weights, q.speeds, strict=True)
        )
        times = "+".join(map(n, q.weights))
    else:
        html = "<p>Сложим длины участков. Чтобы найти общее время, разделим длину каждого участка на его скорость:</p>"
        distances = "+".join(map(n, q.weights))
        times = "+".join(
            frac(n(s), n(v)) for s, v in zip(q.weights, q.speeds, strict=True)
        )
    html += line(r"S_{\mathrm{общ}}=" + distances + "=" + n(sum(a.distances)))
    html += line(r"t_{\mathrm{общ}}=" + times + "=" + n(sum(a.times)))
    return (
        html
        + "<p>Разделим весь путь на всё время движения:</p>"
        + line(
            r"v_{\mathrm{ср}}="
            + frac(n(sum(a.distances)), n(sum(a.times)))
            + "="
            + n(a.result)
        )
    )


def proof(a):
    html = "<p>Чтобы найти среднюю скорость на протяжении пути, нужно весь путь разделить на всё время движения:</p>"
    html += line(r"v_{\mathrm{ср}}=\frac{S_{\mathrm{общ}}}{t_{\mathrm{общ}}}")
    return html + (
        equal_parts(a) if a.question.kind.startswith("equal_") else specified_parts(a)
    )


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(a.result), proof(a))
