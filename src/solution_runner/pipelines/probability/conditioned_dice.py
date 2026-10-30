"""Two fair dice with one excluded face and a checked or rebuilt outcome table."""

import hashlib
import re
from dataclasses import dataclass, replace
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from solution_runner.pipelines.word_problems.common import rewrite

from .common import (
    COUNT,
    UnsupportedCondition,
    count,
    finish,
    line,
    normalize,
    probability,
    require_content,
)

_SUM = re.compile(
    rf"Игральную кость бросили два раза\. Известно, что (?P<face>{COUNT}) очк(?:а|ов) не выпали ни разу\. Найдите при этом условии вероятность события «сумма выпавших очков окажется равна (?P<sum>\d+)»\."
)
_PARITY = re.compile(
    rf"Игральный кубик подбросили два раза\. Известно, что (?P<face>{COUNT}) очк(?:а|ов) не выпало ни разу\. Какова вероятность, что выпал(?:о|и) два (?P<parity>четных|нечетных) числа[?.]"
)


@dataclass(frozen=True)
class Case:
    excluded: int
    kind: str
    value: int


# Read-only, checksum-verified diagrams: the keys describe mathematics, never tasks.
_REUSABLE = {
    Case(3, "sum", 8): "7b0cf362-dbb8-4594-b400-5e1f598a67cd",
    Case(6, "sum", 2): "b187bc8a-a8d9-4151-8345-9bb5bb47a7fb",
    Case(2, "sum", 12): "7c7ceb6f-2e5d-4a17-84cf-5a869c2710f9",
    Case(2, "sum", 4): "20999888-d3ea-411e-a8df-11b5026b29ab",
    Case(3, "parity", 0): "57d0e300-c7dc-4294-bf11-c2f1eacdc2db",
    Case(2, "parity", 1): "21463d76-09a8-4866-be78-0d2f8871b956",
}
_KEY = "generated_conditioned_dice_table"
_ALT = (
    "Таблица исходов двух бросков: синие клетки допустимы, зелёные плюсы благоприятны"
)


def parse(text):
    text = normalize(text)
    if match := _SUM.fullmatch(text):
        case = Case(count(match["face"]), "sum", int(match["sum"]))
    elif match := _PARITY.fullmatch(text):
        case = Case(count(match["face"]), "parity", int(match["parity"] == "нечетных"))
    else:
        raise UnsupportedCondition("unsupported complete conditional-dice condition")
    outcomes(case)
    return case


def outcomes(case):
    if not 1 <= case.excluded <= 6 or case.kind not in ("sum", "parity"):
        raise UnsupportedCondition("unsupported die face or event")
    if case.kind == "parity" and case.value not in (0, 1):
        raise UnsupportedCondition("unsupported die parity")
    domain = [
        (a, b) for a in range(1, 7) for b in range(1, 7) if case.excluded not in (a, b)
    ]
    selected = [
        row
        for row in domain
        if (
            sum(row) == case.value
            if case.kind == "sum"
            else all(x % 2 == case.value for x in row)
        )
    ]
    return domain, selected


def _content(context):
    content = context.get("normalized_content")
    if not isinstance(content, dict) or not isinstance(content.get("sections"), list):
        raise UnsupportedCondition("normalized sections are required")
    if any(
        s.get("asset_keys") for s in content["sections"] if s.get("key") != "solution"
    ):
        raise UnsupportedCondition("only solution diagrams are supported")
    clean = {**context, "normalized_content": {**content, "assets": []}}
    _, condition, answer, solution, text = require_content(clean)
    return content, condition, answer, solution, parse(text)


def asset_requirements(context):
    case = _content(context)[-1]
    source_id = _REUSABLE.get(case)
    return (
        ({"source_asset_id": source_id, "section_id": "solution:1", "alt_text": _ALT},)
        if source_id
        else ()
    )


