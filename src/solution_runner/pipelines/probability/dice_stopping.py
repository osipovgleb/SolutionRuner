"""Positive dice increments: hitting a sum and the number of throws at that time."""

import re
from dataclasses import replace
from fractions import Fraction

from . import solution_diagrams as diagrams
from .bernoulli import fmt
from .common import (
    COUNT,
    UnsupportedCondition,
    count,
    line,
    normalize,
    rewrite,
    rounded,
)

_PATTERN = re.compile(
    rf"Правильный игральный кубик бросили несколько десятков раз\. Известно, что в какой-то момент сумма выпавших при бросаниях очков оказалась равна (?P<total>\d+)\. Какова вероятность того, что к этому моменту (?:был сделан ровно|было сделано ровно) (?P<throws>{COUNT}) брос(?:ок|ка|ков)\? Ответ округлите до сотых\."
)

_STOPPED = re.compile(
    rf"Правильный игральный кубик бросали до тех пор, пока сумма выпавших при всех бросках очков не стала больше чем (?P<threshold>\d+)\. Известно, что общая сумма очков оказалась равна (?P<total>\d+)\. Какова вероятность того, что (?:был сделан ровно|было сделано ровно) (?P<throws>{COUNT}) брос(?:ок|ка|ков)\? Ответ округлите до сотых\."
)
_INCOMPLETE = re.compile(
    rf"(?:Правильный игральный кубик бросали до тех пор, пока сумма выпавших при всех бросках очков не стала равна (?P<t1>\d+)|Игральную кость бросили один или несколько раз\. Оказалось, что сумма всех выпавших очков равна (?P<t2>\d+))\. Какова вероятность того, что (?:был сделан (?:ровно )?|было сделано (?:ровно )?)(?P<throws>{COUNT}) брос(?:ок|ка|ков)\? Ответ округлите до сотых\."
)
_CLARIFIED = re.compile(
    r"Правильный игральный кубик бросали до первого момента, когда сумма всех выпавших очков стала не меньше (?P<total>\d+)\. Известно, что в этот момент сумма оказалась равна (?P<same>\d+)\. Найдите условную вероятность того, что к этому моменту было сделано ровно (?P<throws>\d+) бросков\. Ответ округлите до сотых\."
)
_REUSE = {
    (4, 1): "fb5809fb-c1dc-4db5-9d75-4748838fb3c5",
    (4, 3): "9059a0a1-820a-4baa-af74-bdaf310bb43d",
    (3, 2): "57d2d395-4c35-4174-8b2d-1e3c4ef28934",
    (3, 1): "3471b26f-2427-43e1-a19b-6d5d18b089a9",
}
_KEY = "generated_hitting_sum_tree"
_ALT = "Дерево бросков до достижения заданной суммы"


def _input(context):
    content, condition, answer, solution, text = diagrams.read(context)
    text = normalize(text)
    stopped = _STOPPED.fullmatch(text)
    incomplete = _INCOMPLETE.fullmatch(text)
    clarified = _CLARIFIED.fullmatch(text)
    match = stopped or _PATTERN.fullmatch(text) or incomplete or clarified
    if match is None:
        raise UnsupportedCondition("unsupported complete hitting-sum condition")
    total = int((match["t1"] or match["t2"]) if incomplete else match["total"])
    if clarified and int(clarified["same"]) != total:
        raise UnsupportedCondition("the final sum must equal the stopping boundary")
    throws = count(match["throws"])
    if stopped and (int(match["threshold"]) != total - 1 or total > 4):
        raise UnsupportedCondition(
            "illustrated stopping sums must be 1–4 and exactly one above the threshold"
        )
    if not stopped and total > 24:
        raise UnsupportedCondition(
            "the observation horizon does not guarantee observing this target"
        )
    conditional_hitting_probability(total, throws)
    clarification = (
        f"Правильный игральный кубик бросали до первого момента, когда сумма всех выпавших очков стала не меньше {total}. Известно, что в этот момент сумма оказалась равна {total}. Найдите условную вероятность того, что к этому моменту было сделано ровно {throws} бросков. Ответ округлите до сотых."
        if incomplete
        else ""
    )
    return (
        content,
        condition,
        answer,
        solution,
        total,
        throws,
        bool(stopped),
        clarification,
    )


