"""One physical derivative family evaluates velocity and its requested events."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition, finish, line
from .common import T, answer, polynomial, read, real_roots

_NUMBER = r"[−-]?\d+(?:[,.]\d+)?"
_DEFINITIONS = (
    r"\(где x — расстояние от точки отсчета в метрах, t — время в секундах, измеренное с начала движения\)\.",
    r"где x — расстояние от точки отсчета в метрах, t — время в секундах, прошедшее с начала движения\.",
    r", где x — расстояние от точки отсчета \(в метрах\), t — время движения \(в секундах\)\.",
)


def _question(text):
    pattern = (
        r"Материальная точка движется прямолинейно по закону x\(t\)\s*=\s*(?P<law>.+?)\s*(?P<definition>"
        + "|".join(_DEFINITIONS)
        + r") (?P<query>.+)"
    )
    match = re.fullmatch(pattern, text)
    if not match:
        raise UnsupportedCondition("unsupported complete polynomial motion question")
    query = match["query"].replace(r"\,\mathrm{с}", " с")
    evaluate = re.fullmatch(
        r"Найдите ее скорость \((?:в м/[сc]|в метрах в секунду)\) в момент времени t\s*=\s*(?P<value>"
        + _NUMBER
        + r")\s*[сc]\.",
        query,
    )
    solve = re.fullmatch(
        r"В какой момент времени \(в секундах\) ее скорость была равна (?P<value>"
        + _NUMBER
        + r") м/[сc]\?",
        query,
    )
    if not evaluate and not solve:
        raise UnsupportedCondition(
            "a velocity value or its nonnegative time must be requested"
        )
    value = sp.Rational(
        (evaluate or solve)["value"].replace(",", ".").replace("−", "-")
    )
    return polynomial(match["law"], T), value, bool(evaluate)


def _graph(context):
    content = context["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    return bool(condition.get("asset_keys"))


def _motion_graph(context):
    from . import graph_stationary

    data, question, points = graph_stationary._input(context)
    if question.kind != "motion":
        raise UnsupportedCondition(
            "the graph must describe motion and ask when its velocity is zero"
        )
    return data, question, points


def required_assets(context):
    if not _graph(context):
        _question(read(context)[3])
        return ()
    from . import graph_input

    data, _, _ = _motion_graph(context)
    return graph_input.requirements(data[5])


def diagram_specs(context, *, condition_asset_bytes=None):
    if not _graph(context):
        return ()
    from . import graph_stationary

    _motion_graph(context)
    return graph_stationary.diagram_specs(context)


def _build_graph(context, data, generated):
    from ..probability import condition_diagram, solution_diagrams
    from . import graph_input, graph_stationary

    parsed, q, points = _motion_graph(context)
    content, condition, ans, solution, _, entry, source = parsed
    # The immutable condition asset is verified against its audited ID and SHA
    # by read_graph. A supplied download must also match byte for byte.
    if data is not None:
        condition_diagram.verify_download(source, data)
    svg = (
        graph_stationary.render_svg(entry, source, q.interval, points)
        if entry.get("highlight_stationary")
        else None
    )
    figure, key, changes = graph_input.figure(
        content, entry, svg=svg, generated=generated
    )
    html = "<p>Скорость равна производной расстояния по времени:</p>" + line(
        "V(t)=s'(t)"
    )
    html += "<p>Найдём моменты, когда скорость обращается в ноль:</p>" + line(
        "V(t)=0\\iff s'(t)=0"
    )
    html += (
        "<p>Считаем точки графика с горизонтальной касательной, не включая начало и конец движения. Таких точек — "
        + str(len(points))
        + ".</p>"
    )
    from bs4 import BeautifulSoup

    html = str(BeautifulSoup(figure + html, "html.parser"))
    if solution is not None:
        solution = {
            **solution,
            "html": str(BeautifulSoup(solution.get("html", ""), "html.parser")),
        }
    return solution_diagrams.repair(
        condition,
        ans,
        solution,
        str(len(points)),
        html,
        (key,) if key else (),
        changes,
    )


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    if _graph(context):
        return _build_graph(context, condition_asset_bytes, generated_solution_assets)
    from bs4 import BeautifulSoup

    from .motion_proof import render

    condition, current_answer, solution, text = read(context)
    law, value, evaluate = _question(text)
    velocity = sp.diff(law, T)
    roots = []
    if evaluate:
        if value < 0:
            raise UnsupportedCondition(
                "time measured from the start cannot be negative"
            )
        result = sp.simplify(velocity.subs(T, value))
    else:
        roots = real_roots(sp.expand(velocity - value), T)
        valid = [r for r in roots if r.is_nonnegative is True]
        if len(valid) != 1:
            raise UnsupportedCondition(
                "the motion question does not determine one nonnegative time"
            )
        result = valid[0]
    html = str(
        BeautifulSoup(
            render(law, velocity, value, evaluate, result, roots), "html.parser"
        )
    )
    if solution is not None:
        solution = {
            **solution,
            "html": str(BeautifulSoup(solution.get("html", ""), "html.parser")),
        }
    return finish(condition, current_answer, solution, answer(result), html)
