"""Reviewed area and acute-angle parent methods with exact, complete conditions."""

import re
import unicodedata

import sympy as sp
from bs4 import BeautifulSoup

from ...probability import solution_diagrams as diagrams
from ...probability.common import line
from ...word_problems.math_common import fraction as frac
from .altitude_input import _text
from .altitude_methods import solution_section
from .altitude_parent import exact_answer
from .altitude_solver import AltitudeSolveError, _parse_positive_value
from .basic_parent import _figure, _targeted

_SOURCES = {
    "a6653ffc-0e3b-4423-98e0-e2777653995f": "8e9ebfa607ff7ba205d8075628191dc2775e121461e613dafc47e961645e887e"
}
_KINDS = {
    "right-triangle-leg-hypotenuse-area": "leg_hypotenuse",
    "right-triangle-area-leg-difference": "leg_difference",
    "right-triangle-acute-angle-difference": "angle_difference",
    "right-triangle-acute-angle-ratio": "angle_ratio",
}
_PATTERNS = {
    "leg_hypotenuse": r"Найдите площадь прямоугольного треугольника, если его катет и гипотенуза равны соответственно (?P<a>.+?) и (?P<h>.+?)\.?",
    "leg_difference": r"Площадь прямоугольного треугольника равна (?P<S>.+?)\. Один из его катетов на (?P<d>.+?) больше другого\. Найдите меньший катет\.?",
    "angle_difference": r"Один острый угол прямоугольного треугольника на (?P<d>.+?)(?:°|\^\{?\\circ\}?) больше другого\. Найдите больший острый угол\. Ответ дайте в градусах\.?",
    "angle_ratio": r"Один острый угол прямоугольного треугольника в (?P<r>.+?) раза? больше другого\. Найдите больший острый угол\. Ответ дайте в градусах\.?",
}


_PARENT_CHECKS = {
    "leg_hypotenuse": lambda forms, text: (
        len(forms) == 1
        and forms[0].startswith("S=\\frac{1}{2}\\cdot")
        and ("теореме Пифагора" in text)
        and ("половине произведения" in text)
    ),
    "leg_difference": lambda forms, text: (
        len(forms) == 1
        and forms[0].startswith("\\frac{1}{2}x(x+")
        and all(s in forms[0] for s in ("\\iffx(x+", "\\begin{cases}", "x=-", "x\\gt0"))
    ),
    "angle_difference": lambda forms, text: (
        len(forms) == 1
        and forms[0].startswith("\\begin{cases}\\angleA-\\angleB=")
        and ("\\angleA+\\angleB=90^\\circ" in forms[0])
        and (forms[0].count("\\begin{cases}") == 2)
    ),
    "angle_ratio": lambda forms, text: (
        len(forms) == 3
        and re.fullmatch("[1-9]\\d*x", forms[0]) is not None
        and (forms[1] == "x+" + forms[0] + "=90^\\circ")
        and forms[2].startswith(forms[0] + "=")
    ),
}


def _parent(html, kind):
    soup = BeautifulSoup(html, "html.parser")
    if soup.find(["section", "img", "script", "style"]):
        raise AltitudeSolveError("the complete elementary parent must be reviewed")
    forms = [
        "".join(f["data-inline-latex"].split())
        .replace("^{2}", "^2")
        .replace(r"^{\circ}", r"^\circ")
        for f in soup.select("[data-inline-latex]")
    ]
    text = " ".join(
        unicodedata.normalize("NFKC", soup.get_text(" ", strip=True))
        .replace("\xad", "")
        .split()
    )
    check = _PARENT_CHECKS.get(kind)
    if check is None or not check(forms, text):
        raise AltitudeSolveError(
            "the complete elementary parent method has not been reviewed"
        )


def _read(html, kind, source):
    text = _text(html, source)
    match = re.fullmatch(_PATTERNS[kind], text)
    if match is None:
        raise AltitudeSolveError("an unknown elementary condition statement remains")
    return {k: _parse_positive_value(v) for k, v in match.groupdict().items()}


def _leg_hypotenuse(v):
    a, h = v["a"], v["h"]
    square = sp.simplify(h * h - a * a)
    if square.is_positive is not True:
        raise AltitudeSolveError("the hypotenuse must be longer than the given leg")
    other = sp.sqrt(square)
    answer = exact_answer(a * other / 2)
    body = (
        "<p>Площадь прямоугольного треугольника равна половине произведения катетов. "
        "По теореме Пифагора найдём второй катет a:</p>"
        + line(
            r"a^2=(" + sp.latex(h) + ")^2-(" + sp.latex(a) + ")^2=" + sp.latex(square)
        )
        + line(r"a=\sqrt{" + sp.latex(square) + "}=" + sp.latex(other))
        + line(
            r"S=\frac{1}{2}\cdot("
            + sp.latex(a)
            + r")\cdot("
            + sp.latex(other)
            + ")="
            + answer.replace(",", "{,}")
        )
    )
    return answer, body


