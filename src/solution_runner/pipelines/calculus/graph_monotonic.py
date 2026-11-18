"""Monotonic intervals and global extrema from a reviewed sign chart."""

import re
from dataclasses import dataclass
from fractions import Fraction
from html import escape
from xml.etree import ElementTree as ET

from ..equations.linear_system_intervals import Interval, interval_latex
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from . import (
    graph_condition_layout,
    graph_input,
    graph_primitive_example,
    graph_value_order,
    tangent_native,
)
from .common import answer
from .graph_monotonic_chart import (
    band_latex,
    bounds,
    chart,
    describe,
    global_point,
    integers,
    longest_band,
)
from .graph_reading import NOTE
from .graph_stationary import interval

_PREFIX = re.compile(
    r"На рисунке изображен график (?P<graph>производной функции f\(x\)|(?:функции )?y=f'\(x\)— производной функции (?:y=)?f\(x\)|производной y=f'\(x\)функции y=f\(x\)|функции y=f\(x\)), определенной на интервале(?P<domain>\([^)]*\))\. (?P<request>.+)"
)
_FUNCTION = re.compile(
    r"Функция (?:y=)?f\(x\)определена(?P<continuous> и непрерывна)? на (?:промежутке|отрезке|интервале|полуинтервале)\s*(?P<domain>[\[(][^;]+;[^\])]+[\])])\. На рисунке изображен график ее производной\. (?P<request>.+)"
)
_MONOTONIC = re.compile(
    r"Найдите промежутки (?P<direction>возрастания|убывания) функции (?:y=)?f\(x\)\. В ответе укажите (?P<operation>сумму целых точек, входящих в эти промежутки|длину наибольшего из них)\."
)
_ENDPOINT = re.compile(
    r"В какой точке отрезка\s*(?P<span>\[[^]]+\])\s*(?:функция )?(?:y=)?f\(x\),?\s*принимает (?P<target>наибольшее|наименьшее) значение[?.]"
)
_ENDPOINT_WITHOUT_DOMAIN = re.compile(
    r"На рисунке изображен график производной функции (?:y=)?f\(x\)\. "
    r"(?:В какой точке отрезка\s*(?P<span>\[[^]]+\])\s*(?:функция )?(?:y=)?f\(x\)принимает "
    r"(?P<target>наибольшее|наименьшее) значение|При каком значении x эта функция принимает "
    r"свое (?P<inverted_target>наибольшее|наименьшее) значение на отрезке\s*(?P<inverted_span>\[[^]]+\]))[?.]"
)
_COUNT = (
    "Определите количество целых точек, в которых производная функции положительна."
)
_LOCAL_COUNT = re.compile(
    r"Определите количество целых точек, в (?:окрестностях )?которых функция f\(x\)\s*(возраста|убыва)ет\."
    r"(?: Примечание редакции: функцию называют \1ющей в точке, если она \1ет в окрестности этой точки\.)?"
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
_ANNOTATION = "monotonicity_sign_chart"
_PREVIOUS_ANNOTATION = "monotonicity_on_source"
_ANNOTATION_ALT = "Направление изменения функции и выделенные точки или промежуток"
_SKETCH = "function_comparison_sketch"
_SKETCH_ALT = "Примерный график функции с учётом сравнения её значений"


@dataclass(frozen=True)
class Question:
    domain: Interval | None
    derivative: bool
    continuous: bool
    operation: str
    sign: int = 1
    target: str = ""
    span: Interval | None = None
    comparisons: tuple = ()


def parse(text):
    text = text.replace("−", "-").replace("–", "-").replace("f '(", "f'(")
    implicit = _ENDPOINT_WITHOUT_DOMAIN.fullmatch(text)
    if implicit:
        return Question(
            None,
            True,
            False,
            "global",
            target=implicit["target"] or implicit["inverted_target"],
            span=interval(implicit["span"] or implicit["inverted_span"]),
        )
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
    local = _LOCAL_COUNT.fullmatch(request)
    if local and not derivative:
        return Question(
            domain,
            False,
            continuous,
            "count",
            1 if local[1] == "возраста" else -1,
            target="neighborhood",
        )
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
    if question.operation == "global" and entry.get("illustration_comparison"):
        result, _ = graph_value_order.extremum(question, bands)
        ((left, op, right),) = question.comparisons
        relation = rf"f({answer(left)}) {op} f({answer(right)})"
        html = (
            "<p>Построим примерный график функции по знакам производной "
            "и с учётом условия "
            + f'<span data-inline-latex="{escape(relation)}"></span>'
            + ".</p>"
        )
        return answer(result), html
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
        result, longest = longest_band(selected)
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
    if question.domain is None:
        raise UnsupportedCondition("the audited sign chart requires a stated domain")
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
        for asset in (
            [entry["solution_asset"]]
            if entry.get("solution_asset") and not entry.get("comparison_sketch")
            else []
        )
        + (
            []
            if entry.get("illustration_comparison")
            else entry.get("extra_solution_assets", [])
        )
    )


