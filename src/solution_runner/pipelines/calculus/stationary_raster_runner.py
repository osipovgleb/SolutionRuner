"""Convert horizontal-tangent raster graphs with the proven primitive fitter."""

import hashlib
import re
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
from html import escape
from itertools import pairwise
from statistics import median
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ..equations.linear_system_intervals import interval_latex
from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition, line, normalize, rewrite
from ..triangles.right.basic_parent import _targeted
from . import (
    graph_input,
    graph_stationary,
    horizontal_curves,
    primitive_svg,
    raster_primitive,
)

KEY = "horizontal_tangent_points"
ALT = "Точки с горизонтальной касательной"


def _read(context):
    content = context["normalized_content"]
    conditions = [s for s in content["sections"] if s["key"] == "condition"]
    if len(conditions) != 1 or len(conditions[0].get("asset_keys", [])) != 1:
        raise UnsupportedCondition("one complete primitive condition image is required")
    condition = conditions[0]
    key = condition["asset_keys"][0]
    assets = [a for a in content["assets"] if a.get("asset_key") == key]
    if len(assets) != 1 or assets[0].get("kind") != "ordinary_image":
        raise UnsupportedCondition("the primitive image metadata is ambiguous")
    asset = assets[0]
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-id") != asset["asset_id"]
        or images[0].get("data-asset-key") != key
    ):
        raise UnsupportedCondition("the visible primitive does not match its asset")
    images[0].decompose()
    for node in soup.find_all("var"):
        if (
            set(node.attrs) != {"data-math-identifier"}
            or len(node.get_text()) != 1
            or node["data-math-identifier"] != node.get_text()
        ):
            raise UnsupportedCondition("unsupported mathematical identifier markup")
        node.unwrap()
    clean = deepcopy(context)
    content_copy = clean["normalized_content"]
    content_copy["assets"] = []
    cond = next(s for s in content_copy["sections"] if s["key"] == "condition")
    cond["asset_keys"] = []
    cond["html"] = str(soup)
    text = normalize(graph_input._read_text(clean)[4])
    text = text.replace("график дифференцируемой функции", "график функции")
    text = re.sub(r"на интервале\((-?\d+),\s*(-?\d+)\)", r"на интервале(\1;\2)", text)
    question = graph_stationary.parse(text)
    if question.kind != "horizontal":
        raise UnsupportedCondition("a complete horizontal-tangent question is required")
    return question, condition, asset


def required_assets(context):
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assets = [
        a
        for a in context["normalized_content"]["assets"]
        if a["asset_key"] in condition.get("asset_keys", [])
    ]
    if len(assets) == 1 and assets[0]["asset_id"] in graph_input.EVIDENCE:
        return graph_stationary.required_assets(context)
    return ()


@lru_cache(maxsize=32)
def _recover(data, question):
    return horizontal_curves.recover(data, question)


def _model(context, data, *, review=False):
    question, condition, asset = _read(context)
    if data.startswith(raster_primitive.PNG):
        if any(
            a["asset_key"] not in (asset["asset_key"], KEY)
            for a in context["normalized_content"]["assets"]
        ):
            raise UnsupportedCondition(
                "unrelated primitive assets need separate review"
            )
        model = deepcopy(_recover(data, question))
    else:
        if b"y = f(x)" not in data:
            raise UnsupportedCondition(
                "the prepared horizontal-tangent graph must be labelled y=f(x)"
            )
        model = raster_primitive.embedded(
            data.replace(b"y = f(x)", b"y = F(x)"), question
        )
    if model is None:
        raise UnsupportedCondition("the primitive SVG has no verified model")
    selected = raster_primitive.select(model, question)
    if not review and not question.include_coincident:
        for point in selected:
            # Coordinates refer to the recovered grid. A near coincidence must
            # be reviewed rather than decided from subpixel raster noise.
            if abs(point["svg"][1] - float(question.horizontal)) < 0.25:
                raise UnsupportedCondition(
                    "the raster does not resolve coincidence with the horizontal line"
                )
    if not review:
        _check_count(context, len(selected))
    return question, condition, asset, model, selected


def _check_count(context, count):
    stored = next(
        (s for s in context["normalized_content"]["sections"] if s["key"] == "answer"),
        None,
    )
    stored_text = (
        BeautifulSoup((stored or {}).get("html", ""), "html.parser").get_text().strip()
    )
    if (
        re.fullmatch(r"\d+", stored_text)
        and str(int(stored_text)) == stored_text
        and int(stored_text) != count
    ):
        raise UnsupportedCondition(
            "the recovered tangent count differs from the stored answer; visual review is required"
        )


