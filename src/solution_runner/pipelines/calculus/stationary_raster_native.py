"""Plan stationary-point repairs for native and audited SVG graphs."""

from dataclasses import replace
from fractions import Fraction
from html import escape

from ..equations.linear_system_intervals import interval_latex
from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition, line
from ..triangles.right.basic_parent import _targeted
from . import graph_input, graph_stationary, primitive_svg


def _native_points(context, data):
    from .stationary_raster_runner import _read

    question, _, _ = _read(context)
    entry, points = primitive_svg.read(data, replace(question, kind="count"))
    return question, entry, points


def _audited_input(context):
    from .stationary_raster_runner import _read

    question, _, _ = _read(context)
    parsed = graph_input.read_graph(context)
    entry = parsed[5]
    if entry.get("curve_name") != "f" or tuple(
        map(Fraction, entry.get("domain", ()))
    ) != (question.domain.lower, question.domain.upper):
        raise UnsupportedCondition(
            "the audited curve and domain must match the question"
        )
    points = entry.get("stationary_points")
    if not isinstance(points, list) or len(
        graph_stationary.select(points, question.domain)
    ) != len(points):
        raise UnsupportedCondition("complete stationary-point coordinates are required")
    return parsed, question, graph_stationary.select(points, question.interval)


def _native_plan(context, data, generated):
    from .stationary_raster_runner import ALT, KEY

    try:
        parsed, question, points = _audited_input(context)
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


def proof(question, points):
    def inline(formula):
        return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'

    html = "<p>Прямая " + inline("y=" + str(question.horizontal))
    html += " параллельна оси абсцисс. В точках, где касательная к графику горизонтальна, производная равна нулю:</p>"
    html += line("f'(x)=0")
    html += (
        "<p>Посчитаем точки с горизонтальной касательной на заданном промежутке "
        + inline(interval_latex(question.interval))
        + ". Их количество — "
        + str(len(points))
        + ".</p>"
    )
    return html
