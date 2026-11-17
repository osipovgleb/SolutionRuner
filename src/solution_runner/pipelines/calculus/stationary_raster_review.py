"""Build review-only previews for uncertain stationary-point graphs."""

import hashlib
from copy import deepcopy
from html import escape
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ..equations.linear_system_intervals import interval_latex
from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition


def review_preview(context, *, condition_asset_bytes, error):
    """Show an uncertain candidate without exposing any apply transformations."""

    from .stationary_raster_runner import _model, _render

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
        specs = [solution_diagrams.spec(asset["asset_key"], solution_svg)]

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

        condition_image = image(asset["asset_key"], solution_svg)

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
        note += (
            "<p>Сохранённый ответ: <strong>"
            + escape(stored_text or "отсутствует")
            + "</strong>. Отмечено на графике: <strong>"
            + calculated
            + "</strong>.</p>"
        )
        note += "<p>Точки пронумерованы для сверки с исходным рисунком.</p>"
    except (ValueError, TypeError, ET.ParseError):
        note += "<p>Преобразованный рисунок не построен. Требуется доработка распознавания; исходный рисунок оставлен для сравнения.</p>"

    content["sections"] = [
        s for s in content["sections"] if s["key"] not in ("answer", "solution")
    ]
    content["sections"].append({"key": "solution", "html": note, "asset_keys": []})
    return {
        "content": content,
        "generated_diagrams": specs,
        "message": reason,
        "calculated_answer": calculated,
        "stored_answer": stored_text,
    }