def _render(model, **kwargs):
    return raster_primitive.render(model, **kwargs).replace("y = F(x)", "y = f(x)")


def diagram_specs(context, *, condition_asset_bytes=None):
    data = condition_asset_bytes
    if not isinstance(data, bytes):
        return ()
    if (
        not data.startswith(raster_primitive.PNG)
        and raster_primitive.META.encode() not in data
    ):
        try:
            return graph_stationary.diagram_specs(context)
        except UnsupportedCondition:
            question, entry, points = _native_points(context, data)
            return (
                solution_diagrams.spec(
                    KEY,
                    graph_stationary.render_svg(entry, data, question.interval, points),
                ),
            )
    _question, _condition, asset, model, selected = _model(context, data)
    first = (
        (solution_diagrams.spec(asset["asset_key"], _render(model)),)
        if data.startswith(raster_primitive.PNG)
        else ()
    )
    return (
        *first,
        solution_diagrams.spec(KEY, _render(model, selected_points=selected)),
    )


def proof(question, points):
    def inline(formula):
        return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'

    html = "<p>Прямая " + inline("y=" + str(question.horizontal))
    html += " параллельна оси абсцисс. В точках, где касательная к графику горизонтальна, производная равна нулю:</p>"
    html += line("f'(x)=0")
    html += (
        "<p>Отметим такие точки на графике. Их количество — "
        + str(len(points))
        + ".</p>"
    )
    return html


def _native_points(context, data):
    question, _, _ = _read(context)
    entry, points = primitive_svg.read(data, replace(question, kind="count"))
    if not question.include_coincident:
        lines = [n for n in ET.fromstring(data).iter() if n.tag.endswith("line")]
        axes = [
            n
            for n in lines
            if n.get("stroke", "").lower() in ("#000000", "#000", "black")
            and abs(float(n.get("y1", 0)) - float(n.get("y2", 0))) < 0.01
            and abs(float(n.get("x1", 0)) - float(n.get("x2", 0)))
            > entry["svg_unit"] * 3
        ]
        ys = sorted(
            {
                float(n.get("y1", 0))
                for n in lines
                if n.get("stroke", "").lower() == "#adaaaa"
                and abs(float(n.get("y1", 0)) - float(n.get("y2", 0))) < 0.5
            }
        )
        if len(axes) != 1 or len(ys) < 3:
            raise UnsupportedCondition(
                "native horizontal coincidence needs a verified coordinate grid"
            )
        unit = median(b - a for a, b in pairwise(ys) if b - a > 1)
        if abs(unit / entry["svg_unit"] - 1) > 0.05:
            raise UnsupportedCondition("native coordinate grid units disagree")
        origin = float(axes[0].get("y1"))
        for point in points:
            ordinate = (origin - point["svg"][1]) / unit
            point["y_bounds"] = [str(ordinate - 0.08), str(ordinate + 0.08)]
        points = graph_stationary.parallel_points(points, question.horizontal, False)
    _check_count(context, len(points))
    return question, entry, points


def _native_plan(context, data, generated):
    try:
        graph_stationary._input(context)
    except UnsupportedCondition:
        question, entry, points = _native_points(context, data)
        content = context["normalized_content"]
        condition = next(s for s in content["sections"] if s["key"] == "condition")
        solution = next(
            (s for s in content["sections"] if s["key"] == "solution"), None
        )
        svg = graph_stationary.render_svg(entry, data, question.interval, points)
        figure, key, changes = solution_diagrams.image(
            content, KEY, ALT, svg=svg, generated=generated
        )
        obsolete = [
            a
            for a in content["assets"]
            if a["asset_key"] in (solution or {}).get("asset_keys", [])
            and a["asset_key"] != key
        ]
        removed = tuple(
            {
                "transformation_target_id": "asset:" + a["asset_key"],
                "operation": "remove",
            }
            for a in obsolete
        )
        return solution_diagrams.repair(
            condition,
            _targeted(
                next((s for s in content["sections"] if s["key"] == "answer"), None)
            ),
            _targeted(solution),
            str(len(points)),
            figure + proof(question, points),
            (key,),
            removed + tuple(changes),
        )

    return graph_stationary.build_context_repair_plan(
        context, condition_asset_bytes=data, generated_solution_assets=generated
    )


