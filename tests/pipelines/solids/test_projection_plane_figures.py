"""Exact source reuse, proof roles and mathematical replacement scenes."""

import hashlib
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from projection_plane_source_cases import CASES, GROUPS, plan, read
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import box_parallel_plane_svg as drawing
from solution_runner.pipelines.solids.spatial_distance_model import condition_text


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_scenes_keep_methods_order_and_quantities(case):
    result = plan(case)
    html = solution_html(result)
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == (
        2 if case["task"] == "507496" else 1
    )
    assert not get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    if case["group"] == "701579":
        assert (
            html.index("высота тетраэдра")
            < html.index("теореме Фалеса")
            < html.index("Ещё раз используем")
        )
        assert r"\cos\angle AA_2C" in html and r"CA_1^2=" in html
    elif case["group"] == "484562":
        if case["task"] == "507496":
            assert (
                html.index("По теореме косинусов")
                < html.index("Другой способ")
                < html.index("ребро куба за единицу")
            )
            assert result.answer.startswith(r"\arccos")
        else:
            assert "Другой способ" not in html
            assert not result.answer.startswith(r"\arccos")
    elif case["group"] == "507581":
        assert html.index("прямоугольность параллелепипеда не требуется") < html.index(
            "трёх перпендикулярах"
        )
    else:
        assert {
            "length": "равносторонний",
            "area": "Площадь боковой поверхности",
            "line_angles": "по трём сторонам",
        }[read(case["context"]).names[0]] in html
        assert "DHD₁" in html


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_the_correct_geometric_construction(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    html = solution_html(result)
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == 1
    if case["group"] == "484562":
        assert ("середина A₁B" if case["task"] == "484562" else "середина AD₁") in html
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["task"] != "701646"], ids=lambda c: c["task"]
)
def test_unknown_assets_and_parent_asset_drift_refuse(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    asset["asset_id"] = "00000000-0000-4000-8000-000000000001"
    for s in ctx["normalized_content"]["sections"]:
        s["html"] = s["html"].replace(old, asset["asset_id"])
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_assets=())


@pytest.mark.parametrize("task", ("507581", "507592"))
@pytest.mark.parametrize("dims", ((3, 5, 7), (8, 12, 8), (9, 9, 6)))
def test_replacement_svg_foot_edges_labels_and_section_are_consistent(task, dims):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    for name, val in zip(("AB", "BC", "CC_1"), dims, strict=True):
        raw = re.sub(r"\b" + name + r"\s*=\s*.+?(?=,|\.)", name + " = " + str(val), raw)
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    m = read(ctx)
    (spec,) = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)
    assert spec["sha256"] == hashlib.sha256(spec["svg_text"].encode()).hexdigest()
    root = ET.fromstring(spec["svg_text"])
    ns = "{http://www.w3.org/2000/svg}"
    assert sorted(e.text for e in root.findall(ns + "text")) == sorted(map(str, dims))
    vertices, _ = drawing.projection(m, drawing.template(m.names[0]))
    foot = vertices["E"]
    start, end = ("B", "A_1") if task == "507581" else ("A", "C")
    u, v = (sp.Matrix(vertices[n]) - sp.Matrix(foot) for n in (start, end))
    assert abs(float(sp.det(sp.Matrix.hstack(u, v)))) < 1e-7
    for a in ("A", "D") if task == "507581" else ("D", "D_1"):
        line = root.find(f"{ns}line[@id='helper-{a}-E']")
        assert line is not None
        assert abs(float(line.get("x2")) - foot[0]) < 1e-6
        assert abs(float(line.get("y2")) - foot[1]) < 1e-6
    polygon = root.find(f"{ns}polygon[@id='section']")
    xy = [[float(x) for x in pair.split(",")] for pair in polygon.get("points").split()]
    area2 = abs(
        sum(
            xy[i][0] * xy[(i + 1) % 3][1] - xy[i][1] * xy[(i + 1) % 3][0]
            for i in range(3)
        )
    )
    assert area2 > 100
    with pytest.raises(ContentPlanError):
        plan(case, ctx, generated_solution_assets=())


def test_tetra_point_crossing_center_does_not_reuse_wrong_order_scene():
    case = next(c for c in CASES if c["task"] == "701579")
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None).replace(
        r"\colon", ":"
    )
    raw = raw.replace("AM = AK = 6", "AM = AK = 8").replace("16: 9", "9: 16")
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    assert read(ctx).q["center_side"] < 0
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_changed_reviewed_projection_template_refuses(monkeypatch):
    monkeypatch.setattr(drawing, "TEMPLATE_SHA256", "0" * 64)
    with pytest.raises(ContentPlanError):
        drawing.template("side")