def _comparison_sketch(question, bands):
    points, winner = graph_value_order.sketch_points(question, bands)
    return graph_primitive_example.render_sketch(
        question.span, points, winner, comparisons=question.comparisons
    )


def diagram_specs(context, *, condition_asset_bytes=None):
    data, question, bands = _input(context)
    entry = data[5]
    specs = (
        (
            solution_diagrams.spec(
                entry["diagram_key"], graph_primitive_example.render(entry)
            ),
        )
        if entry.get("primitive_example")
        else ()
    )
    if entry.get("comparison_sketch"):
        specs += (solution_diagrams.spec(_SKETCH, _comparison_sketch(question, bands)),)
    if condition_asset_bytes is not None:
        condition_diagram.verify_download(data[6], condition_asset_bytes)
        graph = _audited_graph(data, question, bands)
        if graph is not None:
            from .monotonic_sum_render import render

            specs += (solution_diagrams.spec(_ANNOTATION, render(graph)),)
    return specs


def _audited_graph(data, question, bands):
    entry, source = data[5:]
    if not source.lstrip().startswith(
        (b"<svg", b"<?xml")
    ) or question.operation not in ("sum", "length", "global"):
        return None
    from .monotonic_sum_input import Graph, ordinate, stationary

    if not entry.get("curve_segments"):
        if question.operation != "sum" or not question.derivative:
            return None
        root = ET.fromstring(tangent_native.presentation(source))
        pieces = []
        for node, (x1, y1, x2, y2) in tangent_native.straight_segments(root):
            if node.get("stroke", "").lower() == "#143b8f" and x1 != x2:
                a, b = [x1, y1], [x2, y2]
                pieces.append([a, a, b, b])
        if not pieces:
            return None
        entry = {**entry, "curve_segments": pieces}

    ox, oy = entry["svg_origin"]
    unit = entry.get("x_unit", entry["svg_unit"])

    def project(value):
        return ox + float(value) * unit

    turning = stationary(entry) if not question.derivative else ()
    coordinates = {}
    for band in bands[:-1]:
        point = band[1]
        lo, hi = bounds(point)
        if "svg" in point:
            xy = tuple(point["svg"])
        elif not point.get("defined", True):
            xy = (project(lo), None)
        elif lo == hi:
            x = project(lo)
            xy = (x, oy if question.derivative else ordinate(entry, x))
        else:
            inside = [xy for xy in turning if project(lo) < xy[0] < project(hi)]
            if len(inside) != 1:
                raise UnsupportedCondition(
                    "one turning point must match the audited bounds"
                )
            xy = inside[0]
        coordinates[id(point)] = xy

    def position(point):
        if id(point) in coordinates:
            return coordinates[id(point)][0]
        return project(point["x"])

    selected = [band for band in bands if band[4] == question.sign]
    values, longest = (), None
    if question.operation == "length":
        _, band = longest_band(selected)
        longest = Interval(*[Fraction(point["x"]) for point in band[:2]], *band[2:4])
    elif question.operation == "sum":
        values = integers(selected, question.domain)
    else:
        result = (
            graph_value_order.extremum(question, bands)[0]
            if question.comparisons
            else global_point(question, bands)
        )
        values = (result,)
    return Graph(
        question,
        data[1],
        {},
        source,
        None,
        entry,
        tuple(coordinates.values()),
        tuple((position(a), position(b), sign) for a, b, _, _, sign in bands),
        tuple(values),
        longest=longest,
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
    concise = bool(entry.get("illustration_comparison"))
    removed = ()
    if concise:
        obsolete_ids = {
            asset["source_id"] for asset in entry.get("extra_solution_assets", [])
        }
        if entry.get("comparison_sketch"):
            obsolete_ids.add(entry["solution_asset"]["source_id"])
        obsolete_keys = {
            asset["asset_key"]
            for asset in content["assets"]
            if asset["asset_id"] in obsolete_ids
            and asset["asset_key"] not in condition["asset_keys"]
        }
        removed = tuple(
            {"transformation_target_id": "asset:" + key, "operation": "remove"}
            for key in sorted(obsolete_keys)
        )
        content = {
            **content,
            "assets": [
                asset
                for asset in content["assets"]
                if asset["asset_key"] not in obsolete_keys
            ],
        }
        entry = {**entry, "extra_solution_assets": []}
        if entry.get("comparison_sketch"):
            del entry["solution_asset"]
    graph = _audited_graph(data, question, bands)
    if graph is None:
        figure, keys, changes, extra = figures(
            content, entry, generated_solution_assets
        )
    else:
        from . import monotonic_sum_render as rendering

        old_keys = {_PREVIOUS_ANNOTATION}
        if not entry.get("comparison_sketch"):
            old_keys.add(_SKETCH)
        if previous_key := entry.get("previous_solution_asset_key"):
            old_keys.add(previous_key)
        if previous_id := entry.get("previous_solution_asset_id"):
            old_keys.update(
                asset["asset_key"]
                for asset in content["assets"]
                if asset["asset_id"] == previous_id
            )
        old_keys.intersection_update((solution or {}).get("asset_keys", ()))
        old_keys.difference_update(condition["asset_keys"])
        obsolete = tuple(
            {
                "transformation_target_id": "asset:" + key,
                "operation": "remove",
            }
            for key in sorted(old_keys)
        )
        if old_keys:
            content = {
                **content,
                "assets": [
                    asset
                    for asset in content["assets"]
                    if asset["asset_key"] not in old_keys
                ],
            }
        supporting_content = {
            **content,
            "assets": [
                asset
                for asset in content["assets"]
                if asset["asset_key"] != _ANNOTATION
            ],
        }
        if entry.get("comparison_sketch"):
            supporting, sketch_key, supporting_changes = graph_input.figure(
                supporting_content,
                {"diagram_key": _SKETCH, "solution_alt": _SKETCH_ALT},
                svg=_comparison_sketch(question, bands),
                generated=generated_solution_assets,
            )
            supporting_keys, extra = (sketch_key,), ""
            if supporting_changes:
                supporting_changes[0]["value"]["position"] = 1
            elif (solution or {}).get("asset_keys") == [_SKETCH, _ANNOTATION]:
                asset = next(
                    asset
                    for asset in supporting_content["assets"]
                    if asset["asset_key"] == _SKETCH
                )
                supporting_changes = [
                    {
                        "transformation_target_id": "asset:" + _SKETCH,
                        "operation": "add",
                        "value": {
                            "asset_key": _SKETCH,
                            "asset_id": asset["asset_id"],
                            "url": asset["url"],
                            "kind": "ordinary_image",
                            "alt": _SKETCH_ALT,
                            "parent_target_id": "section:solution:1",
                            "position": 1,
                            "html": supporting,
                        },
                    }
                ]
        else:
            supporting, supporting_keys, supporting_changes, extra = figures(
                supporting_content, entry, generated_solution_assets
            )
        svg = rendering.render(graph)
        figure, key, changes = graph_input.figure(
            {
                **content,
                "assets": [
                    asset
                    for asset in content["assets"]
                    if asset["asset_key"] not in supporting_keys
                ],
            },
            {"diagram_key": _ANNOTATION, "solution_alt": _ANNOTATION_ALT},
            svg=svg,
            generated=generated_solution_assets,
        )
        keys = (key,) + supporting_keys
        changes = obsolete + tuple(changes) + tuple(supporting_changes)
        if question.operation == "sum":
            endpoints = any(
                n in (question.domain.lower, question.domain.upper)
                for n in graph.integers
            )
            continuity = ""
            if endpoints or any(
                not point.get("defined", True) for point in entry["zero_points"]
            ):
                continuity = (
                    "<p>Учитываем непрерывность функции. Включённые в область определения "
                    "концы примыкающих промежутков монотонности тоже входят в эти промежутки.</p>"
                )
            if supporting:
                supporting = (
                    "<p>График одной из непрерывных функций с этой производной.</p>"
                    + supporting
                )
            html = (
                rendering.RULE
                + figure
                + continuity
                + rendering.proof(graph.integers)
                + supporting
                + rendering.NOTE
            )
        elif question.operation == "global" and question.comparisons:
            html = rendering.RULE + figure + html + supporting
            if concise:
                html += (
                    "<p>Функция принимает "
                    + question.target
                    + " значение при "
                    + f'<span data-inline-latex="x={result}"></span>'
                    + ".</p>"
                )
        elif question.operation == "global":
            html = rendering.endpoint_solution(figure, graph)
        else:
            html = rendering.longest_interval_solution(figure, graph)
        figure = ""
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
    if not concise and not html.endswith(NOTE):
        html += NOTE
    plan = solution_diagrams.repair(
        condition, ans, solution, result, figure + html, keys, removed + tuple(changes)
    )
    return graph_condition_layout.apply_layout(plan, context)
