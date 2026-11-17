"""Two methods for f(x)=k/x+a; all existing image assets stay untouched."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from typing import Any
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from .diagrams import condition_entry, obsolete_solution_asset_keys, solution_images
from .hyperbola_format import answer_text, formula, number
from .hyperbola_format import latex as _latex
from .hyperbola_format import row as _row
from .hyperbola_solution import horizontal_solution, vertical_solution
from .hyperbola_solution import offset_description as _offset_description
from .hyperbola_solution import shift_description as _shift_description

latex = _latex
row = _row
offset_description = _offset_description
shift_description = _shift_description


@dataclass(frozen=True)
class RepairPlan:
    answer: str
    transformations: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...] = ()


# Visually audited immutable raster graphs. Pin the bytes, never a task's answer.
# Each tuple is k, a, x, y for f(x)=k/(x+a) and its marked point.
_RASTER_HORIZONTAL = {
    "7d4d5e053ab0c90b6bc03b8263b622890e3c21eae0e49365e38360c93f92b657": (-3, -1, 2, -3),
    "a286961697060596012cedd34d692318fc70022b7f390f3b05de5a334e4657f8": (-5, 2, 3, -1),
}


def _snap(value: float) -> Fraction:
    if abs(value - round(value)) > 0.06:
        raise ContentPlanError("graph coordinate is not an unambiguous grid node")
    return Fraction(round(value))


def graph_facts(
    data: bytes, *, horizontal_model: bool = False
) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ContentPlanError("invalid condition SVG") from exc
    if any(
        node.get("transform") and not node.tag.endswith("image") for node in root.iter()
    ):
        raise ContentPlanError("transformed SVG coordinates are unsupported")
    lines = list(root.iter("{http://www.w3.org/2000/svg}line"))

    def horizontal(node):
        return abs(float(node.get("y1", 0)) - float(node.get("y2", 0))) < 0.01

    def vertical(node):
        return abs(float(node.get("x1", 0)) - float(node.get("x2", 0))) < 0.01

    grid = [n for n in lines if n.get("stroke", "").upper() == "#ADAAAA"]
    xs = sorted({float(n.get("x1")) for n in grid if vertical(n)})
    ys = sorted({float(n.get("y1")) for n in grid if horizontal(n)})

    def spacing(values):
        if len(values) < 4:
            raise ContentPlanError("coordinate grid is unavailable")
        gaps = [b - a for a, b in pairwise(values) if b - a > 1]
        step = sorted(gaps)[len(gaps) // 2]
        if any(abs(gap / step - round(gap / step)) > 0.025 for gap in gaps):
            raise ContentPlanError("coordinate grid is not uniform")
        return step

    sx, sy = spacing(xs), spacing(ys)
    black = [
        n
        for n in lines
        if n.get("stroke", "").upper() in {"#000000", "#0D0F0F"}
        and not n.get("stroke-dasharray")
    ]
    hx = [
        n
        for n in black
        if horizontal(n) and abs(float(n.get("x2")) - float(n.get("x1"))) > 3 * sx
    ]
    vy = [
        n
        for n in black
        if vertical(n) and abs(float(n.get("y2")) - float(n.get("y1"))) > 3 * sy
    ]
    asymptotes = [
        n
        for n in lines
        if (vertical(n) if horizontal_model else horizontal(n))
        and n.get("stroke-dasharray")
    ]
    asymptote_positions = {
        round(float(n.get("x1" if horizontal_model else "y1")), 3) for n in asymptotes
    }
    points = [
        n
        for n in root.iter("{http://www.w3.org/2000/svg}circle")
        if n.get("fill", "").upper() == "#143B8F"
    ]
    if (
        len(hx) != 1
        or len(vy) != 1
        or len(asymptote_positions) != 1
        or len(points) != 1
    ):
        raise ContentPlanError(
            "need unique axes, horizontal asymptote and marked point"
        )
    ox, oy = float(vy[0].get("x1")), float(hx[0].get("y1"))
    a = (
        _snap((ox - float(asymptotes[0].get("x1"))) / sx)
        if horizontal_model
        else _snap((oy - float(asymptotes[0].get("y1"))) / sy)
    )
    x = _snap((float(points[0].get("cx")) - ox) / sx)
    y = _snap((oy - float(points[0].get("cy"))) / sy)
    k = (x + a) * y if horizontal_model else x * (y - a)
    if (x + a if horizontal_model else x) == 0 or k == 0:
        raise ContentPlanError("degenerate hyperbola")
    return k, a, x, y


def build_context_repair_plan(
    context: dict[str, Any],
    *,
    condition_asset_bytes: bytes | None,
    current_asset_content_type: str | None,
    mode: str,
    horizontal_model: bool = False,
) -> RepairPlan:
    content = _normalized_content(context)
    condition, solution, answer = (
        _section(content, key) for key in ("condition", "solution", "answer")
    )
    if condition is None or condition_asset_bytes is None:
        raise ContentPlanError("condition and its current graph are required")
    from .hyperbola_questions import shifted

    horizontal, raw_target = shifted(context, mode, horizontal_model)
    target = number(raw_target)
    warnings = ()
    if (
        horizontal
        and str(current_asset_content_type).split(";")[0].lower() == "image/svg+xml"
    ):
        k, a, x, y = graph_facts(condition_asset_bytes, horizontal_model=True)
    elif horizontal:
        facts = _RASTER_HORIZONTAL.get(
            hashlib.sha256(condition_asset_bytes).hexdigest()
        )
        if facts is None:
            raise ContentPlanError(
                "horizontal graph bytes have no audited numerical evidence"
            )
        k, a, x, y = map(Fraction, facts)
        warnings = (
            "Изображение условия не SVG; сохранено без изменений. Координаты проверены по исходному растру, закреплённому SHA-256.",
        )
    elif str(current_asset_content_type).split(";")[0].lower() == "image/svg+xml":
        k, a, x, y = graph_facts(condition_asset_bytes)
    else:
        entry = condition_entry(context)
        if entry["sha256"] != hashlib.sha256(condition_asset_bytes).hexdigest():
            raise ContentPlanError(
                "raster graph has no verified numerical evidence for these bytes"
            )
        warnings = (
            "Изображение условия не SVG; сохранено без изменений. Координаты проверены по исходному изображению, закреплённому SHA-256.",
        )
        k, a, x, y = map(Fraction, entry["facts"])
    if (mode == "value" and target == (-a if horizontal else 0)) or (
        mode == "argument" and target == (0 if horizontal else a)
    ):
        raise ContentPlanError("requested value is outside the function domain/range")
    result = (
        (k / (target + a) if mode == "value" else k / target - a)
        if horizontal
        else k / target + a
        if mode == "value"
        else k / (target - a)
    )
    entry = condition_entry(context)
    if (
        entry["kind"] != ("h" if horizontal else "v")
        or tuple(map(Fraction, entry["facts"])) != (k, a, x, y)
        or entry["sha256"] != hashlib.sha256(condition_asset_bytes).hexdigest()
    ):
        raise ContentPlanError(
            "registered solution graph differs from condition evidence"
        )
    if (
        horizontal
        and not entry.get("has_overlay")
        and str(current_asset_content_type).split(";")[0].lower() == "image/svg+xml"
    ):
        warnings += (
            "Исходный SVG содержит внешнюю растровую ссылку; сохранён без изменений, без красных отметок.",
        )
    points_image, offset_image, diagram_keys = solution_images(context)
    html = (
        horizontal_solution(
            k,
            a,
            x,
            y,
            target,
            result,
            points_image,
            offset_image,
            mode,
            tuple(map(Fraction, entry["second_point"]))
            if entry.get("second_point")
            else None,
            tuple(map(Fraction, entry["offset_point"]))
            if entry.get("offset_point")
            else None,
        )
        if horizontal
        else vertical_solution(
            k,
            a,
            x,
            y,
            target,
            result,
            mode,
            points_image,
            offset_image,
            tuple(map(Fraction, entry["second_point"]))
            if entry.get("second_point")
            else None,
            tuple(map(Fraction, entry["offset_point"]))
            if entry.get("offset_point")
            else None,
        )
    )
    retired_keys = obsolete_solution_asset_keys(context)
    if not entry.get("has_overlay"):
        html = html.replace(
            "Красный горизонтальный отрезок показывает отступ",
            "На исходном рисунке горизонтальный отступ равен",
        )
    superseded_keys = (
        (*retired_keys, "image_1") if entry.get("has_overlay") else retired_keys
    )
    # Preserve unrelated illustrations; replace earlier uses of the unannotated condition graph.
    images = [
        tag
        for tag in re.findall(
            r"<img\b[^>]*>",
            str(solution.get("html") or "") if solution else "",
            re.IGNORECASE,
        )
        if not any(key in tag for key in (*diagram_keys, *superseded_keys))
    ]
    if images:
        html += "".join(images)
    first, alternative = html.split("<p><b>Альтернативное решение</b></p>")
    html = (
        f'<section data-content-kind="solution" data-solution-title="Решение">{first}</section>'
        f'<section data-content-kind="solution" data-solution-title="Альтернативное решение">{alternative}</section>'
    )
    changes = []
    # Only remove soft hyphens from prose; never rewrite image markup or assets.
    condition_html = str(condition.get("html") or "")
    cleaned = condition_html.replace("\u00ad", "")
    if horizontal_model:
        cleaned = cleaned.replace(r"f(x)=\frac{k}{x}+a", r"f(x)=\frac{k}{x+a}")
    if horizontal:
        cleaned = re.sub(r"\$([^$]+)\$", lambda m: formula(m[1].strip()), cleaned)
    if cleaned != condition_html:
        changes.append(
            _section_transformation(
                condition,
                "condition",
                "Условие",
                cleaned,
                asset_keys=tuple(condition.get("asset_keys") or ()),
            )
        )
    solution_keys = (
        tuple(
            dict.fromkeys(
                tuple(
                    key
                    for key in (solution.get("asset_keys") or ())
                    if key not in retired_keys
                )
                + diagram_keys
            )
        )
        if solution
        else diagram_keys
    )

    def comparable(value: str) -> str:
        # Transformation-context annotations are transport metadata, not prose.
        return re.sub(r'\s+data-transformation-target-id="[^"]*"', "", value)

    if (
        solution is None
        or comparable(str(solution.get("html") or "")) != comparable(html)
        or tuple(solution.get("asset_keys") or ()) != solution_keys
    ):
        changes.append(
            _section_transformation(
                solution, "solution", "Решение", html, asset_keys=solution_keys
            )
        )
    result_text = answer_text(result).replace(".", ",")
    existing = BeautifulSoup(
        str(answer.get("html") or "") if answer else "", "html.parser"
    ).get_text("", strip=True)
    if existing.replace("−", "-") != result_text:
        if existing:
            warnings += (
                f"Исходный ответ {existing} отличается от вычисленного {result_text}; ответ исправляется по графику.",
            )
        changes.append(
            _section_transformation(
                answer,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{result_text}</span></p>',
            )
        )
    return RepairPlan(result_text, tuple(changes), warnings)