def render_svg(total, throws):
    conditional_hitting_probability(total, throws)
    if total > 4:
        raise UnsupportedCondition("the illustrated tree supports sums up to four")
    leaves = [1]
    for remaining in range(1, total + 1):
        leaves.append(sum(leaves[:remaining]) + (remaining < 6))
    width = max(900, 200 + 75 * leaves[total])
    height = 70 + 90 * total
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><g font-family="Times New Roman,serif" font-size="16">'
    ]

    def branch(s, depth, x, left, right):
        choices = total - s
        unit = (right - left) / leaves[choices]
        cursor = left
        for face in range(1, choices + 2):
            invalid = face == choices + 1
            if invalid and choices == 6:
                continue
            span = unit * (1 if invalid else leaves[choices - face])
            child_left = cursor
            cx = cursor + span / 2
            cursor += span
            cy = 50 + 90 * (depth + 1)
            color = "#ff0000" if invalid else "#1647b3"
            parts.append(
                f'<path d="M{x} {50 + 90 * depth}L{cx} {cy}" stroke="{color}" fill="none"/>'
            )
            numerator = 6 - choices if invalid else 1
            mx = (x + cx) / 2
            my = (50 + 90 * depth + cy) / 2
            parts.append(
                f'<rect x="{mx - 10}" y="{my - 17}" width="20" height="31" fill="white"/><text x="{mx}" y="{my - 4}" text-anchor="middle" fill="{color}">{numerator}</text><path d="M{mx - 7} {my}h14" stroke="{color}"/><text x="{mx}" y="{my + 14}" text-anchor="middle" fill="{color}">6</text>'
            )
            if invalid:
                label = (
                    ",".join(str(f) for f in range(choices + 1, 7))
                    if choices > 2
                    else f"{choices + 1},…,6"
                )
                parts.append(
                    f'<text x="{cx}" y="{cy + 5}" fill="red" text-anchor="middle">{label}</text>'
                )
                continue
            final = s + face == total
            fill = "#9bd3ab" if final and depth + 1 == throws else "white"
            stroke = "#1647b3" if final else "black"
            parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="12" stroke="{stroke}" fill="{fill}"/><text x="{cx}" y="{cy + 5}" text-anchor="middle">{face}</text>'
            )
            if not final:
                branch(
                    s + face,
                    depth + 1,
                    cx,
                    child_left,
                    child_left + span,
                )

    branch(0, 0, width / 2, 180, width - 30)
    for k in range(1, total + 1):
        parts.append(f'<text x="8" y="{55 + 90 * k}">Бросок {k}</text>')
    parts.append("</g></svg>")
    return "".join(parts)


def required_assets(context):
    *_, total, throws, stopped, _clarification = _input(context)
    source = _REUSE.get((total, throws)) if stopped else None
    return (
        ({"source_asset_id": source, "section_id": "solution:1", "alt_text": _ALT},)
        if source
        else ()
    )


def diagram_specs(context):
    *_, total, throws, stopped, _clarification = _input(context)
    return (
        (diagrams.spec(_KEY, render_svg(total, throws)),)
        if stopped and (total, throws) not in _REUSE
        else ()
    )


def hitting_counts(total):
    if not isinstance(total, int) or not 1 <= total <= 60:
        raise UnsupportedCondition("supported target sums are integers from 1 to 60")
    counts = []
    previous = [0] * (total + 1)
    previous[0] = 1
    for _ in range(total):
        current = [0] * (total + 1)
        for s in range(1, total + 1):
            current[s] = sum(previous[max(0, s - 6) : s])
        counts.append(current[total])
        previous = current
    return tuple(counts)


def conditional_hitting_probability(total, throws):
    counts = hitting_counts(total)
    if not isinstance(throws, int) or not 1 <= throws <= total:
        raise UnsupportedCondition(
            "the requested hitting time must be from 1 to the target sum"
        )
    probabilities = tuple(Fraction(c, 6**k) for k, c in enumerate(counts, 1))
    return probabilities[throws - 1] / sum(probabilities), counts, probabilities