def _build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data = condition_asset_bytes
    if not isinstance(data, bytes):
        raise UnsupportedCondition("current primitive diagram bytes are required")
    if (
        not data.startswith(raster_primitive.PNG)
        and raster_primitive.META.encode() not in data
    ):
        return _native_plan(context, data, generated_solution_assets)
    question, condition, asset, model, selected = _model(context, data)
    content = context["normalized_content"]
    svg = _render(model, selected_points=selected)
    figure, key, changes = solution_diagrams.image(
        content, KEY, ALT, svg=svg, generated=generated_solution_assets
    )
    result = solution_diagrams.repair(
        condition,
        _targeted(next((s for s in content["sections"] if s["key"] == "answer"), None)),
        _targeted(
            next((s for s in content["sections"] if s["key"] == "solution"), None)
        ),
        str(len(selected)),
        figure + proof(question, selected),
        (key,),
        changes,
    )
    if not data.startswith(raster_primitive.PNG):
        return result
    condition_svg = _render(model)
    digest = hashlib.sha256(condition_svg.encode()).hexdigest()
    generated = [
        a
        for a in generated_solution_assets
        if a.get("asset_key") == asset["asset_key"] and a.get("sha256") == digest
    ]
    if len(generated) != 1:
        raise UnsupportedCondition(
            "the prepared SVG does not match the current primitive PNG"
        )
    new = generated[0]
    soup = BeautifulSoup(condition["html"], "html.parser")
    image = soup.find("img")
    image["data-asset-id"] = new["source_asset_id"]
    image["src"] = new["url"]
    image["alt"] = "График функции"
    image["data-transformation-target-id"] = "asset:" + asset["asset_key"]
    asset_change = {
        "transformation_target_id": "asset:" + asset["asset_key"],
        "operation": "rewrite",
        "value": {
            "asset_key": asset["asset_key"],
            "asset_id": new["source_asset_id"],
            "url": new["url"],
            "kind": "ordinary_image",
            "alt": image["alt"],
            "parent_target_id": _targeted(condition)["transformation_target_id"],
            "position": 0,
            "html": str(image),
        },
    }
    condition_change = rewrite(
        _targeted(condition), "condition", condition.get("title", "Условие"), str(soup)
    )
    condition_change["value"]["asset_keys"] = list(condition["asset_keys"])
    return replace(
        result,
        transformations=(asset_change, condition_change, *result.transformations),
    )


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    """Compare the exact DOM content after server materialization, not escaping."""
    plan = _build_context_repair_plan(
        context,
        condition_asset_bytes=condition_asset_bytes,
        generated_solution_assets=generated_solution_assets,
    )
    content = context["normalized_content"]
    current = next((s for s in content["sections"] if s["key"] == "solution"), None)

    def canonical(raw, *, reused_alts=False):
        soup = BeautifulSoup(raw or "", "html.parser")
        for tag in soup.find_all(True):
            tag.attrs.pop("data-transformation-target-id", None)
            if reused_alts and tag.name == "img":
                asset = next(
                    (
                        a
                        for a in content.get("assets", [])
                        if a.get("asset_id") == tag.get("data-asset-id")
                        and a.get("asset_key") == tag.get("data-asset-key")
                    ),
                    None,
                )
                if asset is not None:
                    tag["alt"] = asset.get("alt", "")
        return str(soup)

    expected = canonical(plan.solution_html, reused_alts=True)
    matches = current is not None and canonical(current.get("html", "")) == expected
    changes = []
    for original in plan.transformations:
        change = deepcopy(original)
        if change["transformation_target_id"].startswith("section:solution"):
            if matches:
                continue
            change["value"]["html"] = expected
        changes.append(change)
    question, condition, _asset = _read(context)
    condition_changes = [
        t
        for t in changes
        if t["transformation_target_id"].startswith("section:condition")
    ]
    image_html = (
        condition_changes[-1]["value"]["html"]
        if condition_changes
        else condition["html"]
    )
    image = BeautifulSoup(image_html, "html.parser").find("img")

    def inline(formula):
        return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'

    condition_html = (
        "<p>На рисунке изображён график функции "
        + inline("y=f(x)")
        + ", определённой на интервале "
        + inline(interval_latex(question.domain))
        + ".</p>"
        + "<p>Найдите количество точек, в которых касательная к графику функции параллельна прямой "
        + inline("y=" + str(question.horizontal))
        + (" или совпадает с ней" if question.include_coincident else "")
        + ".</p>"
        + "<center>"
        + str(image)
        + "</center>"
    )
    condition_html = canonical(condition_html, reused_alts=True)
    changes = [
        t
        for t in changes
        if not t["transformation_target_id"].startswith("section:condition")
    ]
    if canonical(condition["html"]) != condition_html:
        change = rewrite(
            _targeted(condition),
            "condition",
            condition.get("title", "Условие"),
            condition_html,
        )
        change["value"]["asset_keys"] = list(condition["asset_keys"])
        changes.append(change)
    return replace(plan, solution_html=expected, transformations=tuple(changes))


