"""Two dependent events with supplied marginals and intersection probability."""

import re
from fractions import Fraction
from html import escape

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import format_answer, parse_rational

from . import solution_diagrams as diagrams
from .bernoulli import checked, fmt, result
from .common import NUMBER, UnsupportedCondition, line, normalize

_BASIC = re.compile(
    rf"В торговом центре два одинаковых автомата продают кофе\. Вероятность того, что к концу дня в автомате закончится кофе, равна (?P<p>{NUMBER})\. Вероятность того, что кофе закончится в обоих автоматах, равна (?P<j>{NUMBER})\. Найдите вероятность того, что к концу дня кофе останется в обоих автоматах\."
)
_EVENING = re.compile(
    rf"В торговом центре два одинаковых автомата продают кофе\. Обслуживание автоматов происходит по вечерам после закрытия центра\. Известно, что вероятность события «К вечеру в первом автомате закончится кофе» равна (?P<p>{NUMBER})\. Такая же вероятность события «К вечеру во втором автомате закончится кофе»\. Вероятность того, что кофе к вечеру закончится в обоих автоматах, равна (?P<j>{NUMBER})\. Найдите вероятность того, что к вечеру кофе останется в обоих автоматах\."
)
_EXACTLY_ONE = re.compile(
    rf"В (?P<place>аэропорту|торговом центре) два одинаковых автомата продают (?P<drink>чай|кофе)\. Вероятность того, что к концу дня в первом автомате закончится (?P=drink), равна (?P<p>{NUMBER})\. Такова же вероятность, что (?P=drink) закончится во втором автомате\. Вероятность того, что (?P=drink) закончится в обоих автоматах, равна (?P<j>{NUMBER})\. Найдите вероятность того, что к концу дня (?:(?:в одном из автоматов (?P=drink) закончится, а в другом — нет)|(?:(?P=drink) останется только в одном из автоматов))\."
)
_REUSE = {
    (Fraction(3, 10), Fraction(3, 25)): "415eec67-8d2e-47bd-a8ab-89dc740d3093",
    (Fraction(1, 4), Fraction(3, 20)): "f762becb-74d9-4165-ab63-365dbc6d0ce3",
}
_KEY = "generated_joint_probability_table"
_ALT = "Таблица совместных исходов двух автоматов"


def joint_distribution(a, b, j):
    checked(a)
    checked(b)
    checked(j)
    cells = (1 - a - b + j, b - j, a - j, j)
    if any(x < 0 for x in cells):
        raise UnsupportedCondition(
            "the supplied marginal and intersection probabilities are inconsistent"
        )
    return cells


def _input(context):
    content, condition, answer, solution, text = diagrams.read(context)
    text = normalize(text)
    match = (
        _BASIC.fullmatch(text)
        or _EVENING.fullmatch(text)
        or _EXACTLY_ONE.fullmatch(text)
    )
    if match is None:
        raise UnsupportedCondition("unsupported complete joint-event condition")
    p, j = parse_rational(match["p"]), parse_rational(match["j"])
    cells = joint_distribution(p, p, j)
    one = "drink" in match.re.groupindex
    return content, condition, answer, solution, p, j, cells, one


def required_assets(context):
    *_, p, j, _cells, one = _input(context)
    source = _REUSE.get((p, j)) if not one else None
    return (
        ({"source_asset_id": source, "section_id": "solution:1", "alt_text": _ALT},)
        if source
        else ()
    )


def render_svg(p, j):
    cells = joint_distribution(p, p, j)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="285" viewBox="0 0 720 285">',
        '<g font-family="Times New Roman,serif" font-size="15" fill="#111">',
    ]

    def text(x, y, value, color="#111", size=15):
        parts.append(
            f'<text x="{x}" y="{y}" text-anchor="middle" fill="{color}" font-size="{size}">{escape(str(value))}</text>'
        )

    for panel, offset in enumerate((0, 370)):
        x = 75 + offset
        y = 92
        w = 116
        h = 75
        text(x + w, 23, "Первый автомат", size=18)
        for col, title in enumerate(("Кофе остался", "Кофе закончился")):
            text(x + w * (col + 0.5), 63, title)
        parts.append(
            f'<text x="{25 + offset}" y="167" transform="rotate(-90 {25 + offset} 167)" text-anchor="middle">Второй автомат</text>'
        )
        for row, title in enumerate(("Кофе остался", "Кофе закончился")):
            parts.append(
                f'<text transform="translate({50 + offset} {y + h * (row + 0.5)}) rotate(-90)" text-anchor="middle" font-size="13"><tspan x="0" y="-6">Кофе</tspan><tspan x="0" y="9">{title.split()[1]}</tspan></text>'
            )
        parts.append(
            f'<rect x="{x}" y="{y}" width="{2 * w}" height="{2 * h}" fill="none" stroke="#111"/>'
        )
        parts.append(
            f'<path d="M{x + w} {y}v{2 * h} M{x} {y + h}h{2 * w}" fill="none" stroke="#111"/>'
        )
        if panel == 0:
            text(x + w * 0.5, y + h * 0.5 + 6, "?", size=25)
            text(x + w * 1.5, y + h * 1.5 + 6, format_answer(j), size=23)
            parts.append(
                f'<rect x="{x + 6}" y="{y + h + 6}" width="{2 * w + 12}" height="{h - 12}" fill="none" stroke="#5876c9"/>'
            )
            parts.append(
                f'<rect x="{x + w + 6}" y="{y + 6}" width="{w - 12}" height="{2 * h + 12}" fill="none" stroke="#37a4cd"/>'
            )
            text(x + 2 * w + 23, y + h * 1.5 + 6, format_answer(p), "#5876c9", 16)
            text(x + w * 1.5, y + 2 * h + 24, format_answer(p), "#37a4cd", 16)
        else:
            for index, value in enumerate(cells):
                row, col = divmod(index, 2)
                color = ("#14a83b", "#37a4cd", "#5876c9", "#111")[index]
                text(
                    x + w * (col + 0.5),
                    y + h * (row + 0.5) + 6,
                    format_answer(value),
                    color,
                    22,
                )
    parts.append("</g></svg>")
    return "".join(parts)


