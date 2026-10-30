"""Monotonic intervals and global extrema from a reviewed sign chart."""

import re
from dataclasses import dataclass
from fractions import Fraction

from ..equations.linear_system_intervals import Interval, interval_latex
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from . import graph_input, graph_primitive_example, graph_value_order
from .common import answer
from .graph_monotonic_chart import (
    band_latex,
    bounds,
    chart,
    describe,
    global_point,
    integers,
)
from .graph_stationary import interval

_PREFIX = re.compile(
    r"На рисунке изображен график (?P<graph>производной функции f\(x\)|y=f'\(x\)— производной функции (?:y=)?f\(x\)|функции y=f\(x\)), определенной на интервале(?P<domain>\([^)]*\))\. (?P<request>.+)"
)
_FUNCTION = re.compile(
    r"Функция (?:y=)?f\(x\)определена(?P<continuous> и непрерывна)? на (?:промежутке|отрезке|интервале|полуинтервале)\s*(?P<domain>[\[(][^;]+;[^\])]+[\])])\. На рисунке изображен график ее производной\. (?P<request>.+)"
)
_MONOTONIC = re.compile(
    r"Найдите промежутки (?P<direction>возрастания|убывания) функции f\(x\)\. В ответе укажите (?P<operation>сумму целых точек, входящих в эти промежутки|длину наибольшего из них)\."
)
_ENDPOINT = re.compile(
    r"В какой точке отрезка\s*(?P<span>\[[^]]+\])\s*(?:функция )?f\(x\)принимает (?P<target>наибольшее|наименьшее) значение[?.]"
)
_COUNT = (
    "Определите количество целых точек, в которых производная функции положительна."
)
_VALUE = re.compile(
    r"Найдите наименьшее значение функции f\(x\)на отрезке\s*(?P<span>\[[^]]+\])\."
)
_COMPARISON = re.compile(
    r"Найдите точку x_0, в которой функция (?:y=f\(x\)|f\(x\))?\s*принимает (?P<target>наименьшее|наибольшее) значение, если f\((?P<a>-?\d+)\)(?P<op>=|≥|>|\\lt|<|\\leq)\s*f\((?P<b>-?\d+)\)\.?"
)
_CONTINUITY = (
    "<p>Если функция непрерывна на отрезке, а её производная положительна "
    "(отрицательна) внутри него, то функция возрастает (убывает) на всём отрезке. "
    "Внутренние точки, где производная равна нулю, присоединяем к промежуткам монотонности.</p>"
)
_NOTE = (
    "<p><b>Примечание.</b> Если функция непрерывна на конце промежутка монотонности, "
    "эту граничную точку присоединяют к промежутку. Непрерывная функция монотонна "
    "и тогда, когда её производная сохраняет знак всюду, кроме конечного числа "
    "точек, в которых производная может не существовать.</p>"
    "<p>Например, для непрерывной функции</p>"
    + line(
        r"f(x)=x+\frac{|x|}{2}=\begin{cases}\frac{x}{2},&x<0,\\\frac{3x}{2},&x\geq0\end{cases}"
    )
    + "<p>производная не существует при нуле и положительна во всех остальных точках. "
    "Поэтому функция возрастает на всей числовой прямой.</p>"
)


@dataclass(frozen=True)
class Question:
    domain: Interval
    derivative: bool
    continuous: bool
    operation: str
    sign: int = 1
    target: str = ""
    span: Interval | None = None
    comparisons: tuple = ()