def review_preview(context, *, condition_asset_bytes, error):
    """Show an uncertain candidate without exposing any apply transformations."""
    content = deepcopy(context["normalized_content"])
    stored = next((s for s in content["sections"] if s["key"] == "answer"), {})
    stored_text = (
        BeautifulSoup(stored.get("html", ""), "html.parser").get_text().strip()
    )
    reason = error
    if "stored answer" in error:
        reason = "Подсчёт по рисунку не совпадает с сохранённым ответом."
    elif "coincidence" in error:
        reason = "Нужно проверить, совпадает ли касательная с заданной прямой."
    elif "unsupported complete" in error:
        reason = "В этой карточке условие другого типа; этот обработчик его не решает."
    note = (
        "<p><strong>Только для сверки. Применение заблокировано.</strong></p><p>"
        + escape(reason)
        + "</p>"
    )
    if "разрыв" in error:
        reason = "Не удалось надёжно отделить кривую от координатной сетки."
        note = (
            "<p><strong>Только для сверки. Применение заблокировано.</strong></p><p>"
            + reason
            + "</p>"
        )
    elif "curvature optimization" in error:
        reason = "Не удалось согласовать гладкость кривой без изменения её изгибов."
        note = (
            "<p><strong>Только для сверки. Применение заблокировано.</strong></p><p>"
            + reason
            + "</p>"
        )
    specs = []
    calculated = None
    try:
        if not isinstance(condition_asset_bytes, bytes):
            raise UnsupportedCondition("the current graph bytes are unavailable")
        question, _condition, asset, model, selected = _model(
            context, condition_asset_bytes, review=True
        )
        calculated = str(len(selected))
        condition_svg = _render(model)
        root = ET.fromstring(_render(model, selected_points=selected))
        ns = "{http://www.w3.org/2000/svg}"
        group = root.find(ns + 'g[@data-runner-diagram="stationary_points"]')
        # The whole open domain is being counted; circles already show its ends.
        for polyline in list(group.findall(ns + "polyline")):
            group.remove(polyline)
        for index, circle in enumerate(group.findall(ns + "circle"), 1):
            ET.SubElement(
                group,
                ns + "text",
                {
                    "x": str(float(circle.get("cx")) + 4),
                    "y": str(float(circle.get("cy")) - 5),
                    "fill": "#007EA5",
                    "font-size": "11",
                    "font-family": "Arial",
                },
            ).text = str(index)
        solution_svg = ET.tostring(root, encoding="unicode")
        specs = [
            solution_diagrams.spec(asset["asset_key"], condition_svg),
            solution_diagrams.spec(KEY, solution_svg),
        ]

        def image(key, svg):
            digest = hashlib.sha256(svg.encode()).hexdigest()
            aid = "preview-" + digest[:16]
            content["assets"] = [a for a in content["assets"] if a["asset_key"] != key]
            content["assets"].append(
                {
                    "asset_key": key,
                    "asset_id": aid,
                    "kind": "ordinary_image",
                    "url": "/assets/" + aid,
                }
            )
            return (
                '<center><img width="480" data-asset-key="'
                + key
                + '" data-asset-id="'
                + aid
                + '" src="/assets/'
                + aid
                + '"/></center>'
            )

        condition_image = image(asset["asset_key"], condition_svg)

        def inline(formula):
            return (
                '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'
            )

        target = next(s for s in content["sections"] if s["key"] == "condition")
        target["html"] = (
            "<p>На рисунке изображён график функции "
            + inline("y=f(x)")
            + ", определённой на интервале "
            + inline(interval_latex(question.domain))
            + ".</p>"
            + "<p>Найдите количество точек, в которых касательная к графику функции параллельна прямой "
            + inline("y=" + str(question.horizontal))
            + (" или совпадает с ней" if question.include_coincident else "")
            + ".</p>"
            + condition_image
        )
        figure = image(KEY, solution_svg)
        note += (
            "<p>Сохранённый ответ: <strong>"
            + escape(stored_text or "отсутствует")
            + "</strong>. Отмечено на графике: <strong>"
            + calculated
            + "</strong>.</p>"
        )
        note += figure + "<p>Точки пронумерованы для сверки с исходным рисунком.</p>"
    except (ValueError, TypeError, ET.ParseError):
        note += "<p>Преобразованный рисунок не построен. Требуется доработка распознавания; исходный рисунок оставлен для сравнения.</p>"

    content["sections"] = [
        s for s in content["sections"] if s["key"] not in ("answer", "solution")
    ]
    content["sections"].append(
        {"key": "solution", "html": note, "asset_keys": [KEY] if specs else []}
    )
    return {
        "content": content,
        "generated_diagrams": specs,
        "message": reason,
        "calculated_answer": calculated,
        "stored_answer": stored_text,
    }
