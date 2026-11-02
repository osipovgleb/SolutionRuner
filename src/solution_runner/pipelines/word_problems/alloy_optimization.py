"""Balance two metals, then maximize their mass by the parent's derivative method."""

import hashlib
import re
from copy import deepcopy
from dataclasses import dataclass
from importlib.resources import files

import sympy as sp

from ..calculus.common import answer
from ..probability import solution_diagrams as diagrams
from ..probability.common import NUMBER, UnsupportedCondition, line
from ..triangles.isosceles.planner import _normalized_content, _section
from . import math_common

_PATTERN = re.compile(
    rf"В двух областях есть по (?P<workers>[1-9]\d{{0,4}}) рабочих, каждый из которых готов трудиться по (?P<hours>[1-9]\d{{0,2}}) часов в сутки на добыче алюминия или никеля\. "
    rf"В первой области один рабочий за час добывает (?P<aluminium>{NUMBER}) кг алюминия или (?P<nickel>{NUMBER}) кг никеля\. "
    r"Во второй области для добычи x кг алюминия в день требуется x\^\{2\} человеко-часов труда, а для добычи y кг никеля в день требуется y\^\{2\} человеко-часов труда\. "
    r"Обе области поставляют добытый металл на завод, где для нужд промышленности производится сплав алюминия и никеля, в котором на 1 кг алюминия приходится 1 кг никеля\. "
    r"При этом области договариваются между собой вести добычу металлов так, чтобы завод мог произвести наибольшее количество сплава\. "
    r"Сколько килограммов сплава при таких условиях ежедневно сможет произвести завод\?"
)
# shortcut: only audited critical-point charts; extend when a new labor budget appears.
_CHARTS = {
    sp.Integer(10): (
        "e7d12b7b-6935-4703-be95-8a189ffb8472",
        "295fb715bca25b0f807a4d8d9d8c95c5660b9b9120057d1c2e18957d68075ce7",
    ),
    sp.Integer(20): (
        "60cb8a3c-1aac-4f83-ac9e-b466fb190d90",
        "dd6d14f2a744aedd238962abf29b134f44d081526f489fd138c21a230dc2dc6a",
    ),
}
_ALT = "Знаки производной массы сплава и точка максимума"


@dataclass(frozen=True)
class Analysis:
    workers: int
    hours: int
    rate: sp.Rational
    labor: int
    first: sp.Rational
    critical: sp.Rational
    result: sp.Rational


def calculate(context):
    content = _normalized_content(context)
    if any(
        s.get("asset_keys") for s in content["sections"] if s.get("key") != "solution"
    ):
        raise UnsupportedCondition("alloy figures may appear only in the solution")
    prepared = deepcopy(context)
    prepared["normalized_content"]["assets"] = []
    solution = _section(prepared["normalized_content"], "solution")
    if solution:
        solution["asset_keys"] = []
    text = math_common.read(prepared)[3]
    text = re.sub(r"\bу\b", "y", text).replace("‐", "-").replace("‑", "-")
    match = _PATTERN.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("unsupported complete alloy optimization condition")
    workers, hours = int(match["workers"]), int(match["hours"])
    rate, other = (
        sp.Rational(match[k].replace("{,}", ".").replace(",", "."))
        for k in ("aluminium", "nickel")
    )
    if not 0 < rate <= 1000 or rate != other:
        raise UnsupportedCondition(
            "equal positive bounded first-region rates are required"
        )
    labor = workers * hours
    critical = sp.sqrt(sp.Rational(labor, 2))
    if critical not in _CHARTS:
        raise UnsupportedCondition("the critical point requires an audited sign chart")
    a = Analysis(
        workers, hours, rate, labor, rate * labor, critical, rate * labor + 2 * critical
    )
    source, digest = _CHARTS[critical]
    blob = files(__package__).joinpath("assets/" + source + ".svg").read_bytes()
    if hashlib.sha256(blob).hexdigest() != digest:
        raise UnsupportedCondition("the audited alloy sign chart has changed")
    assets = content.get("assets", [])
    if (
        not isinstance(assets, list)
        or len(assets) > 1
        or any(
            not isinstance(asset, dict)
            or asset.get("asset_id") != source
            or not isinstance(asset.get("asset_key"), str)
            or not asset["asset_key"]
            or asset.get("kind", "ordinary_image") != "ordinary_image"
            or asset.get("url", "/assets/" + source) != "/assets/" + source
            for asset in assets
        )
    ):
        raise UnsupportedCondition(
            "the source sign chart does not match the computed maximum"
        )
    return content, a


