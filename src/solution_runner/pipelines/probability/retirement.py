"""An unknown subgroup rate from a two-branch population tree."""

import re
from fractions import Fraction
from html import escape

from solution_runner.pipelines.core.numbers import format_answer

from . import solution_diagrams as diagrams
from .bernoulli import checked, fmt, result
from .common import NUMBER, UnsupportedCondition, line, normalize
from .mixtures import percent

_PATTERN = re.compile(
    rf"В городе (?P<w>{NUMBER})% взрослого населения — мужчины\. Пенсионеры составляют (?P<t>{NUMBER})% взрослого населения, причем доля пенсионеров среди женщин равна (?P<b>{NUMBER})%\. Для социологического опроса выбран случайным образом мужчина, проживающий в этом городе\. Найдите вероятность события «выбранный мужчина является пенсионером»\."
)
_REUSE = {
    (Fraction(48, 100), Fraction(15, 100)): "cce8ccf3-d659-4202-81f7-6b56905d905d",
    (Fraction(46, 100), Fraction(10, 100)): "3372fb38-5864-415b-9012-5ff1775c5da8",
    (Fraction(44, 100), Fraction(10, 100)): "b910d995-d006-4077-805c-f8506209a0a2",
    (Fraction(42, 100), Fraction(5, 100)): "254bb528-8c39-4a92-b114-d17b82d0c8aa",
}
_KEY = "generated_population_tree"
_ALT = "Дерево вероятностей: пол и пенсионный статус"


def _input(context):
    content, condition, answer, solution, text = diagrams.read(context)
    text = re.sub(r"\s*%", "%", normalize(text).replace(r"\%", "%"))
    match = _PATTERN.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("unsupported complete subgroup-rate condition")
    weight, total, female = (percent(match[k]) for k in ("w", "t", "b"))
    if weight == 0:
        raise UnsupportedCondition(
            "a randomly selected man requires a nonempty male population"
        )
    male = checked((total - (1 - weight) * female) / weight)
    return content, condition, answer, solution, weight, total, female, male


def render_svg(weight, female):
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="255" viewBox="0 0 760 255">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#111"/></marker></defs><g font-family="Times New Roman,serif" font-size="20" fill="#111">',
    ]

    def edge(x1, y1, x2, y2, label=None):
        parts.append(
            f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="#111" stroke-width="1.6" marker-end="url(#arrow)"/>'
        )
        if label:
            parts.append(
                f'<text x="{(x1 + x2) / 2 - 15}" y="{(y1 + y2) / 2 - 8}" text-anchor="middle">{escape(label)}</text>'
            )

    def box(x, y, w, text):
        parts.append(
            f'<rect x="{x - w / 2}" y="{y - 17}" width="{w}" height="27" fill="white" stroke="#5976bf" stroke-width="1.4"/><text x="{x}" y="{y + 3}" text-anchor="middle">{text}</text>'
        )

    edge(350, 38, 185, 93, format_answer(weight))
    edge(410, 38, 575, 93, format_answer(1 - weight))
    edge(170, 124, 70, 204)
    edge(200, 124, 285, 204, "x")
    edge(560, 124, 465, 204)
    edge(590, 124, 690, 204, format_answer(female))
    box(380, 26, 210, "взрослое население")
    box(185, 111, 110, "мужчины")
    box(575, 111, 125, "женщины")
    for x, title, width in [
        (80, "трудоспособны", 145),
        (290, "пенсионеры", 130),
        (470, "трудоспособны", 145),
        (685, "пенсионеры", 130),
    ]:
        box(x, 226, width, title)
    parts.append("</g></svg>")
    return "".join(parts)


def required_assets(context):
    *_, weight, _total, female, _male = _input(context)
    source = _REUSE.get((weight, female))
    return (
        ({"source_asset_id": source, "section_id": "solution:1", "alt_text": _ALT},)
        if source
        else ()
    )


def diagram_specs(context):
    *_, weight, _total, female, _male = _input(context)
    return (
        ()
        if (weight, female) in _REUSE
        else (diagrams.spec(_KEY, render_svg(weight, female)),)
    )


def build_context_repair_plan(context, *, generated_solution_assets=()):
    content, condition, answer_section, solution, weight, total, female, male = _input(
        context
    )
    women = 1 - weight
    pension_women = women * female
    pension_men = total - pension_women
    html = (
        "<p>Первый способ. Вычтем долю женщин-пенсионеров из общей доли пенсионеров, затем найдём условную долю среди мужчин:</p>"
        + line(rf"P(Ж)=1-{fmt(weight)}={fmt(women)}")
        + line(rf"P(Ж\cap П)={fmt(women)}\cdot {fmt(female)}={fmt(pension_women)}")
        + line(rf"P(М\cap П)={fmt(total)}-{fmt(pension_women)}={fmt(pension_men)}")
        + line(rf"P(П\mid М)=\frac{{{fmt(pension_men)}}}{{{fmt(weight)}}}={fmt(male)}")
    )
    html += "<p>Второй способ. Пусть x — неизвестная доля пенсионеров среди мужчин. Построим дерево вероятностей:</p>"
    figure, key, changes = diagrams.image(
        content,
        _KEY,
        _ALT,
        source_id=_REUSE.get((weight, female)),
        svg=render_svg(weight, female),
        generated=generated_solution_assets,
    )
    html += figure
    html += (
        "<p>По формуле полной вероятности доля пенсионеров складывается из двух ветвей:</p>"
        + line(rf"{fmt(weight)}x+{fmt(women)}\cdot {fmt(female)}={fmt(total)}")
        + line(rf"{fmt(weight)}x={fmt(pension_men)}")
        + line(rf"x=\frac{{{fmt(pension_men)}}}{{{fmt(weight)}}}")
    )
    answer, html = result(male, html)
    return diagrams.repair(
        condition, answer_section, solution, answer, html, (key,), changes
    )
