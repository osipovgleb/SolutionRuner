"""Prepare monotonicity sum solutions using the existing PNG-to-SVG fitter."""

from copy import deepcopy
from dataclasses import replace

from bs4 import BeautifulSoup

from ..probability import solution_diagrams
from ..triangles.right.basic_parent import _targeted
from . import (
    derivative_level_runner,
    graph_condition_layout,
    graph_monotonic,
    marked_curve_render,
    monotonic_sum_input,
    monotonic_sum_render,
)

KEY = "derivative_sign_chart"
STATIONARY_KEY = "stationary_point_guides"
NEIGHBORHOOD_KEY = "colored_function_neighborhood"
ALT = (
    "Знаки производной, направление изменения функции и целые точки нужных промежутков"
)


def required_assets(context):
    if _level_question(context):
        return derivative_level_runner.required_assets(context)
    q, _, _ = monotonic_sum_input.read(context)
    return graph_monotonic.required_assets(context) if q.operation == "value" else ()


def diagram_specs(context, *, condition_asset_bytes=None):
    if condition_asset_bytes is None:
        return ()
    if _level_question(context):
        return derivative_level_runner.diagram_specs(
            context, condition_asset_bytes=condition_asset_bytes
        )
    q, _, _ = monotonic_sum_input.read(context)
    if q.operation == "value":
        return graph_monotonic.diagram_specs(context)
    graph = monotonic_sum_input.input(context, condition_asset_bytes)
    specs = []
    if graph.model is not None and graph.source != condition_asset_bytes:
        specs.append(
            solution_diagrams.spec(graph.asset["asset_key"], graph.source.decode())
        )
    key, svg = _solution_diagram(graph)
    specs.append(solution_diagrams.spec(key, svg))
    return tuple(specs)


def _solution_diagram(graph):
    q = graph.question
    if getattr(q, "target", "") != "neighborhood":
        key = STATIONARY_KEY if q.operation == "stationary" else KEY
        return key, monotonic_sum_render.render(graph)
    entry = graph.entry
    segments = entry["curve_segments"]
    turns = [
        point
        for point, a, b in zip(graph.zeros, graph.bands, graph.bands[1:])
        if a[2] != b[2]
    ]
    chart = {
        "left": segments[0][0][0],
        "right": segments[-1][-1][0],
        "initial": graph.bands[0][2],
        "turns": turns,
    }
    origin = entry["svg_origin"][0]
    unit = entry.get("x_unit", entry["svg_unit"])
    points = [
        {"svg": [x, monotonic_sum_input.ordinate(entry, x)], "sign": q.sign}
        for n in graph.integers
        for x in [origin + n * unit]
    ]
    return NEIGHBORHOOD_KEY, marked_curve_render.render(
        graph.source,
        {**entry, "function_sign_chart": chart},
        points,
        points,
        signed=True,
        project_marks=True,
    )


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    plan = _build_context_repair_plan(
        context,
        condition_asset_bytes=condition_asset_bytes,
        generated_solution_assets=generated_solution_assets,
    )
    return graph_condition_layout.apply_layout(plan, context)


def _build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    if _level_question(context):
        return derivative_level_runner.build_context_repair_plan(
            context,
            condition_asset_bytes=condition_asset_bytes,
            generated_solution_assets=generated_solution_assets,
        )
    q, _, _ = monotonic_sum_input.read(context)
    if q.operation == "value":
        return graph_monotonic.build_context_repair_plan(
            context,
            condition_asset_bytes=condition_asset_bytes,
            generated_solution_assets=generated_solution_assets,
        )
    graph = monotonic_sum_input.input(context, condition_asset_bytes)
    content = context["normalized_content"]
    sections = content["sections"]
    answer = next((s for s in sections if s["key"] == "answer"), None)
    solution = next((s for s in sections if s["key"] == "solution"), None)
    diagram_key, svg = _solution_diagram(graph)
    alt = ALT
    if q.operation == "stationary":
        alt = "График функции с отмеченными точками горизонтального касания"
    elif diagram_key == NEIGHBORHOOD_KEY:
        alt = "Участки возрастания и убывания с отмеченными целыми точками"
    elif q.operation in ("count", "point") and q.derivative:
        alt = "Знаки производной и отмеченные точки на заданном промежутке"
    figure, key, changes = solution_diagrams.image(
        content, diagram_key, alt, svg=svg, generated=generated_solution_assets
    )
    removed = tuple(
        {"transformation_target_id": "asset:" + a["asset_key"], "operation": "remove"}
        for a in content["assets"]
        if a["asset_key"] in (solution or {}).get("asset_keys", [])
        and a["asset_key"] not in (key, graph.asset["asset_key"])
    )
    if getattr(q, "target", "") == "neighborhood":
        html = monotonic_sum_render.neighborhood_solution(figure, graph)
    elif q.operation == "stationary":
        html = monotonic_sum_render.stationary_solution(figure, graph)
    elif q.operation == "global":
        html = monotonic_sum_render.endpoint_solution(figure, graph)
    elif q.operation == "length":
        html = monotonic_sum_render.longest_interval_solution(figure, graph)
    elif q.operation in ("count", "point") and q.derivative:
        html = monotonic_sum_render.derivative_extrema_solution(figure, graph)
    else:
        html = monotonic_sum_render.solution(
            figure,
            graph.integers,
            count=q.operation == "count",
            extrema=q.operation == "sum" and not q.derivative,
        )
    plan = solution_diagrams.repair(
        graph.condition,
        _targeted(answer),
        _targeted(solution),
        graph.result,
        html,
        (key,),
        removed + tuple(changes),
    )
    plan = derivative_level_runner._replace_condition_raster(
        plan,
        graph.condition,
        graph.asset,
        (condition_asset_bytes, graph.model),
        generated_solution_assets,
        render_svg=lambda model: monotonic_sum_input.render_model(
            model, graph.question
        ),
        alt="График производной функции"
        if graph.question.derivative
        else "График функции",
    )

    def canonical(raw):
        soup = BeautifulSoup(raw or "", "html.parser")
        for tag in soup.find_all(True):
            tag.attrs.pop("data-transformation-target-id", None)
        return str(soup)

    expected = canonical(plan.solution_html)
    filtered = []
    for original in plan.transformations:
        change = deepcopy(original)
        if change["transformation_target_id"].startswith("section:solution"):
            if (
                solution is not None
                and canonical(solution["html"]) == expected
                and solution.get("asset_keys", []) == [key]
            ):
                continue
            change["value"]["html"] = expected
        filtered.append(change)
    return replace(plan, solution_html=expected, transformations=tuple(filtered))


def _level_question(context):
    from ..probability.common import UnsupportedCondition

    try:
        derivative_level_runner._read(context)
    except UnsupportedCondition:
        return False
    return True