def parse(text):
    text = text.replace("−", "-").replace("–", "-")
    match = _PREFIX.fullmatch(text)
    stated = _FUNCTION.fullmatch(text)
    if not match and not stated:
        raise UnsupportedCondition("a complete monotonicity graph question is required")
    source = match or stated
    domain = interval(source["domain"])
    derivative = not match or "производной" in match["graph"]
    continuous = bool(stated and stated["continuous"])
    request = source["request"]
    monotonic = _MONOTONIC.fullmatch(request)
    if monotonic:
        return Question(
            domain,
            derivative,
            continuous,
            "sum" if monotonic["operation"].startswith("сумму") else "length",
            1 if monotonic["direction"] == "возрастания" else -1,
        )
    if request == _COUNT and not derivative:
        return Question(domain, derivative, continuous, "count")
    value = _VALUE.fullmatch(request)
    if value and not derivative:
        return Question(
            domain,
            derivative,
            continuous,
            "value",
            target="наименьшее",
            span=interval(value["span"]),
        )
    comparison = _COMPARISON.fullmatch(request)
    if comparison and derivative:
        op = comparison["op"].replace(r"\lt", "<").replace("≥", r"\geq")
        return Question(
            domain,
            derivative,
            continuous,
            "global",
            target=comparison["target"],
            span=domain,
            comparisons=((Fraction(comparison["a"]), op, Fraction(comparison["b"])),),
        )
    endpoint = _ENDPOINT.fullmatch(request)
    if endpoint and derivative:
        return Question(
            domain,
            derivative,
            continuous,
            "global",
            target=endpoint["target"],
            span=interval(endpoint["span"]),
        )
    if (
        request
        == "Найдите абсциссу точки, в которой функция y=f(x)принимает наибольшее значение."
    ):
        return Question(
            domain, derivative, continuous, "global", target="наибольшее", span=domain
        )
    raise UnsupportedCondition("the entire monotonicity request must be recognized")


def global_proof(question, bands, labels, constraints):
    comparison_html = ""
    if question.comparisons:
        result, comparison_html = graph_value_order.extremum(question, bands)
    else:
        result = global_point(question, bands)
    html = (
        _CONTINUITY
        + "<p>Определим промежутки возрастания и убывания по знаку производной:</p>"
    )
    for b in bands:
        html += line(
            r"f\ "
            + (r"\nearrow" if b[4] > 0 else r"\searrow")
            + r"\quad x\in"
            + band_latex(b, labels)
        )
    html += (
        constraints
        + comparison_html
        + "<p>Учитывая направление изменения функции на заданном промежутке, получаем точку, в которой достигается "
        + question.target
        + " значение:</p>"
    )
    html += line(r"x\in" + interval_latex(question.span)) + line(
        "x_0=" + answer(result)
    )
    return answer(result), html


def proof(question, bands, entry):
    labels, constraints = describe(bands)
    if question.operation == "global":
        return global_proof(question, bands, labels, constraints)
    if question.operation == "value":
        return graph_value_order.minimum_value(question, bands, entry)
    selected = [b for b in bands if b[4] == question.sign]
    if not selected:
        raise UnsupportedCondition("no requested monotonic interval was established")
    direction = "возрастает" if question.sign > 0 else "убывает"
    html = _CONTINUITY if question.derivative else ""
    html += (
        "<p>"
        + ("По знаку производной" if question.derivative else "Из графика")
        + " определяем промежутки, на которых функция "
        + direction
        + ":</p>"
    )
    for point in entry.get("zero_points", []):
        if not point.get("defined", True) and question.continuous:
            html += "<p>В указанной точке производная не существует:</p>" + line(
                "x=" + answer(point["x"])
            )
            html += "<p>Функция в ней непрерывна. Поэтому присоединяем эту точку к соседним промежуткам монотонности; при одинаковом направлении изменения объединяем их.</p>"
    for b in selected:
        html += line(r"x\in" + band_latex(b, labels))
    html += constraints
    if question.operation in ["sum", "count"]:
        values = integers(selected, question.domain)
        html += (
            "<p>Найдём целые точки, входящие в эти промежутки, и сложим их абсциссы:</p>"
            if question.operation == "sum"
            else "<p>Производная положительна внутри указанных промежутков возрастания. Подсчитаем целые точки:</p>"
        )
        html += line(r"x\in\{" + ";".join(map(str, values)) + r"\}")
        terms = "+".join("(" + str(x) + ")" if x < 0 else str(x) for x in values) or "0"
        result = sum(values) if question.operation == "sum" else len(values)
        html += (
            line("S=" + terms + "=" + str(result))
            if question.operation == "sum"
            else line("N=" + str(result))
        )
        if question.operation == "count":
            html += "<p><b>Примечание.</b> Целые точки — это точки с целыми абсциссами. Значения функции в них могут быть нецелыми. В точках экстремума производная равна нулю, поэтому их не учитываем.</p>"
    else:
        exact = [
            (bounds(b[1])[0] - bounds(b[0])[0], b)
            for b in selected
            if "x" in b[0] and "x" in b[1]
        ]
        if not exact:
            raise UnsupportedCondition("an exact longest interval is required")
        result, longest = max(exact, key=lambda item: item[0])
        if any(
            bounds(b[1])[1] - bounds(b[0])[0] > result
            for b in selected
            if b is not longest
        ):
            raise UnsupportedCondition(
                "the longest interval cannot be determined exactly"
            )
        html += "<p>Наибольший из этих промежутков:</p>" + line(
            r"x\in" + band_latex(longest, labels)
        )
        html += "<p>Его длина равна разности правой и левой границ:</p>"
        html += line(
            "L="
            + answer(longest[1]["x"])
            + "-("
            + answer(longest[0]["x"])
            + ")="
            + answer(result)
        )
    if question.continuous:
        html += _NOTE
    return answer(result), html


