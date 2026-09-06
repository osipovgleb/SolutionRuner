"""Bounded included-angle area rule for general-triangle group 561168."""

from __future__ import annotations

from fractions import Fraction
from html import unescape
import re
from typing import Any

from ..right.planner import RepairPlan, RightTrianglePlanError

RULE = "general-triangle-561168-obtuse-included-angle-area"


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    values = [v for v in content.get("sections", []) if isinstance(v, dict) and v.get("key") == key]
    if len(values) > 1: raise RightTrianglePlanError(f"multiple {key} sections")
    return values[0] if values else None


def _plain(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html))).replace("\u00ad", "").strip()


def _number(raw: str) -> Fraction:
    value = raw.replace(",", ".")
    if not re.fullmatch(r"(?:0|[1-9]\d*)(?:\.\d+)?", value): raise RightTrianglePlanError("unsupported decimal")
    result = Fraction(value)
    if result <= 0: raise RightTrianglePlanError("values must be positive")
    return result


def _display(value: Fraction) -> str:
    if value.denominator == 1: return str(value.numerator)
    scale=1
    while scale < 1_000_000 and scale % value.denominator: scale *= 10
    if scale % value.denominator == 0:
        whole, remainder = divmod(value.numerator, value.denominator)
        return (f"{whole}.{str(remainder*(scale//value.denominator)).zfill(len(str(scale))-1)}").rstrip("0").rstrip(".").replace(".", "{,}")
    return rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def _asset(content: dict[str, Any], parent_asset_id: str) -> dict[str, Any] | None:
    images=[v for v in content.get("assets",[]) if isinstance(v,dict) and v.get("kind")=="ordinary_image"]
    target=[v for v in images if v.get("asset_key")=="image_1"]
    if not target:
        return {"transformation_target_id":"asset:image_1","operation":"add","value":{"parent_target_id":"section:condition:1","position":0,"asset_key":"image_1","asset_id":parent_asset_id,"url":f"/assets/{parent_asset_id}","kind":"ordinary_image","alt":""}}
    if len(images)!=1 or len(target)!=1 or target[0].get("asset_id")!=parent_asset_id: raise RightTrianglePlanError("foreign or ambiguous condition image")
    return None


def _values(html: str) -> tuple[Fraction, Fraction, str, str, int]:
    text=_plain(html)
    required=("В треугольнике ABC", "угол B", "тупой", "AB", "BC", "площадь", "Найдите величину угла")
    if any(term not in text for term in required): raise RightTrianglePlanError("condition is outside frozen group-561168 grammar")
    ab=re.search(r"\bAB\s*=\s*([0-9]+(?:[,.][0-9]+)?)",text);bc=re.search(r"\bBC\s*=\s*([0-9]+(?:[,.][0-9]+)?)",text)
    if ab is None or bc is None: raise RightTrianglePlanError("condition must declare AB and BC")
    latex=re.findall(r'data-inline-latex="([^"]+)"',unescape(html))
    radical=next((v for v in latex if re.fullmatch(r"([1-9]\d*)\\sqrt\{3\}",v.replace(" ",""))),None)
    if radical is not None:
        coefficient=Fraction(int(re.fullmatch(r"([1-9]\d*)\\sqrt\{3\}",radical.replace(" ","")).group(1)))
        return _number(ab.group(1)),_number(bc.group(1)),rf"{coefficient}\sqrt{{3}}",r"\frac{\sqrt{3}}{2}",120
    area=re.search(r"площадь треугольника равна\s*([0-9]+(?:[,.][0-9]+)?)",text)
    if area is None: raise RightTrianglePlanError("area must be an audited decimal or k sqrt(3)")
    a,b,s=_number(ab.group(1)),_number(bc.group(1)),_number(area.group(1))
    sine=2*s/(a*b)
    if sine != Fraction(1,2): raise RightTrianglePlanError("only the audited sine values are supported")
    return a,b,_display(s),r"\frac{1}{2}",150


def build_repair_plan(context: dict[str, Any], *, parent_condition_asset_id: str) -> RepairPlan:
    content=context.get("normalized_content")
    if not isinstance(content,dict) or content.get("format")!="teacherhelper-normalized" or content.get("schema_version")!=3: raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition=_section(content,"condition")
    if condition is None: raise RightTrianglePlanError("condition section is required")
    ab,bc,area,sine,angle=_values(str(condition.get("html") or ""))
    formula=rf"S=\frac{{1}}{{2}}\cdot AB\cdot BC\cdot\sin \angle B"
    solve=rf"\sin \angle B=\frac{{2S}}{{AB\cdot BC}}"
    substitute=rf"\sin \angle B=\frac{{2\cdot {area}}}{{{_display(ab)}\cdot {_display(bc)}}}={sine}"
    html=(f'<section data-content-kind="solution" data-content-rule="{RULE}" data-solution-title="Решение">'
          '<p>По формуле площади треугольника через две стороны и угол между ними:</p>'
          f'<center><p><span data-inline-latex="{formula}"></span>.</p></center>'
          '<p>Выразим синус искомого угла:</p>'
          f'<center><p><span data-inline-latex="{solve}"></span>.</p></center>'
          '<p>Подставим данные условия:</p>'
          f'<center><p><span data-inline-latex="{substitute}"></span>.</p></center>'
          f'<p>Это значение синуса соответствует острому углу; по условию угол <span data-inline-latex="B"></span> тупой, поэтому <span data-inline-latex="\\angle B={angle}^{{\\circ}}"></span>.</p></section>')
    transforms=[];asset=_asset(content,parent_condition_asset_id)
    if asset is not None: transforms.append(asset)
    solution=_section(content,"solution"); desired={"transformation_target_id":"section:solution","operation":"rewrite" if solution is not None else "add","value":{"title":"Решение","html":html,"asset_keys":[]}}
    if solution is None or str(solution.get("html") or "")!=html: transforms.append(desired)
    answer=str(angle);current=_section(content,"answer");answer_html=f'<p><span data-effect="spaced">{answer}</span></p>'
    if current is None or str(current.get("html") or "")!=answer_html: transforms.append({"transformation_target_id":"section:answer:1","operation":"rewrite","value":{"title":"Ответ","html":answer_html,"asset_keys":[]}})
    return RepairPlan(answer=answer,transformations=tuple(transforms))
