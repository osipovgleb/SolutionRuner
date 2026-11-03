"""Prepare reviewed angle constructions while retaining the parent's argument."""

import re
import unicodedata

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...core.numbers import format_answer, parse_rational
from ...probability import solution_diagrams as diagrams
from ...probability.common import line
from .altitude_input import _text
from .altitude_methods import solution_section
from .altitude_solver import AltitudeSolveError
from .basic_parent import _figure, _targeted

MEDIAN = "right-triangle-median-angle"
BISECTORS = "right-triangle-bisector-intersection-angle"
_SOURCES = {
    "6373d59e-25da-49c7-b889-fb12dc36acd7": "71dc69ccaeb25a3a7eb43b8d0e8cacc4bc9ea4cea60254142ff898e486e0f320",
    "9644f129-5e06-489f-91ff-a15865eab80e": "3f0949d5a5dc3745b541b4ca59ea971e0d9b07e32ae561362c3284db9a7d4caf",
}
_RULE_SOURCES = dict(zip((MEDIAN, BISECTORS), _SOURCES))
_DEGREE = r"(?:°|\^\{?\\circ\}?)"
_NUMBER = r"\d+(?:(?:[,.]|\{,\})\d+)?"
_QUESTIONS = {
    MEDIAN: (
        r"[ВB] треугольнике ABC угол ACB равен 90\s*"
        + _DEGREE
        + r"\s*, угол B равен (?P<angle>"
        + _NUMBER
        + r")\s*"
        + _DEGREE
        + r"\s*, CD\s*[—–−-]\s*медиана\. Найдите угол ACD\s*\."
    ),
    BISECTORS: (
        r"Острый угол прямоугольного треугольника равен (?P<angle>"
        + _NUMBER
        + r")\s*"
        + _DEGREE
        + r"\s*\. Найдите острый угол, образованный "
        r"биссектрисами этого и прямого углов треугольника\."
    ),
}
_PARENT_PROSE = {
    MEDIAN: (
        "CD — медиана в прямоугольном треугольнике, значит, CD = AD = BD . "
        "Тогда треугольник ACD — равнобедренный, углы при его основании равны. ."
    ),
    BISECTORS: (
        "Под углом пересечения прямых понимается меньший угол, который они образуют. "
        "Найдем угол АОЕ — внешний угол треугольника АОС . Получаем: ."
    ),
}
_PARENT_FORMULAS = {
    MEDIAN: re.compile(
        r"\\angle ACD=\\angle A=90\^\{\\circ\}-"
        + _NUMBER
        + r"\^\{\\circ\}="
        + _NUMBER
        + r"\^\{\\circ\}"
    ),
    BISECTORS: re.compile(
        r"\\angle AOE=\\frac\{1\}\{2\}\(\\angle C\+\\angle A\)="
        r"\\frac\{90\^\{\\circ\}\}\{2\}\+\\frac\{"
        + _NUMBER
        + r"\^\{\\circ\}\}\{2\}="
        + _NUMBER
        + r"\^\{\\circ\}"
    ),
}


def _parent(html, rule):
    soup = BeautifulSoup(html, "html.parser")
    formulas = soup.select("[data-inline-latex]")
    prose = " ".join(
        unicodedata.normalize("NFKC", soup.get_text(" ", strip=True))
        .replace("\xad", "")
        .split()
    )
    if (
        soup.find(["section", "img", "script", "style"])
        or prose != _PARENT_PROSE[rule]
        or len(formulas) != 1
        or formulas[0].get_text().strip()
        or _PARENT_FORMULAS[rule].fullmatch(formulas[0]["data-inline-latex"]) is None
    ):
        raise AltitudeSolveError("the complete construction parent must be reviewed")


def read_question(html, source, rule):
    if rule not in _QUESTIONS or source != _RULE_SOURCES[rule]:
        raise AltitudeSolveError("the construction and its figure must be reviewed")
    text = _text(html, source, labels="ABCD")
    match = re.fullmatch(_QUESTIONS[rule] + r" Ответ дайте в градусах\.", text)
    if match is None:
        raise AltitudeSolveError("every construction statement and request is required")
    angle = parse_rational(match["angle"])
    if not 0 < angle < 90:
        raise AltitudeSolveError("the given triangle angle must be acute")
    return angle


def _proof(angle, rule):
    value = format_answer(angle).replace(",", "{,}")
    if rule == MEDIAN:
        answer = format_answer(90 - angle)
        body = (
            "<p>CD — медиана в прямоугольном треугольнике, значит, она равна половине гипотенузы AB:</p>"
            + line("CD=AD=BD")
            + "<p>Тогда треугольник ACD — равнобедренный, углы при его основании равны. Острые углы прямоугольного треугольника в сумме дают 90°:</p>"
            + line(r"\angle ACD=\angle A=90^{\circ}-\angle B")
            + line(
                r"\angle ACD=90^{\circ}-"
                + value
                + r"^{\circ}="
                + answer.replace(",", "{,}")
                + r"^{\circ}"
            )
        )
    else:
        answer = format_answer(45 + angle / 2)
        body = (
            "<p>Обозначим данный острый угол через A, прямой угол — через C, а точку пересечения их биссектрис — через O. Точка E — пересечение биссектрисы угла C со стороной AB.</p>"
            "<p>Под углом пересечения прямых понимается меньший угол, который они образуют. Найдем угол AOE — внешний угол треугольника AOC. Биссектрисы делят соответствующие углы пополам, поэтому:</p>"
            + line(r"\angle CAO=\frac{\angle A}{2}")
            + line(r"\angle ACO=\frac{\angle C}{2}=\frac{90^{\circ}}{2}=45^{\circ}")
            + "<p>Внешний угол равен сумме двух внутренних углов, не смежных с ним. Получаем:</p>"
            + line(r"\angle AOE=\frac{1}{2}(\angle C+\angle A)")
            + line(r"\angle AOE=\frac{90^{\circ}}{2}+\frac{" + value + r"^{\circ}}{2}")
            + line(
                r"\angle AOE=45^{\circ}+\frac{"
                + value
                + r"^{\circ}}{2}="
                + answer.replace(",", "{,}")
                + r"^{\circ}"
            )
            + "<p>Так как угол A острый, полученный угол меньше 90° и является искомым.</p>"
        )
    return answer, solution_section("Решение", body)


def prepare(context, *, parent_asset_id, parent_solution_html, content_rule_key):
    from .planner import RepairPlan, _section

    try:
        if content_rule_key not in _QUESTIONS:
            raise AltitudeSolveError("the construction rule must be reviewed")
        _parent(parent_solution_html, content_rule_key)
        content = context.get("normalized_content")
        if (
            not isinstance(content, dict)
            or content.get("format") != "teacherhelper-normalized"
            or content.get("schema_version") != 3
        ):
            raise AltitudeSolveError("schema-v3 normalized content is required")
        condition = _section(content, "condition")
        if condition is None or not isinstance(condition.get("html"), str):
            raise AltitudeSolveError("a complete construction condition is required")
        angle = read_question(condition["html"], parent_asset_id, content_rule_key)
        changes = _figure(content, condition, parent_asset_id, sources=_SOURCES)
        answer, html = _proof(angle, content_rule_key)
        plan = diagrams.repair(
            condition,
            _targeted(_section(content, "answer")),
            _targeted(_section(content, "solution")),
            answer,
            html,
            asset_changes=changes,
        )
        return RepairPlan(plan.answer, plan.transformations)
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