def _input(context):
    data = graph_input.read_graph(context)
    question = parse(data[4])
    entry = data[5]
    if (
        entry.get("illustration_comparison")
        and tuple(
            (Fraction(a), op, Fraction(b))
            for a, op, b in entry["illustration_comparison"]
        )
        != question.comparisons
    ):
        raise UnsupportedCondition(
            "the source illustration does not match the stated value comparison"
        )
    bands = chart(entry, question)
    if question.operation == "global" and any(not b[2] for b in bands[1:]):
        raise UnsupportedCondition(
            "global extrema require continuity at every derivative exception"
        )
    return data, question, bands


def required_assets(context):
    data, _, _ = _input(context)
    entry = data[5]
    return tuple(
        {
            "source_asset_id": asset["source_id"],
            "section_id": "solution:1",
            "alt_text": entry["solution_alt"],
        }
        for asset in ([entry["solution_asset"]] if entry.get("solution_asset") else [])
        + entry.get("extra_solution_assets", [])
    )


def diagram_specs(context):
    data, _, _ = _input(context)
    entry = data[5]
    return (
        (
            solution_diagrams.spec(
                entry["diagram_key"], graph_primitive_example.render(entry)
            ),
        )
        if entry.get("primitive_example")
        else ()
    )


def figures(content, entry, generated):
    all_assets = (
        [entry["solution_asset"]] if entry.get("solution_asset") else []
    ) + entry.get("extra_solution_assets", [])
    if not all_assets:
        svg = (
            graph_primitive_example.render(entry)
            if entry.get("primitive_example")
            else None
        )
        html, key, changes = graph_input.figure(
            content, entry, svg=svg, generated=generated
        )
        return html, (key,) if key else (), changes, ""
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    allowed = {a["source_id"] for a in all_assets}
    if any(
        a["asset_id"] not in allowed and a["asset_key"] not in condition["asset_keys"]
        for a in content["assets"]
    ):
        raise UnsupportedCondition("an unrelated solution illustration is present")
    htmls, keys = [], []
    for asset in all_assets:
        selected = {
            **content,
            "assets": [
                a
                for a in content["assets"]
                if a["asset_id"] == asset["source_id"]
                or a["asset_key"] in condition["asset_keys"]
            ],
        }
        html, key, _ = graph_input.figure(selected, {**entry, "solution_asset": asset})
        htmls.append(html)
        keys.append(key)
    return htmls[0], tuple(keys), (), "".join(htmls[1:])


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data, question, bands = _input(context)
    content, condition, ans, solution, _, entry, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    result, html = proof(question, bands, entry)
    figure, keys, changes, extra = figures(content, entry, generated_solution_assets)
    if figure and entry.get("primitive_example"):
        html += (
            "<p>График одной из непрерывных функций, соответствующих заданной производной:</p>"
            + figure
        )
        figure = ""
    if extra:
        html += (
            "<p><b>Примечание.</b> Непрерывность на концах существенна. Если в правом конце был бы разрыв, значение в этой точке могло бы оказаться ниже внутреннего минимума:</p>"
            + extra
        )
    return solution_diagrams.repair(
        condition, ans, solution, result, figure + html, keys, changes
    )