def build_context_repair_plan(context, *, generated_solution_assets=()):
    (
        content,
        condition,
        answer_section,
        solution,
        total,
        throws,
        stopped,
        clarification,
    ) = _input(context)
    value, counts, probabilities = conditional_hitting_probability(total, throws)
    prefix = ""
    if stopped:
        completed = [c * 6 ** (total - k) for k, c in enumerate(counts, 1)]
        prefix = f"<p>Способ 1. Дополним каждую допустимую последовательность произвольными результатами до общей длины {total}. Теперь все полные последовательности равновероятны. Последовательность длины k допускает 6⁽ⁿ⁻ᵏ⁾ дополнений, где n — заданная сумма:</p>"
        prefix += line(
            r"N(A)=" + "+".join(str(c) for c in completed if c) + f"={sum(completed)}"
        )
        prefix += line(
            rf"P(B\mid A)=\frac{{{completed[throws - 1]}}}{{{sum(completed)}}}={fmt(value)}"
        )
        prefix += "<p>Способ 2. Применим условные вероятности непосредственно.</p>"
    html = f"<p>Получить {total} при нескольких бросаниях кубика можно за разное число бросков. Каждая последовательность длины k имеет вероятность 1/6ᵏ. Поскольку все результаты положительны, сумма {total} достигается не более одного раза и не позже {total}-го броска.</p>"
    html += "<p>Посчитаем последовательности с нужной суммой для каждой длины. При необходимости используем N(k,s)=N(k−1,s−1)+…+N(k−1,s−6), где N(0,0)=1, а невозможные суммы дают ноль:</p>"
    for k, c in enumerate(counts, 1):
        if c:
            html += line(
                rf"P(S_{{{k}}}={total})=\frac{{{c}}}{{6^{{{k}}}}}={fmt(probabilities[k - 1])}"
            )
    html += "<p>Пусть A — событие достижения заданной суммы, а B — достижение её за указанное число бросков. Случаи с разным числом бросков несовместны, поэтому их вероятности складываются:</p>"
    html += line(
        r"P(A)="
        + "+".join(fmt(p) for p in probabilities if p)
        + "="
        + fmt(sum(probabilities))
    )
    html += "<p>Применим формулу условной вероятности:</p>"
    html += line(
        rf"P(B\mid A)=\frac{{P(A\cap B)}}{{P(A)}}=\frac{{{fmt(probabilities[throws - 1])}}}{{{fmt(sum(probabilities))}}}={fmt(value)}"
    )
    html = prefix + html
    keys = ()
    asset_changes = ()
    if stopped:
        html += "<p>Способ 3. Построим дерево вариантов. Красные ветви превышают заданную сумму и не входят в событие A. Выделенные конечные вершины достигают суммы за нужное число бросков. Вероятность каждого пути равна произведению вероятностей его рёбер:</p>"
        figure, key, asset_changes = diagrams.image(
            content,
            _KEY,
            _ALT,
            source_id=_REUSE.get((total, throws)),
            svg=render_svg(total, throws),
            generated=generated_solution_assets,
        )
        keys = (key,)
        html += figure + line(
            rf"P(B\mid A)=\frac{{{fmt(probabilities[throws - 1])}}}{{{fmt(sum(probabilities))}}}={fmt(value)}"
        )
        html += "<p>Примечание. Пути разной длины не равновероятны. Делить число подходящих коротких путей на общее число путей нельзя; одинаковую вероятность имеют только дополненные до общей длины последовательности первого способа.</p>"
    answer = rounded(value, 2)
    html += line(rf"P(B\mid A)\approx {answer.replace(',', '{,}')}")
    plan = diagrams.repair(
        condition, answer_section, solution, answer, html, keys, asset_changes
    )
    if clarification:
        correction = rewrite(
            condition,
            "condition",
            condition.get("title") or "Условие",
            "<p>" + clarification + "</p>",
        )
        return replace(plan, transformations=(correction,) + plan.transformations)
    return plan
