"""Verify SVG topology, lettering, clipping bounds, and exact boundary questions."""

import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from ray_source_cases import CASES, GROUPS, plan, section, solution_html
from test_construction_parent_sources import angle, verify
from test_two_ray_source_methods import geometry_values, replay

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.triangles.right.construction_angles import (
    read_context,
)
from solution_runner.pipelines.triangles.right.construction_svg import (
    _template,
    figure_svg,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def point(line, end):
    return tuple(float(line.get(axis + str(end))) for axis in ("x", "y"))


def polygon(element):
    return [tuple(map(float, p.split(","))) for p in element.get("points").split()]


@pytest.mark.parametrize("pair", ["HD", "HM", "DM"])
@pytest.mark.parametrize("topology", [-1, 0])
def test_generated_svg_has_correct_rays_markers_original_lettering_and_bounds(
    pair, topology
):
    svg = figure_svg(pair, topology)
    root = ET.fromstring(svg)
    original, _, glyphs, styles, _ = _template(pair)
    assert root.get("viewBox") == original.get("viewBox")
    width, height = map(float, root.get("viewBox").split()[2:])
    lines = {e.get("id"): e for e in root.findall("s:line", NS)}
    a, b, c = (
        point(lines["side-AC"], 1),
        point(lines["side-CB"], 2),
        point(lines["side-AC"], 2),
    )
    assert angle(a, c, b) == pytest.approx(90, abs=1e-6)
    rays = {k.removeprefix("ray-"): e for k, e in lines.items() if k.startswith("ray-")}
    assert len(rays) == (1 if topology == 0 else 2)
    feet = {
        role: point(next(e for name, e in rays.items() if role in name), 2)
        for role in pair
    }
    for role, foot in feet.items():
        assert foot[1] == pytest.approx(a[1], abs=1e-6)
        if role == "H":
            assert foot[0] == pytest.approx(c[0], abs=1e-6)
        if role == "M":
            assert foot[0] == pytest.approx((a[0] + b[0]) / 2, abs=1e-6)
        if role == "D":
            assert angle(a, c, foot) == pytest.approx(angle(foot, c, b), abs=1e-5)
        if topology < 0:
            assert rays[role].get("stroke") == styles[role]["stroke"]
    if topology == 0:
        assert feet[pair[0]] == feet[pair[1]]
    else:
        assert feet[pair[0]][0] < feet[pair[1]][0]
        assert angle(a, b, c) < 45
    for marker in root.findall("s:polyline", NS):
        p, q, r = polygon(marker)
        u, v = (p[0] - q[0], p[1] - q[1]), (r[0] - q[0], r[1] - q[1])
        assert abs(u[0] * v[0] + u[1] * v[1]) < 1e-5
    boxes = []
    for name, glyph in glyphs.items():
        generated = root.find("s:g[@id='label-" + name + "']", NS)
        assert generated is not None
        assert [e.get("d") for e in generated.findall(".//s:path", NS)] == [
            e.get("d") for e in glyph.findall(".//s:path", NS)
        ]
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([^ ]+) ([^)]+)\)", generated.get("transform")
            ).groups(),
        )
        rect = generated.find(".//s:rect", NS)
        x, y = float(rect.get("x", 0)) + dx, float(rect.get("y", 0)) + dy
        w, h = float(rect.get("width")), float(rect.get("height"))
        assert -1e-3 <= x < x + w <= width + 1e-3
        assert -1e-3 <= y < y + h <= height + 1e-3
        boxes.append((x, y, x + w, y + h))
    for index, one in enumerate(boxes):
        for two in boxes[index + 1 :]:
            assert min(one[2], two[2]) <= max(one[0], two[0]) or min(
                one[3], two[3]
            ) <= max(one[1], two[1])
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    assert not root.findall(".//s:text", NS)


@pytest.mark.parametrize(
    "group,pair", [("27770", "HD"), ("27772", "HM"), ("27774", "DM")]
)
@pytest.mark.parametrize("beta", [21, 45, 66, 0.5, 89.5])
def test_named_angles_preserve_vertices_across_all_ray_orders(group, pair, beta):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    rays = {
        "HD": "высотой CH и биссектрисой CD",
        "HM": "высотой CH и медианой CM",
        "DM": "биссектрисой CD и медианой CM",
    }[pair]
    section(ctx, "condition")["html"] = (
        "<p>"
        + str(
            __import__("bs4")
            .BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
            .img
        )
        + f"Острый угол B прямоугольного треугольника ABC равен {beta}°. Найдите угол между {rays}, проведенными из вершины прямого угла C. Ответ дайте в градусах.</p>"
    )
    result = plan(case, ctx)
    model = read_context(ctx)
    assert model.b == beta and model.a == 90 - beta
    verify(solution_html(result), geometry_values(90 - beta))
    specs = get_handler(GROUPS[group]["rule"]).diagram_specs(ctx)
    assert len(specs) == (1 if beta <= 45 else 0)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("group,max_phi", [("27771", 45), ("27773", 90), ("27775", 45)])
@pytest.mark.parametrize("mode", ["zero", "near_bound", "beyond_bound"])
def test_inverse_zero_fractional_and_degenerate_boundaries(group, max_phi, mode):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])

    soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
    # The parent uses a plain numeric token, while native children also cover LaTeX spans.
    old = {"27771": "21", "27773": "40", "27775": "14"}[group]
    value = 0 if mode == "zero" else max_phi - 0.5 if mode == "near_bound" else max_phi
    section(ctx, "condition")["html"] = str(soup).replace(old + "°", str(value) + "°")
    if mode == "beyond_bound":
        with pytest.raises(ContentPlanError):
            plan(case, ctx)
        return
    model = read_context(ctx)
    verify(solution_html(plan(case, ctx)), geometry_values(float(model.a)))
    if mode == "zero":
        html = solution_html(plan(case, ctx))
        assert "совпадают" in html and "В прямоугольном треугольнике CHM" not in html


def test_registered_bisector_rule_rejects_a_median_question():
    case = next(c for c in CASES if c["task"] == "27770")
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = (
        section(ctx, "condition")["html"]
        .replace("бис­сек­три­сой", "медианой")
        .replace('"CD"', '"CM"')
        .replace(">CD<", ">CM<")
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
