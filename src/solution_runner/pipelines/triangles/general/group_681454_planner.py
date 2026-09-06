"""Strict bisector-angle repair for group 681454."""

from __future__ import annotations

from html import unescape
import re
from typing import Any

from ..right.planner import RepairPlan, RightTrianglePlanError

RULE = "general-triangle-681454-bisector-angle"


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    found = [s for s in content.get("sections", []) if isinstance(s, dict) and s.get("key") == key]
    if len(found) > 1:
        raise RightTrianglePlanError(f"multiple {key} sections")
    return found[0] if found else None


def _visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html))).replace("\u00ad", "").strip()


def _values(html: str) -> tuple[str, int, int, int]:
    text = _visible(html)
    has_bisector = "биссектриса AD" in text or "AD — биссектриса" in text
    if "В треугольнике ABC" not in text or not has_bisector:
        raise RightTrianglePlanError("condition is outside frozen group-681454 grammar")
    bad_match = re.search(r"угол BAD\s+равен\s*(\d+)°", text)
    if bad_match is None:
        raise RightTrianglePlanError("condition must state an integer BAD angle")
    bad = int(bad_match.group(1))

    acb_match = re.search(r"угол ACB\s+равен\s*(\d+)°", text)
    if "Найдите угол ABD" in text and acb_match is not None:
        acb = int(acb_match.group(1))
        result = 180 - 2 * bad - acb
        if not 0 < bad < 90 or not 0 < acb < 180 or not 0 < result < 180:
            raise RightTrianglePlanError("angles are inconsistent")
        return "triangle-sum", bad, acb, result

    c_match = re.search(r"угол C\s+равен\s*(\d+)°", text)
    if "Найдите величину угла ADB" in text and c_match is not None:
        c = int(c_match.group(1))
        result = bad + c
        if not 0 < bad < 90 or not 0 < c < 180 or not 0 < result < 180:
            raise RightTrianglePlanError("angles are inconsistent")
        return "exterior-angle", bad, c, result

    raise RightTrianglePlanError("condition is outside frozen group-681454 grammar")


def _asset(content: dict[str, Any], parent_asset_id: str) -> dict[str, Any] | None:
    images = [a for a in content.get("assets", []) if isinstance(a, dict) and a.get("kind") == "ordinary_image"]
    target = [a for a in images if a.get("asset_key") == "image_1"]
    if not target:
        return {"transformation_target_id": "asset:image_1", "operation": "add", "value": {"parent_target_id": "section:condition:1", "position": 0, "asset_key": "image_1", "asset_id": parent_asset_id, "url": f"/assets/{parent_asset_id}", "kind": "ordinary_image", "alt": ""}}
    if len(images) != 1 or len(target) != 1 or target[0].get("asset_id") != parent_asset_id:
        raise RightTrianglePlanError("foreign or ambiguous condition image")
    return None


def build_repair_plan(context: dict[str, Any], *, parent_condition_asset_id: str) -> RepairPlan:
    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    form, bad, known, result = _values(str(condition.get("html") or ""))
    if form == "triangle-sum":
        cab = 2 * bad
        html = (
            f'<section data-content-kind="solution" data-content-rule="{RULE}" data-solution-title="Решение">'
            '<p>Луч <span data-inline-latex="AD"></span> — биссектриса, поэтому он делит угол <span data-inline-latex="CAB"></span> пополам:</p>'
            f'<center><p><span data-inline-latex="\\angle CAB=2\\cdot\\angle BAD=2\\cdot {bad}^{{\\circ}}={cab}^{{\\circ}}"></span>.</p></center>'
            '<p>По теореме о сумме углов треугольника выразим искомый угол:</p>'
            '<center><p><span data-inline-latex="\\angle ABD=180^{\\circ}-\\angle CAB-\\angle ACB"></span>.</p></center>'
            '<p>Подставим найденный и данный углы:</p>'
            f'<center><p><span data-inline-latex="\\angle ABD=180^{{\\circ}}-{cab}^{{\\circ}}-{known}^{{\\circ}}={result}^{{\\circ}}"></span>.</p></center>'
            '</section>'
        )
    else:
        html = (
            f'<section data-content-kind="solution" data-content-rule="{RULE}" data-solution-title="Решение">'
            '<p>Луч <span data-inline-latex="AD"></span> — биссектриса, поэтому:</p>'
            f'<center><p><span data-inline-latex="\\angle CAD=\\angle BAD={bad}^{{\\circ}}"></span>.</p></center>'
            '<p>Угол <span data-inline-latex="ADB"></span> — внешний угол треугольника <span data-inline-latex="ADC"></span>, поэтому:</p>'
            '<center><p><span data-inline-latex="\\angle ADB=\\angle CAD+\\angle ACD"></span>.</p></center>'
            '<p>Подставим известные углы:</p>'
            f'<center><p><span data-inline-latex="\\angle ADB={bad}^{{\\circ}}+{known}^{{\\circ}}={result}^{{\\circ}}"></span>.</p></center>'
            '</section>'
        )
    transforms: list[dict[str, Any]] = []
    asset = _asset(content, parent_condition_asset_id)
    if asset is not None:
        transforms.append(asset)
    solution = _section(content, "solution")
    if solution is None or str(solution.get("html") or "") != html:
        transforms.append({"transformation_target_id": "section:solution", "operation": "rewrite" if solution else "add", "value": {"title": "Решение", "html": html, "asset_keys": []}})
    answer_html = f'<p><span data-effect="spaced">{result}</span></p>'
    answer = _section(content, "answer")
    if answer is None or str(answer.get("html") or "") != answer_html:
        transforms.append({"transformation_target_id": "section:answer:1", "operation": "rewrite", "value": {"title": "Ответ", "html": answer_html, "asset_keys": []}})
    return RepairPlan(answer=str(result), transformations=tuple(transforms))
