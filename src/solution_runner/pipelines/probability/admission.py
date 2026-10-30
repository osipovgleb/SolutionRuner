"""Overlapping admission requirements, retaining all five parent methods."""

import re
from fractions import Fraction
from html import escape

from solution_runner.pipelines.core.numbers import format_answer, parse_rational

from . import solution_diagrams as diagrams
from .bernoulli import checked, fmt, result
from .common import NUMBER, UnsupportedCondition, line, normalize

_PATTERN = re.compile(
    rf"Чтобы поступить в институт на специальность «[^«»]+»а?, абитуриент должен набрать на ЕГЭ не менее (?P<t1>\d+) баллов по каждому из трех предметов — математика, русский язык и иностранный язык\. Чтобы поступить на (?:на )?специальность «[^«»]+», нужно набрать не менее (?P<t2>\d+) баллов по каждому из трех предметов — математика, русский язык и обществознание\. Вероятность того, что абитуриент (?P<person>[А-Я])\. получит не менее (?P<t3>\d+) баллов по математике, равна (?P<m>{NUMBER}), по русскому языку — (?P<r>{NUMBER}), по иностранному языку — (?P<f>{NUMBER}) и по обществознанию — (?P<s>{NUMBER})\. Найдите вероятность того, что (?P=person)\. сможет поступить хотя бы на одну из двух упомянутых специальностей\."
)
_REUSE = {
    (
        Fraction(6, 10),
        Fraction(8, 10),
        Fraction(7, 10),
        Fraction(5, 10),
    ): "8cfc1399-c6ea-46b4-a430-2d45c80181f5",
    (
        Fraction(6, 10),
        Fraction(6, 10),
        Fraction(6, 10),
        Fraction(9, 10),
    ): "e626b7fc-8fe2-4331-9284-31fa28348680",
}
_KEY = "generated_admission_tree"
_ALT = "Двоичное дерево результатов четырёх экзаменов"


def _input(context):
    content, condition, answer, solution, text = diagrams.read(context)
    match = _PATTERN.fullmatch(normalize(text))
    if match is None:
        raise UnsupportedCondition("unsupported complete admission condition")
    if len({int(match[k]) for k in ("t1", "t2", "t3")}) != 1:
        raise UnsupportedCondition(
            "the two specialties and given probabilities must use the same score threshold"
        )
    probabilities = tuple(
        checked(parse_rational(match[k])) for k in ("m", "r", "f", "s")
    )
    return content, condition, answer, solution, probabilities


def admission_probability(m, r, f, s):
    for p in (m, r, f, s):
        checked(p)
    return m * r * (f + s - f * s)