def render_svg(case):
    domain, selected = outcomes(case)
    root = ET.fromstring(
        Path(__file__).with_name("dice_table_template.svg").read_bytes()
    )
    ns = "{http://www.w3.org/2000/svg}"
    ET.register_namespace("", ns[1:-1])
    marker = next(e.attrib["d"] for e in root.iter() if e.get("fill") == "#0D9948")
    for parent in root.iter():
        for child in list(parent):
            if child.get("fill") in ("#143B8F", "#0D9948"):
                parent.remove(child)
    xs = (49.404, 77.301, 105.316, 133.331, 161.346, 189.361, 219.483)
    ys = (38.253, 69.168, 96.987, 124.806, 152.625, 180.444, 208.332)
    background = ET.Element(ns + "g", {"data-role": "admissible-outcomes"})
    for a, b in domain:
        ET.SubElement(
            background,
            ns + "rect",
            {
                "x": str(xs[b - 1]),
                "y": str(ys[a - 1]),
                "width": str(xs[b] - xs[b - 1]),
                "height": str(ys[a] - ys[a - 1]),
                "fill": "#143B8F",
                "opacity": "0.5",
                "data-outcome": f"{a},{b}",
            },
        )
    root.insert(0, background)
    marks = ET.SubElement(root, ns + "g", {"data-role": "favorable-outcomes"})
    for a, b in selected:
        x, y = (xs[b - 1] + xs[b]) / 2, (ys[a - 1] + ys[a]) / 2
        ET.SubElement(
            marks,
            ns + "path",
            {
                "fill": "#0D9948",
                "d": marker,
                "transform": f"translate({x - 204.1695:.4f} {y - 83.5045:.4f})",
                "data-outcome": f"{a},{b}",
            },
        )
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context):
    case = _content(context)[-1]
    if case in _REUSABLE:
        return ()
    svg = render_svg(case)
    return (
        {
            "asset_key": _KEY,
            "svg_text": svg,
            "sha256": hashlib.sha256(svg.encode()).hexdigest(),
        },
    )


def _diagram(content, case, generated):
    if source_id := _REUSABLE.get(case):
        asset = next(
            (a for a in content.get("assets", []) if a.get("asset_id") == source_id),
            None,
        )
        if asset is None:
            raise UnsupportedCondition(
                "the mathematically compatible source diagram is required"
            )
        key, source_id = asset["asset_key"], asset["asset_id"]
        url = asset.get("url") or "/assets/" + source_id
        changes = []
    else:
        if len(generated) != 1 or generated[0].get("asset_key") != _KEY:
            raise UnsupportedCondition("a generated conditional-dice table is required")
        asset = generated[0]
        expected = hashlib.sha256(render_svg(case).encode()).hexdigest()
        if asset.get("sha256") != expected:
            raise UnsupportedCondition(
                "the generated table does not match this probability space"
            )
        key, source_id, url = _KEY, asset["source_asset_id"], asset["url"]
        existing = next(
            (a for a in content.get("assets", []) if a.get("asset_key") == key), None
        )
        changes = (
            []
            if existing and existing.get("asset_id") == source_id
            else [
                {
                    "transformation_target_id": "asset:" + key,
                    "operation": "add",
                    "value": {
                        "asset_key": key,
                        "asset_id": source_id,
                        "url": url,
                        "kind": "ordinary_image",
                        "alt": _ALT,
                        "parent_target_id": "section:solution:1",
                        "position": 0,
                    },
                }
            ]
        )
    markup = f'<center><img alt="{_ALT}" data-asset-key="{escape(key, quote=True)}" data-asset-id="{escape(source_id, quote=True)}" src="{escape(url, quote=True)}"/></center>'
    if changes:
        changes[0]["value"]["html"] = markup
    return key, markup, changes


def build_context_repair_plan(context, *, generated_solution_assets=()):
    content, condition, answer_section, solution, case = _content(context)
    domain, selected = outcomes(case)
    key, diagram, asset_changes = _diagram(content, case, generated_solution_assets)
    answer, calculation = probability(len(selected), len(domain))
    html = f"<p>Условию, что число {case.excluded} не выпало ни разу, соответствуют {len(domain)} упорядоченных исходов двух бросков. В таблице они отмечены синим цветом. Благоприятных исходов — {len(selected)}, они отмечены зелёным плюсом:</p>"
    html += (
        diagram
        + "<p>Разделим число благоприятных исходов на число допустимых при данном условии:</p>"
        + calculation
    )
    if case.kind == "parity":
        count_one = sum(x != case.excluded and x % 2 == case.value for x in range(1, 7))
        html += "<p>Другой способ. При одном броске после исключения указанного числа остаются пять равновозможных значений. Посчитаем значения нужной чётности:</p>"
        html += line(rf"p=\frac{{{count_one}}}{{5}}")
        html += "<p>Ограничение наложено на каждый бросок отдельно, поэтому броски остаются независимыми. Вероятность двух нужных результатов равна произведению:</p>"
        html += line(
            rf"P=\frac{{{count_one}}}{{5}}\cdot\frac{{{count_one}}}{{5}}=\frac{{{len(selected)}}}{{25}}"
        ) + line("P=" + answer.replace(",", "{,}"))
    plan = finish(condition, answer_section, solution, answer, html)
    changes = list(plan.transformations)
    if not any(
        t["transformation_target_id"].startswith("section:solution") for t in changes
    ) and solution.get("asset_keys") != [key]:
        changes.append(rewrite(solution, "solution", "Решение", html))
    for change in changes:
        if change["transformation_target_id"].startswith("section:solution"):
            change["value"]["asset_keys"] = [key]
    return replace(plan, transformations=tuple(asset_changes + changes))
