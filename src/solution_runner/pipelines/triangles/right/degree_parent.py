"""Preserve reviewed 30-degree proofs, including complementary 60-degree questions."""

import re
import unicodedata

import sympy as sp
from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ...probability.common import line
from ...word_problems.math_common import fraction as frac
from .altitude_input import _ALIASES, _text
from .altitude_methods import review_sections, solution_section
from .altitude_parent import _display, exact_answer
from .altitude_solver import (
    AltitudeSolveError,
    _parse_positive_value,
    solve_altitude_condition,
)
from .basic_parent import _figure, _targeted

_SOURCES = {
    "c4d631d2-f62e-4a29-8a3b-1f025265659e": "55a71ed80ac8b1a208293311b9a73785abf6a76c5dfc3c6170ccd88178516eda"
}
_REQUESTS = {
    "right-triangle-altitude-length": "CH",
    "right-triangle-hypotenuse-projection-ah": "AH",
    "right-triangle-hypotenuse-projection-bh": "BH",
}
_SECTIONS = {
    "CH": (
        ("Решение", (r"CH=AC\sinA=AB\cosA\sinA=",)),
        (
            "Приведем другое решение",
            (r"BC=\frac{AB}{2}=", r"HB=\frac{BC}{2}=", r"CH=\sqrt{BC^2-BH^2}="),
        ),
    ),
    "AH": (
        ("Решение", (r"AH=AC\cosA=AB\cos^2A=",)),
        (
            "Приведем другое решение",
            (r"CB=\frac{1}{2}AB=", r"HB=\frac{1}{2}CB=", "AH=AB-HB="),
        ),
    ),
}
_DEGREE = r"(?:°|\^\{?\\circ\}?)"
_QUESTION = (
    r"[ВB] треугольнике ABC угол C равен 90" + _DEGREE + r"\s*,\s*"
    r"(?P<height>CH\s*[—–−-]\s*высота,\s*)?угол A равен (?P<angle>\d+)"
    + _DEGREE
    + r"\s*,?\s*AB\s*=\s*(?P<length>.+?)\s*\.?\s*Найдите (?P<altitude>высоту )?(?P<request>CH|AH|BH)\s*\.?\s*"
)


def _parent(html, requested):
    soup = BeautifulSoup(html, "html.parser")
    if requested in _SECTIONS:
        review_sections(soup, _SECTIONS[requested])
        return
    if soup.find(["section", "img", "script", "style"]) or soup.select(
        "[data-inline-latex]"
    ):
        raise AltitudeSolveError("the complete half-hypotenuse parent must be reviewed")
    text = " ".join(
        unicodedata.normalize("NFKC", soup.get_text(" ", strip=True))
        .replace("\xad", "")
        .split()
    )
    number = r"\d+(?:[,.]\d+)?"
    expected = (
        r"В треугольнике ABC катет BC лежит напротив угла в 30°, поэтому он вдвое меньше "
        r"гипотенузы AB , то есть его длина равна "
        + number
        + r"\. В треугольнике BHC катет BH "
        r"лежит напротив угла в 30°, поэтому он вдвое меньше гипотенузы BC , то есть его длина равна "
        + number
        + r"\."
    )
    if re.fullmatch(expected, text) is None:
        raise AltitudeSolveError(
            "the complete half-hypotenuse argument must be reviewed"
        )


def read_question(html, source, expected):
    text = _text(html, source)
    text = text.replace(r"\mathrm{AB}", " AB ")
    text = re.sub(r"\\text\{\s*,\s*\}", ", ", text)
    text = text.replace(r"\ ", " ")
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = " ".join(text.split())
    match = re.fullmatch(_QUESTION, text)
    if match is None or match["request"] != expected:
        raise AltitudeSolveError(
            "every degree, length and request must be read explicitly"
        )
    angle = int(match["angle"])
    if angle not in {30, 60}:
        raise AltitudeSolveError(
            "the preserved half-hypotenuse method requires an angle of 30 or 60 degrees"
        )
    if not match["height"] and not (expected == "CH" and match["altitude"]):
        raise AltitudeSolveError("CH must be explicitly defined as an altitude")
    return angle, _parse_positive_value(match["length"])


def _solve(angle, length, requested):
    sine = sp.sin(sp.pi * angle / 180)
    html = (
        "<p>В треугольнике ABC угол C равен 90°, CH — высота, "
        '<span data-inline-latex="AB=' + sp.latex(length) + '"></span>, '
        '<span data-inline-latex="\\sin A=' + sp.latex(sine) + '"></span>. Найдите '
        '<span data-inline-latex="' + requested + '"></span>.</p>'
    )
    return solve_altitude_condition(html)


