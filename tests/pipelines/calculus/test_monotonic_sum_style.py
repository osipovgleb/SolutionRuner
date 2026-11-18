"""The selected integer points and the short proof agree with the displayed curve."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from graph_samples import _apply_local, source_bytes
from test_graph_monotonic import sample

from solution_runner.pipelines.calculus import graph_input
from solution_runner.pipelines.calculus import monotonic_sum_input as source
from solution_runner.pipelines.calculus import monotonic_sum_render as drawing
from solution_runner.pipelines.calculus import monotonic_sum_runner as runner

FIXTURES = Path(__file__).parent / "fixtures/monotonic_sum"


def prepare(context, data):
    specs = runner.diagram_specs(context, condition_asset_bytes=data)
    generated = tuple(
        {
            **s,
            "source_asset_id": "local-" + s["asset_key"],
            "url": "/assets/local-" + s["asset_key"],
        }
        for s in specs
    )
    return runner.build_context_repair_plan(
        context, condition_asset_bytes=data, generated_solution_assets=generated
    ), specs


def test_boundary_zero_is_counted_but_open_domain_endpoints_are_not():
    context = sample("6429")["context"]
    data = (
        graph_input.ASSETS / "cdf2b435-ca9d-403e-91c0-fc92fb92fcb8.svg"
    ).read_bytes()
    graph = source.input(context, data)
    assert graph.integers == (2, 3, 4, 5)
    assert graph.result == "14"
    svg = ET.fromstring(drawing.render(graph))
    layer = svg.find(drawing.NS + 'g[@id="derivative-signs-and-integers"]')
    assert [
        int(n.get("data-integer-abscissa"))
        for n in layer.iter(drawing.NS + "circle")
        if n.get("data-integer-abscissa")
    ] == [2, 3, 4, 5]
    assert [
        n.text for n in layer.iter(drawing.NS + "text") if n.text in ("+", "−")
    ] == ["+", "−", "+"]
    assert (
        len(list(layer.iter(drawing.NS + "line"))) == 2
    )  # Only the zero verticals; no added grid.
    original = ET.fromstring(data)
    assert [n.get("d") for n in svg.iter(drawing.NS + "path")][
        : len(list(original.iter(drawing.NS + "path")))
    ] == [n.get("d") for n in original.iter(drawing.NS + "path")]
    proof = drawing.proof(graph.integers)
    assert len(BeautifulSoup(proof, "html.parser").find_all("p")) == 2
    assert "S=2+3+4+5=14" in proof
    assert "производная" not in proof and "x\\in" not in proof
    plan, specs = prepare(context, data)
    soup = BeautifulSoup(plan.solution_html, "html.parser")
    assert [node.name for node in soup.contents] == ["p", "center", "p", "center", "p"]
    assert (
        soup.contents[0].get_text().startswith("Правило. Если производная положительна")
    )
    assert (
        soup.contents[-1]
        .get_text()
        .startswith("Примечание. Когда дан график производной")
    )
    assert "Если дан график самой функции" in soup.contents[-1].get_text()
    assert len(specs) == 1  # Preserve the native condition SVG byte for byte.
    assert not any(
        t["transformation_target_id"] == "asset:image_1" for t in plan.transformations
    )
    original_image = BeautifulSoup(
        context["normalized_content"]["sections"][0]["html"], "html.parser"
    ).img
    formatted = BeautifulSoup(plan.condition_html, "html.parser")
    assert [node.name for node in formatted.contents] == ["p", "p", "center"]
    assert formatted.img["data-asset-id"] == original_image["data-asset-id"]


@pytest.mark.parametrize(
    ("task", "left", "right"), [("27499", -7, -1), ("27500", -1, 5)]
)
def test_longest_interval_is_highlighted_on_the_x_axis(task, left, right):
    case = sample(task)
    graph = source.input(case["context"], source_bytes(case))
    root = ET.fromstring(drawing.render(graph))
    overlay = root.find(drawing.NS + 'g[@id="derivative-signs-and-integers"]')
    (highlight,) = [
        line
        for line in overlay.iter(drawing.NS + "line")
        if line.get("stroke") == "#2563eb"
    ]
    ox, oy = graph.entry["svg_origin"]
    unit = graph.entry.get("x_unit", graph.entry["svg_unit"])
    assert float(highlight.get("y1")) == float(highlight.get("y2")) == oy
    assert float(highlight.get("x1")) == ox + left * unit
    assert float(highlight.get("x2")) == ox + right * unit


@pytest.mark.parametrize("task", ["8051", "7331", "7491", "7517"])
def test_png_conversion_is_replayable_and_negative_abscissas_have_parentheses(task):
    context = json.loads((FIXTURES / (task + ".json")).read_text())
    data = (FIXTURES / (task + ".png")).read_bytes()
    original = deepcopy(context)
    plan, specs = prepare(context, data)
    assert context == original
    expected, calculation = {
        "8051": ("-3", "S=(-6)+(-2)+(-1)+0+1+2+3=-3"),
        "7331": ("-10", "S=(-6)+(-4)+(-2)+(-1)+0+1+2=-10"),
        "7491": ("25", "S=(-1)+0+2+7+8+9=25"),
        "7517": ("6", "S=(-3)+(-1)+0+1+2+3+4=6"),
    }[task]
    assert plan.answer == expected
    assert calculation in plan.solution_html
    assert len(specs) == 2
    # Replay all changes locally, including replacing the condition raster.
    condition_svg = next(
        s["svg_text"].encode() for s in specs if s["asset_key"] == "image_1"
    )
    for section in context["normalized_content"]["sections"]:
        section["transformation_target_id"] = "section:" + section["section_id"]
    _apply_local(context, plan.transformations)
    replay, replay_specs = prepare(context, condition_svg)
    assert replay.transformations == ()
    assert len(replay_specs) == 1


def test_function_graph_counts_rising_points_and_excludes_stationary_boundaries():
    context = sample("27487")["context"]
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    asset = next(
        a
        for a in context["normalized_content"]["assets"]
        if a["asset_key"] in condition["asset_keys"]
    )
    data = (graph_input.ASSETS / (asset["asset_id"] + ".svg")).read_bytes()
    graph = source.input(context, data)
    assert graph.integers == (-2, -1, 5, 6)
    assert graph.result == "4"
    assert 0 not in graph.integers and 7 not in graph.integers
    plan, specs = prepare(context, data)
    assert "Их количество — 4" in plan.solution_html
    assert plan.solution_html.startswith(drawing.COUNT_RULE)
    assert "Точки экстремума не учитываем" in plan.solution_html
    assert "S=" not in plan.solution_html
    assert "y=f(x)" not in drawing.proof(graph.integers, count=True)
    root = ET.fromstring(specs[-1]["svg_text"])
    layer = root.find(drawing.NS + 'g[@id="derivative-signs-and-integers"]')
    assert [
        n.text for n in layer.iter(drawing.NS + "text") if n.text in ("+", "−")
    ] == ["−", "+", "−", "+", "−"]


def test_extremum_sum_preserves_native_arcs_and_includes_reversals_at_joins():
    cases = json.loads(
        (Path(__file__).parent / "fixtures/category_9_extrema.json").read_text()
    )["cases"]
    context = next(c["context"] for c in cases if c["task"] == "7545")
    _, _, asset = source.read(context)
    data = (graph_input.ASSETS / (asset["asset_id"] + ".svg")).read_bytes()
    graph = source.input(context, data)
    assert graph.integers == (-5, -3, -2, 0, 1, 2, 3)
    assert graph.result == "-4"
    plan, specs = prepare(context, data)
    assert len(specs) == 1
    assert plan.solution_html.startswith(drawing.EXTREMA_RULE)
    assert "S=(-5)+(-3)+(-2)+0+1+2+3=-4" in plan.solution_html
    root, original = ET.fromstring(specs[0]["svg_text"]), ET.fromstring(data)
    assert root.get("viewBox").split() == original.get("viewBox").split()
    assert [n.get("d") for n in root.iter(drawing.NS + "path")] == [
        n.get("d") for n in original.iter(drawing.NS + "path")
    ]
    layer = root.find(drawing.NS + 'g[@id="derivative-signs-and-integers"]')
    assert len(list(layer.iter(drawing.NS + "circle"))) == 7
    assert not list(layer.iter(drawing.NS + "line"))


@pytest.mark.parametrize(
    ("task", "point", "direction", "side"),
    [("27491", "-3", "убывает", "левом"), ("27492", "-7", "возрастает", "левом")],
)
def test_derivative_sign_selects_the_correct_endpoint(task, point, direction, side):
    context = sample(task)["context"]
    _, _, asset = source.read(context)
    entry = graph_input.EVIDENCE[asset["asset_id"]]
    data = (
        graph_input.ASSETS
        / entry.get("filename", asset["asset_id"] + entry.get("extension", ".svg"))
    ).read_bytes()
    plan, specs = prepare(context, data)
    assert plan.answer == point
    assert plan.solution_html.startswith(drawing.RULE)
    assert f"функция {direction}" in plan.solution_html
    assert f"на {side} конце" in plan.solution_html
    assert f"x_0={point}" in plan.solution_html
    root = ET.fromstring(specs[-1]["svg_text"])
    layer = root.find(drawing.NS + 'g[@id="derivative-signs-and-integers"]')
    assert len(list(layer.iter(drawing.NS + "line"))) == 2


def test_maximum_count_marks_only_selected_downward_crossings():
    cases = json.loads(
        (Path(__file__).parent / "fixtures/category_9_extrema.json").read_text()
    )["cases"]
    context = next(c["context"] for c in cases if c["task"] == "27494")
    _, _, asset = source.read(context)
    data = (graph_input.ASSETS / (asset["asset_id"] + ".svg")).read_bytes()
    graph = source.input(context, data)
    assert len(graph.zeros) > len(graph.marks) == 1
    ox, oy = graph.entry["svg_origin"]
    px, py = graph.marks[0]
    assert round((px - ox) / graph.entry["x_unit"]) == 7
    assert py == oy
    plan, specs = prepare(context, data)
    assert plan.answer == "1"
    assert "с плюса на минус" in plan.solution_html
    root = ET.fromstring(specs[-1]["svg_text"])
    assert len(root.findall(f".//{drawing.NS}circle[@fill='#15803d']")) == 1