def render_svg(probabilities):
    m, r, f, s = probabilities
    yes = admission_probability(m, r, f, s)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="660" height="670" viewBox="0 0 660 670"><g font-family="Arial,sans-serif" font-size="15" fill="#222">'
    ]

    def text(x, y, value, color="#222", size=15):
        parts.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" fill="{color}" font-size="{size}">{escape(value)}</text>'
        )

    def edge(a, b, label, color):
        x1, y1 = a
        x2, y2 = b
        parts.append(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="#333" fill="none"/>')
        text((x1 + x2) / 2, (y1 + y2) / 2, label, color)

    text(95, 86, "Русский язык", "#1654ef")
    text(95, 226, "Математика", "#1654ef")
    text(95, 366, "Иностранный язык", "#1654ef")
    text(95, 506, "Обществознание", "#1654ef")
    root = (350, 20)
    r_yes = (265, 125)
    r_no = (495, 125)
    m_yes = (230, 265)
    m_no = (395, 265)
    f_yes = (155, 405)
    f_no = (330, 405)
    s_yes = (265, 545)
    s_no = (465, 545)
    for a, b, p in [
        (root, r_yes, r),
        (r_yes, m_yes, m),
        (m_yes, f_yes, f),
        (f_no, s_yes, s),
    ]:
        edge(a, b, format_answer(p), "#43bd29")
    for a, b, p in [
        (root, r_no, 1 - r),
        (r_yes, m_no, 1 - m),
        (m_yes, f_no, 1 - f),
        (f_no, s_no, 1 - s),
    ]:
        edge(a, b, format_answer(p), "#ff2525")
    for x, y, p in [
        (r_no[0], r_no[1], 1 - r),
        (m_no[0], m_no[1], r * (1 - m)),
        (s_no[0], s_no[1], r * m * (1 - f) * (1 - s)),
    ]:
        text(x, y + 18, "не сдал")
        text(x, y + 38, "НЕ ПОСТУПИЛ", "#ff2525")
        text(x, y + 58, format_answer(p), "#ff2525", 14)
    for x, y, p in [
        (f_yes[0], f_yes[1], r * m * f),
        (s_yes[0], s_yes[1], r * m * (1 - f) * s),
    ]:
        text(x, y + 18, "сдал")
        text(x, y + 38, "ПОСТУПИЛ", "#43bd29")
        text(x, y + 58, format_answer(p), "#43bd29", 14)
    text(r_yes[0], r_yes[1] + 18, "сдал")
    text(m_yes[0], m_yes[1] + 18, "сдал")
    text(f_no[0], f_no[1] + 18, "не сдал")
    text(
        330,
        636,
        "Вероятность поступить: "
        + format_answer(r * m * f)
        + " + "
        + format_answer(r * m * (1 - f) * s)
        + " = "
        + format_answer(yes),
        "#43bd29",
    )
    text(330, 659, "Вероятность не поступить: " + format_answer(1 - yes), "#ff2525")
    parts.append("</g></svg>")
    return "".join(parts)


def required_assets(context):
    *_, probabilities = _input(context)
    source = _REUSE.get(probabilities)
    return (
        ({"source_asset_id": source, "section_id": "solution:1", "alt_text": _ALT},)
        if source
        else ()
    )


def diagram_specs(context):
    *_, probabilities = _input(context)
    return (
        ()
        if probabilities in _REUSE
        else (diagrams.spec(_KEY, render_svg(probabilities)),)
    )


def build_context_repair_plan(context, *, generated_solution_assets=()):
    content, condition, answer_section, solution, probabilities = _input(context)
    m, r, f, s = probabilities
    common = m * r
    value = admission_probability(m, r, f, s)
    html = (
        "<p>Способ 1. Для обеих специальностей нужны математика и русский язык. Кроме них, нужен хотя бы один из двух оставшихся предметов. В модели задачи результаты экзаменов независимы:</p>"
        + line(r"P=mr(f+s-fs)")
        + line(
            rf"P={fmt(m)}\cdot {fmt(r)}\cdot({fmt(f)}+{fmt(s)}-{fmt(f)}\cdot {fmt(s)})"
        )
    )
    html += (
        "<p>Способ 2. Пусть A и B означают выполнение требований первой и второй специальностей. Их пересечение требует все четыре экзамена:</p>"
        + line(
            rf"P(A)={fmt(common * f)},\quad P(B)={fmt(common * s)},\quad P(A\cap B)={fmt(common * f * s)}"
        )
        + line(
            rf"P(A\cup B)={fmt(common * f)}+{fmt(common * s)}-{fmt(common * f * s)}={fmt(value)}"
        )
    )
    html += (
        "<p>Способ 3. Разобьём успех на три несовместных случая: подходит только первая специальность, подходят обе, подходит только вторая:</p>"
        + line(r"P=mr[f(1-s)+fs+(1-f)s]")
        + line(
            rf"P={fmt(common)}\cdot[{fmt(f * (1 - s))}+{fmt(f * s)}+{fmt((1 - f) * s)}]={fmt(value)}"
        )
    )
    html += (
        "<p>Способ 4. При сданных общих предметах достаточно, чтобы не провалить оба дополнительных экзамена:</p>"
        + line(r"P=mr[1-(1-f)(1-s)]")
        + line(rf"P={fmt(common)}[1-{fmt(1 - f)}\cdot {fmt(1 - s)}]={fmt(value)}")
    )
    html += "<p>Способ 5. Построим двоичное дерево. Поступление соответствует двум зелёным конечным ветвям, их вероятности складываются:</p>"
    figure, key, changes = diagrams.image(
        content,
        _KEY,
        _ALT,
        source_id=_REUSE.get(probabilities),
        svg=render_svg(probabilities),
        generated=generated_solution_assets,
    )
    html += figure + line(rf"P={fmt(r * m * f)}+{fmt(r * m * (1 - f) * s)}")
    answer, html = result(value, html)
    return diagrams.repair(
        condition, answer_section, solution, answer, html, (key,), changes
    )