def _leg_difference(v):
    area, d = v["S"], v["d"]
    discriminant = sp.simplify(d * d + 8 * area)
    root = sp.sqrt(discriminant)
    positive, negative = sp.simplify((root - d) / 2), sp.simplify((-root - d) / 2)
    answer = exact_answer(positive)
    dt, st, dd = sp.latex(d), sp.latex(area), sp.latex(discriminant)
    body = (
        "<p>Пусть x — меньший катет. Больший катет отличается от него на заданную разность. "
        "Площадь равна половине произведения катетов:</p>"
        + line(r"\frac{1}{2}x(x+" + dt + ")=" + st)
        + line("x(x+" + dt + ")=" + sp.latex(2 * area))
        + line("x^2+(" + dt + ")x-(" + sp.latex(2 * area) + ")=0")
        + line("D=(" + dt + ")^2+8(" + st + ")=" + dd)
        + line(
            "x_1="
            + frac("-(" + dt + r")+\sqrt{" + dd + "}", "2")
            + "="
            + sp.latex(positive)
        )
        + line(
            "x_2="
            + frac("-(" + dt + r")-\sqrt{" + dd + "}", "2")
            + "="
            + sp.latex(negative)
        )
        + "<p>Отрицательный корень не подходит: длина катета положительна. Поэтому:</p>"
        + line("x=x_1=" + answer.replace(",", "{,}"))
    )
    return answer, body


def _angle_difference(v):
    d = v["d"]
    if (90 - d).is_positive is not True:
        raise AltitudeSolveError(
            "the acute-angle difference must be less than 90 degrees"
        )
    larger, smaller = (90 + d) / 2, (90 - d) / 2
    answer = exact_answer(larger)
    body = (
        "<p>Обозначим больший острый угол A, меньший — B. Сумма острых углов равна 90°, "
        "а разность дана в условии. Получаем систему:</p>"
        + line(
            r"\begin{cases}\angle A-\angle B="
            + sp.latex(d)
            + r"^{\circ}\\\angle A+\angle B=90^{\circ}\end{cases}"
        )
        + line(
            r"\begin{cases}\angle A="
            + sp.latex(larger)
            + r"^{\circ}\\\angle B="
            + sp.latex(smaller)
            + r"^{\circ}\end{cases}"
        )
    )
    return answer, body


def _angle_ratio(v):
    r = v["r"]
    if (r - 1).is_positive is not True:
        raise AltitudeSolveError(
            "the ratio of the larger angle to the smaller must exceed one"
        )
    small = sp.simplify(90 / (1 + r))
    answer = exact_answer(r * small)
    rt = sp.latex(r)
    body = (
        "<p>Пусть x — меньший острый угол. Больший угол равен произведению x "
        "и данного отношения. Сумма острых углов равна 90°:</p>"
        + line("x+(" + rt + r")x=90^{\circ}")
        + line(
            "x="
            + frac("90", "1+(" + rt + ")")
            + r"^{\circ}="
            + sp.latex(small)
            + r"^{\circ}"
        )
        + line(
            "("
            + rt
            + ")x=("
            + rt
            + r")\cdot("
            + sp.latex(small)
            + r")^{\circ}="
            + answer.replace(",", "{,}")
            + r"^{\circ}"
        )
    )
    return answer, body


_SOLVERS = {
    "leg_hypotenuse": _leg_hypotenuse,
    "leg_difference": _leg_difference,
    "angle_difference": _angle_difference,
    "angle_ratio": _angle_ratio,
}


def prepare(context, *, parent_asset_id, parent_solution_html, content_rule_key):
    from .planner import RepairPlan, _section

    if content_rule_key not in _KINDS:
        raise AltitudeSolveError("the elementary rule has not been reviewed")
    kind = _KINDS[content_rule_key]
    _parent(parent_solution_html, kind)
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise AltitudeSolveError("schema-v3 normalized content is required")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise AltitudeSolveError("a complete elementary condition is required")
    values = _read(condition["html"], kind, parent_asset_id)
    changes = _figure(content, condition, parent_asset_id, sources=_SOURCES)
    answer, body = _SOLVERS[kind](values)
    plan = diagrams.repair(
        condition,
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        answer,
        solution_section("Решение", body),
        asset_changes=changes,
    )
    return RepairPlan(plan.answer, plan.transformations)