def _primary(requested, values, answer):
    if requested == "CH":
        formula = (
            r"CH=AC\sin A=AB\cos A\sin A=("
            + values["AB"]
            + r")\cdot("
            + values["cosA"]
            + r")\cdot("
            + values["sinA"]
            + ")="
            + answer
        )
    else:
        formula = (
            r"AH=AC\cos A=AB\cos^2 A=("
            + values["AB"]
            + r")\cdot("
            + values["cosA"]
            + ")^2="
            + answer
        )
    return (
        "<p>Последовательно выразим длины через гипотенузу и тригонометрические функции угла A:</p>"
        + line(formula)
    )


def _half_length(segment, hypotenuse, values, answer=None):
    parts = [
        segment,
        frac(hypotenuse, "2"),
        frac(values[_ALIASES.get(hypotenuse, hypotenuse)], "2"),
        values[_ALIASES.get(segment, segment)],
    ]
    if answer is not None:
        parts.append(answer)
    return line(
        "=".join(
            part
            for index, part in enumerate(parts)
            if index == 0 or part != parts[index - 1]
        )
    )


def _halves(angle, requested, values, answer):
    leg, projection = ("BC", "BH") if angle == 30 else ("AC", "AH")
    leg_label = "CB" if requested == "AH" and angle == 30 else leg
    projection_label = "HB" if requested != "BH" and angle == 30 else projection
    explanation = (
        "<p>Угол A равен 30°. Катет BC, лежащий напротив него, равен половине гипотенузы AB:</p>"
        if angle == 30
        else "<p>Угол A равен 60°, поэтому угол B равен 30°. Катет AC, лежащий напротив угла B, равен половине гипотенузы AB:</p>"
    )
    body = explanation + _half_length(leg_label, "AB", values)
    body += (
        "<p>Углы HCB и A равны по свойству высоты прямоугольного треугольника. В треугольнике HCB катет HB лежит напротив угла 30°:</p>"
        if angle == 30
        else "<p>Углы ACH и B равны по свойству высоты прямоугольного треугольника. В треугольнике ACH катет AH лежит напротив угла 30°:</p>"
    )
    body += _half_length(
        projection_label, leg_label, values, answer if requested == projection else None
    )
    if requested == "CH":
        body += "<p>По теореме Пифагора:</p>" + line(
            r"CH=\sqrt{"
            + leg_label
            + "^2-"
            + projection_label
            + r"^2}=\sqrt{("
            + values[leg]
            + ")^2-("
            + values[projection]
            + ")^2}="
            + answer
        )
    elif requested != projection:
        body += line(
            requested
            + "=AB-"
            + projection_label
            + "=("
            + values["AB"]
            + ")-("
            + values[projection]
            + ")="
            + answer
        )
    return body


def _prepare(context, *, parent_asset_id, parent_solution_html, content_rule_key):
    from .planner import RepairPlan, _section

    if content_rule_key not in _REQUESTS:
        raise AltitudeSolveError("the degree-based rule has not been reviewed")
    requested = _REQUESTS[content_rule_key]
    _parent(parent_solution_html, requested)
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise AltitudeSolveError("schema-v3 normalized content is required")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise AltitudeSolveError("a complete degree-based condition is required")
    angle, length = read_question(condition["html"], parent_asset_id, requested)
    solved = _solve(angle, length, requested)
    changes = _figure(content, condition, parent_asset_id, sources=_SOURCES)
    answer = exact_answer(solved.exact_value)
    values = _display(solved)
    alternative = _halves(angle, requested, values, answer.replace(",", "{,}"))
    if requested == "BH":
        html = solution_section("Решение", alternative)
    else:
        html = solution_section(
            "Решение", _primary(requested, values, answer.replace(",", "{,}"))
        ) + solution_section("Приведем другое решение", alternative)
    plan = diagrams.repair(
        condition,
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        answer,
        html,
        asset_changes=changes,
    )
    return RepairPlan(plan.answer, plan.transformations)


def prepare(context, *, parent_asset_id, parent_solution_html, content_rule_key):
    try:
        return _prepare(
            context,
            parent_asset_id=parent_asset_id,
            parent_solution_html=parent_solution_html,
            content_rule_key=content_rule_key,
        )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