def diagram_specs(context):
    *_, p, j, _cells, one = _input(context)
    return () if one or (p, j) in _REUSE else (diagrams.spec(_KEY, render_svg(p, j)),)


def _neither(p, j, complement_first):
    value = 1 - 2 * p + j
    union = 2 * p - j
    direct = (
        "<p>Пусть A и B означают, что кофе закончился в первом и втором автоматах. По формуле суммы совместных событий:</p>"
        + line(r"P(A\cup B)=P(A)+P(B)-P(A\cap B)")
        + line(rf"P(A\cup B)={fmt(p)}+{fmt(p)}-{fmt(j)}={fmt(union)}")
    )
    direct += (
        "<p>Кофе останется в обоих автоматах в противоположном случае:</p>"
        + line(rf"P(\overline{{A}}\cap\overline{{B}})=1-{fmt(union)}={fmt(value)}")
    )
    remaining = (
        "<p>Другой способ. Вероятность остатка кофе в каждом автомате равна 1−p, а хотя бы в одном — 1−P(A∩B). По той же формуле объединения выразим совместный остаток:</p>"
        + line(rf"P(\overline{{A}})=P(\overline{{B}})=1-{fmt(p)}={fmt(1 - p)}")
        + line(rf"{fmt(1 - j)}={fmt(1 - p)}+{fmt(1 - p)}-x")
        + line(rf"x={fmt(1 - p)}+{fmt(1 - p)}-{fmt(1 - j)}={fmt(value)}")
    )
    if complement_first:
        remaining = remaining.replace("Другой способ. ", "")
        direct = "<p>Другой способ.</p>" + direct
    return value, (remaining + direct if complement_first else direct + remaining)


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    content, condition, answer_section, solution, p, j, cells, one = _input(context)
    if one:
        html = (
            "<p>Сначала найдём вероятность того, что содержимое закончится хотя бы в одном автомате. События совместны:</p>"
            + line(rf"P(A\cup B)={fmt(p)}+{fmt(p)}-{fmt(j)}={fmt(2 * p - j)}")
        )
        html += (
            "<p>Чтобы осталось ровно одно событие, исключим одновременное наступление обоих:</p>"
            + line(rf"P(A\triangle B)=P(A\cup B)-P(A\cap B)={fmt(2 * p - j)}-{fmt(j)}")
        )
        answer, html = result(cells[1] + cells[2], html)
        return diagrams.repair(condition, answer_section, solution, answer, html)
    if not parent_solution_html.strip():
        raise UnsupportedCondition(
            "joint-event solution requires the parent method order"
        )
    readable = " ".join(
        BeautifulSoup(parent_solution_html, "html.parser")
        .get_text(" ", strip=True)
        .replace("\xad", "")
        .split()
    )
    complement_first = readable.startswith("Вероятность того, что кофе останется")
    value, html = _neither(p, j, complement_first)
    if j != p * p:
        html += (
            "<p>События не независимы: данная вероятность их пересечения отличается от произведения вероятностей:</p>"
            + line(rf"P(A\cap B)={fmt(j)}\ne ({fmt(p)})^2={fmt(p * p)}")
        )
    figure, key, asset_changes = diagrams.image(
        content,
        _KEY,
        _ALT,
        source_id=_REUSE.get((p, j)),
        svg=render_svg(p, j),
        generated=generated_solution_assets,
    )
    html += "<p>Проверим расчёт в таблице совместных исходов:</p>" + figure
    answer, html = result(value, html)
    return diagrams.repair(
        condition, answer_section, solution, answer, html, (key,), asset_changes
    )
