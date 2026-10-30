"""Audited arrow endpoints feed the shared exact coordinate operations."""

import json
import re
from fractions import Fraction
from pathlib import Path

from solution_runner.pipelines.core.numbers import format_answer
from solution_runner.pipelines.probability import condition_diagram
from solution_runner.pipelines.probability.common import (
    UnsupportedCondition,
    finish,
    line,
)

from .coordinates import _ask, _fmt, evaluate, solve

_ASSETS = Path(__file__).with_name("assets")
_EVIDENCE = json.loads((_ASSETS / "coordinate_diagrams.json").read_text())
_VECTOR = r"\\vec\{(?:[a-z]|[A-Z]{2})\}"
_PREFIX = re.compile(
    r"(?:(?:На координатной плоскости|На рисунке) изображены|Даны) векторы (?P<names>.+?)(?:, координатами которых являются целые числа)?\. (?P<question>.+)"
)
_DECOMPOSITION = re.compile(
    r"Вектор \\vec\{c\} разложен по двум неколлинеарным векторам \\vec\{a\} и \\vec\{b\}: \\vec\{c\}=k\\vec\{a\}\+l\\vec\{b\}, где k и l — коэффициенты разложения\. Найдите (?P<target>[kl])\."
)


def _question(text, vectors):
    text = re.sub(r"\\overrightarrow\{([a-z])\}", r"\\vec{\1}", text)
    prefix = _PREFIX.fullmatch(text)
    if prefix:
        names = prefix["names"]
        declared = re.findall(_VECTOR, names)
        gap = re.sub(_VECTOR, "", names).replace(", ", "").replace(" и ", "")
        if gap or declared != [rf"\vec{{{name}}}" for name in vectors]:
            raise UnsupportedCondition(
                "the named vectors do not match the audited diagram"
            )
        text = prefix["question"]
    decomposition = _DECOMPOSITION.fullmatch(text)
    if decomposition:
        if list(vectors) != ["a", "b", "c"]:
            raise UnsupportedCondition(
                "the decomposition requires the three named arrows"
            )
        return "decomposition", decomposition["target"]
    angle = re.fullmatch(
        rf"Найдите угол между векторами (?P<a>{_VECTOR}) и (?P<b>{_VECTOR})\. Ответ дайте в градусах\.",
        text,
    )
    if angle:
        names = [angle[k][5:-1] for k in ("a", "b")]
        if len(set(names)) != 2 or set(names) != set(vectors):
            raise UnsupportedCondition(
                "the angle requires exactly the two named arrows"
            )
        return "angle", None
    match = re.fullmatch(r"Найдите (.+?)\.?", text)
    if match is None:
        raise UnsupportedCondition("unsupported complete diagram-vector question")
    mode, expression = _ask(match[1])
    if expression is not None:
        evaluate(expression, vectors)
    return mode, expression


def decompose(a, b, c):
    determinant = a[0] * b[1] - a[1] * b[0]
    if not determinant:
        raise UnsupportedCondition("the two basis vectors must be noncollinear")
    return (
        (c[0] * b[1] - c[1] * b[0]) / determinant,
        (a[0] * c[1] - a[1] * c[0]) / determinant,
    )


def _decomposition(vectors, target):
    a, b, c = (vectors[name] for name in ("a", "b", "c"))
    k, l = decompose(a, b, c)
    axis = 0 if b[0] else 1
    other = 1 - axis
    f = _fmt
    html = "<p>Подставим координаты векторов в разложение и приравняем соответствующие координаты:</p>"
    html += line(r"\vec c=k\vec a+l\vec b")
    html += line(
        r"\begin{cases}"
        + rf"({f(a[0])})k+({f(b[0])})l={f(c[0])}\\({f(a[1])})k+({f(b[1])})l={f(c[1])}"
        + r"\end{cases}"
    )
    html += "<p>Выразим l из одного уравнения и подставим в другое:</p>"
    html += line(rf"l=\frac{{{f(c[axis])}-({f(a[axis])})k}}{{{f(b[axis])}}}")
    html += line(
        rf"({f(a[other])})k+({f(b[other])})\cdot\frac{{{f(c[axis])}-({f(a[axis])})k}}{{{f(b[axis])}}}={f(c[other])}"
    )
    coefficient = a[other] * b[axis] - b[other] * a[axis]
    right = c[other] * b[axis] - b[other] * c[axis]
    html += line(rf"({f(coefficient)})k={f(right)}\quad\Rightarrow\quad k={f(k)}")
    html += line(
        rf"l=\frac{{{f(c[axis])}-({f(a[axis])})\cdot({f(k)})}}{{{f(b[axis])}}}={f(l)}"
    )

    return format_answer(k if target == "k" else l), html


def build_context_repair_plan(context, *, condition_asset_bytes=None):
    content, condition, answer, solution, text, entry, source = condition_diagram.read(
        context, _EVIDENCE, _ASSETS
    )
    condition_diagram.verify_download(source, condition_asset_bytes)
    if len(content.get("assets", [])) != 1:
        raise UnsupportedCondition("one audited coordinate diagram is required")
    vectors = {}
    html = "<p>Координаты вектора равны разности соответствующих координат его конца и начала. По рисунку получаем:</p>"
    for name, (start, end) in entry["vectors"].items():
        vectors[name] = tuple(
            Fraction(y) - Fraction(x) for x, y in zip(start, end, strict=True)
        )
        symbol = rf"\overrightarrow{{{name}}}" if len(name) == 2 else rf"\vec{{{name}}}"
        html += line(
            rf"{symbol}=({end[0]}-({start[0]});{end[1]}-({start[1]}))={_fmt(vectors[name])}"
        )
    mode, expression = _question(text, vectors)
    result, steps = (
        _decomposition(vectors, expression)
        if mode == "decomposition"
        else solve(vectors, mode, expression)
    )
    return finish(condition, answer, solution, result, html + steps)
