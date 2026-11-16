"""Count zeros through a primitive's stationary points; convert PNGs in-place."""

import hashlib
from copy import deepcopy
from dataclasses import replace
from html import escape

from bs4 import BeautifulSoup

from ..equations.linear_system_intervals import interval_latex
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line, normalize, rewrite
from ..triangles.right.basic_parent import _targeted
from . import graph_input, graph_stationary, primitive_svg, raster_primitive

KEY = "primitive_stationary_points"
ALT = "Экстремумы первообразной на заданном промежутке"


def _read(context, *, primitive_only=True):
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
    text = normalize(graph_input._read_text(clean)[4]).replace(
        ")и одной из первообразных", ") — одной из первообразных"
    )
    text = text.replace("график дифференцируемой функции", "график функции")
    text = text.replace(
        "), которая является одной из первообразных", "), одной из первообразных"
    )
    question = graph_stationary.parse(text)
    if primitive_only and question.kind != "primitive":
        raise UnsupportedCondition(
            "the raster rule requires a stated primitive and f(x)=0"
        )
    if (
        question.interval.lower <= question.domain.lower
        or question.interval.upper >= question.domain.upper
    ):
        raise UnsupportedCondition(
            "the requested interval must be inside the open domain"
        )
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


def _model(context, data):
    question, condition, asset = _read(context)
    if data.startswith(raster_primitive.PNG):
        if any(
            a["asset_key"] not in (asset["asset_key"], KEY)
            for a in context["normalized_content"]["assets"]
        ):
            raise UnsupportedCondition(
                "unrelated primitive assets need separate review"
            )
        model = raster_primitive.recover(data, question)
    else:
        model = raster_primitive.embedded(data, question)
    if model is None:
        raise UnsupportedCondition("the primitive SVG has no verified model")
    selected = raster_primitive.select(model, question)
    return question, condition, asset, model, selected


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
            question, _, _ = _read(context, primitive_only=False)
            entry, selected = primitive_svg.read(data, question)
            svg = graph_stationary.render_svg(entry, data, question.interval, selected)
            return (solution_diagrams.spec(KEY, svg),)
    _question, _condition, asset, model, selected = _model(context, data)
    first = (
        (solution_diagrams.spec(asset["asset_key"], raster_primitive.render(model)),)
        if data.startswith(raster_primitive.PNG)
        else ()
    )
    return (
        *first,
        solution_diagrams.spec(
            KEY, raster_primitive.render(model, selected_points=selected)
        ),
    )


def proof(question, points):
    def inline(formula):
        return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'

    if question.kind == "count":
        html = (
            "<p>Нас просят найти количество решений уравнения "
            + inline("f'(x)=0")
            + ".</p>"
        )
    else:
        html = "<p>Нас просят найти количество решений уравнения " + inline("f(x)=0")
        html += (
            ". По определению первообразной, " + inline("f(x)=F'(x)") + ", поэтому:</p>"
        )
        html += line("f(x)=0" + r"\quad\Rightarrow\quad F'(x)=0")
    if any(p["kind"] not in ("max", "min") for p in points):
        html += "<p>Производная равна нулю в точках с горизонтальной касательной. На данном графике учитываем экстремумы и стационарные точки без экстремума. "
        html += "Посчитаем такие точки на заданном промежутке "
    else:
        html += "<p>Правило: Если производная равна 0 то это экстремум(лок. min/лок. max)</p><p>"
        html += "Посчитаем экстремумы на заданном промежутке "
    html += (
        inline(interval_latex(question.interval))
        + ". Их количество — "
        + str(len(points))
        + ".</p>"
    )
    return html


def _native_plan(context, data, generated):
    try:
        parsed, question, points = graph_stationary._input(context)
    except UnsupportedCondition:
        question, condition, _ = _read(context, primitive_only=False)
        entry, points = primitive_svg.read(data, question)
        svg = graph_stationary.render_svg(entry, data, question.interval, points)
        content = context["normalized_content"]
        figure, key, changes = solution_diagrams.image(
            content, KEY, ALT, svg=svg, generated=generated
        )
        html = (
            proof(question, points)
            if question.kind in ("primitive", "count")
            else graph_stationary.proof(question, points)[1]
        )
        solution = next(
            (s for s in content["sections"] if s["key"] == "solution"), None
        )
        obsolete = [
            a
            for a in content["assets"]
            if a["asset_key"] in (solution or {}).get("asset_keys", [])
            and a["asset_key"] != KEY
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
            figure + html,
            (key,),
            removed + tuple(changes),
        )
    if question.kind not in ("primitive", "count"):
        return graph_stationary.build_context_repair_plan(
            context, condition_asset_bytes=data, generated_solution_assets=generated
        )
    content, condition, ans, solution, _, entry, source = parsed
    condition_diagram.verify_download(source, data)
    svg = (
        graph_stationary.render_svg(entry, source, question.interval, points)
        if entry.get("highlight_stationary")
        else None
    )
    figure, key, changes = graph_input.figure(
        content, entry, svg=svg, generated=generated
    )
    return solution_diagrams.repair(
        condition,
        ans,
        solution,
        str(len(points)),
        figure + proof(question, points),
        (key,) if key else (),
        changes,
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
    svg = raster_primitive.render(model, selected_points=selected)
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
    condition_svg = raster_primitive.render(model)
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
    image["alt"] = "График первообразной"
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
    return replace(plan, solution_html=expected, transformations=tuple(changes))