def required_assets(context):
    _, a = calculate(context)
    return (
        {
            "source_asset_id": _CHARTS[a.critical][0],
            "section_id": "solution:1",
            "alt_text": _ALT,
        },
    )


def proof(a, diagram):
    f = math_common.number
    total, first, critical = f(a.labor), f(a.first), f(a.critical)
    upper = sp.latex(sp.sqrt(a.labor))
    html = "<p>В каждой области найдём суточный запас труда в человеко-часах:</p>"
    html += line(rf"T={a.workers}\cdot {a.hours}={total}")
    html += "<p>В первой области при полной загрузке будет добыто следующее количество металлов:</p>"
    html += line(rf"F={f(a.rate)}\cdot {total}={first}")
    html += f"<p>Пусть в первой области добыто y кг алюминия, тогда никеля будет ({answer(a.first)} − y) кг. Во второй области пусть добыто x кг алюминия; оставшегося труда хватит на добычу никеля. Для сплава нужны равные массы металлов:</p>"
    html += line(rf"x+y=\sqrt{{{total}-x^2}}+{first}-y\quad(*)")
    html += "<p>Масса сплава равна сумме масс металлов. Найдём верхнюю оценку на всём отрезке допустимой добычи второй области, затем проверим достижимость:</p>"
    html += line(rf"m(x)=x+\sqrt{{{total}-x^2}}+{first},\quad 0\le x\le {upper}")
    html += "<p>Найдём производную внутри отрезка:</p>"
    html += line(
        rf"m'(x)=1-\frac{{x}}{{\sqrt{{{total}-x^2}}}}=\frac{{\sqrt{{{total}-x^2}}-x}}{{\sqrt{{{total}-x^2}}}}"
    )
    html += "<p>Знаменатель положителен. Найдём единственный нуль производной:</p>"
    html += line(rf"m'(x)=0\iff\sqrt{{{total}-x^2}}=x\iff x={critical}")
    html += (
        "<p>До этой точки производная положительна, после неё отрицательна. Укажем знаки производной и поведение функции на рисунке:</p>"
        + diagram
    )
    html += f"<p>Функция возрастает до x={critical}, затем убывает; поэтому её наибольшее значение на замкнутом отрезке достигается в этой точке. Из равенства (*) найдём добычу алюминия в первой области:</p>"
    html += line(rf"y=\frac{{{first}}}{{2}}={f(a.first / 2)}")
    html += f"<p>Первая область добывает по {answer(a.first / 2)} кг каждого металла: обе массы неотрицательны, а суммарная затрата труда равна T. Вторая область добывает по {critical} кг; проверим её затрату труда:</p>"
    html += line(rf"({critical})^2+({critical})^2={total}=T")
    html += "<p>Баланс металлов и оба ограничения труда выполнены, значит найденный максимум достижим. Вычислим массу сплава:</p>"
    return html + line(
        rf"m({critical})={critical}+\sqrt{{{total}-({critical})^2}}+{first}={f(a.result)}"
    )


def build_context_repair_plan(context):
    content, a = calculate(context)
    diagram, key, changes = diagrams.image(
        content, "image_1", _ALT, source_id=_CHARTS[a.critical][0]
    )
    return diagrams.repair(
        _section(content, "condition"),
        _section(content, "answer"),
        _section(content, "solution"),
        answer(a.result),
        proof(a, diagram),
        (key,),
        changes,
    )
