"""Validate diagram vertex roles, equal sides, exterior rays, arcs and replay."""

import itertools
import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from isosceles_angle_cases import PARENTS, plan, section
from test_two_ray_source_methods import replay

from solution_runner.pipelines.triangles.isosceles.angle_figures import (
    DIFFERENCE,
    EXTERIOR_BASE,
    EXTERIOR_GIVEN,
    EXTERIOR_VERTEX,
    LARGER,
    selection,
    source_bytes,
)
from solution_runner.pipelines.triangles.isosceles.area_figures import (
    ACUTE,
    NARROW,
    OBTUSE,
)
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag


def _endpoint(line, index):
    return tuple(float(line.get(axis + str(index))) for axis in ("x", "y"))


def _points(root, model, plain):
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    if plain:
        p, q = model.base_vertices
        return {
            p: _endpoint(lines["side-left"], 1),
            q: _endpoint(lines["side-right"], 1),
            model.apex: _endpoint(lines["side-left"], 2),
        }
    points = {}
    for vertex in "ABC":
        incident = [
            e
            for name, e in lines.items()
            if name and name.startswith("side-") and vertex in name[5:]
        ]
        assert len(incident) == 2
        common = {_endpoint(incident[0], 1), _endpoint(incident[0], 2)} & {
            _endpoint(incident[1], 1),
            _endpoint(incident[1], 2),
        }
        assert len(common) == 1
        points[vertex] = common.pop()
    return points


def _geometry(root, model, plain):
    points = _points(root, model, plain)
    p, q = model.base_vertices
    c = points[model.apex]
    u, v = (
        tuple(points[p][i] - c[i] for i in (0, 1)),
        tuple(points[q][i] - c[i] for i in (0, 1)),
    )
    assert math.hypot(*u) == pytest.approx(math.hypot(*v), abs=2e-6)
    cosine = sum(u[i] * v[i] for i in (0, 1)) / (math.hypot(*u) * math.hypot(*v))
    assert math.degrees(math.acos(max(-1, min(1, cosine)))) == pytest.approx(
        float(model.apex_angle), abs=2e-5
    )
    if not plain:
        ray = next(
            e for e in root.findall(_tag("line")) if e.get("id") == "exterior-ray"
        )
        vertex = (
            model.apex
            if model.given_kind == "external_vertex"
            else model.given_vertex
            if model.given_kind == "external_base"
            else model.requested[1]
        )
        opposite = (
            next(v for v in model.base_vertices if v != model.requested)
            if model.given_kind == "external_vertex"
            else next(v for v in model.base_vertices if v != vertex)
        )
        center = points[vertex]
        assert _endpoint(ray, 1) == center
        a = tuple(_endpoint(ray, 2)[i] - center[i] for i in (0, 1))
        b = tuple(points[opposite][i] - center[i] for i in (0, 1))
        assert (
            abs(a[0] * b[1] - a[1] * b[0]) < 1e-4
            and sum(a[i] * b[i] for i in (0, 1)) < 0
        )
        cyan = [e for e in root.findall(_tag("path")) if e.get("stroke") == "#007EA5"]
        assert len(cyan) == (0 if model.requested_kind == "external_base" else 2)
    left, top, width, height = map(float, root.get("viewBox").split())
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    for g in root.findall(_tag("g")):
        x, y, w, h = _bounds(g)
        dx, dy = map(
            float,
            re.fullmatch(r"translate\(([^ ]+) ([^)]+)\)", g.get("transform")).groups(),
        )
        assert left - 1e-5 <= x + dx and top - 1e-5 <= y + dy
        assert x + dx + w <= left + width + 1e-5 and y + dy + h <= top + height + 1e-5


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize(
    "kind", ["plain", "exterior_requested", "external_base", "external_vertex"]
)
@pytest.mark.parametrize("gamma", [60, 90, 150, 170])
def test_all_frames_topologies_and_flat_obtuse_angles_prepare_and_replay(
    frame, kind, gamma
):
    p, q, r = frame
    group = {
        "plain": "27745",
        "exterior_requested": "27746",
        "external_base": "27747",
        "external_vertex": "27748",
    }[kind]
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    equal = p + r + "=" + q + r
    given = (
        equal + f", угол {r} равен {gamma}°"
        if kind in {"plain", "exterior_requested"}
        else equal
        + f". Внешний угол при вершине {q if kind == 'external_base' else r} равен {(180 + gamma) // 2 if kind == 'external_base' else 180 - gamma}°"
    )
    request = (
        "внешний угол " + r + q + "D"
        if kind == "exterior_requested"
        else "угол " + (r if kind == "external_base" else q)
    )
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC {given}. Найдите {request}. Ответ дайте в градусах.</p>"
    )
    model, _, _, _, source, diagram = selection(ctx)
    assert model.apex_angle == gamma
    if diagram:
        root = ET.fromstring(diagram["svg_text"])
        custom = any(e.get("id") for e in root.findall(_tag("line")))
        if custom:
            _geometry(root, model, kind == "plain")
        else:
            assert (
                source == EXTERIOR_BASE
                and model.apex == "C"
                and model.requested[1] == "B"
                and model.topology == 1
            )
            assert [ET.tostring(e) for e in root] == [
                ET.tostring(e) for e in ET.fromstring(source_bytes(source))
            ]
    elif kind == "plain":
        assert model.apex == "C" and source in (
            {ACUTE, NARROW, LARGER} if model.topology == 1 else {OBTUSE, DIFFERENCE}
        )
    elif kind == "external_base":
        assert (
            model.apex == "C"
            and model.given_vertex == "B"
            and model.topology == 1
            and source == EXTERIOR_GIVEN
        )
    else:
        assert (
            kind == "external_vertex"
            and model.apex == "B"
            and model.requested == "C"
            and model.topology == 1
            and source == EXTERIOR_VERTEX
        )
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "source", [EXTERIOR_BASE, EXTERIOR_GIVEN, EXTERIOR_VERTEX, LARGER, DIFFERENCE]
)
def test_original_sources_are_present_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))
