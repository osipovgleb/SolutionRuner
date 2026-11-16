"""Native and raster primitives must preserve their stationary points and intervals."""

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from test_raster_rays import Gateway as RayGateway

from solution_runner.pipelines.calculus import (
    graph_stationary,
    primitive_runner,
    primitive_svg,
    raster_primitive,
)
from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)

ROOT = Path(__file__).parent / "fixtures/primitive_rasters"
CASES = {
    str(c["source_problem_id"]): c
    for c in json.loads((ROOT / "contexts.json").read_text())
}
RULE = "calculus-raster-primitive-zeros"


class Gateway(RayGateway):
    def __init__(self, context):
        self.context = deepcopy(context)
        asset = context["normalized_content"]["assets"][0]
        task = str(context["source_problem_id"])
        path = ROOT / (task + (".svg" if task == "323153" else ".png"))
        self.files = {asset["asset_id"]: path.read_bytes()}
        self.uploads = 0
        self.writes = 0


@pytest.mark.parametrize(
    "task,expected", [("323117", 7), ("323119", 7), ("323085", 11)]
)
def test_raster_prepare_highlight_upload_readback_and_no_duplicates(task, expected):
    context = CASES[task]
    gateway = Gateway(context)
    before = deepcopy(context)
    record = _prepared_record(gateway, context, None, RULE)
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == str(expected)
    assert len(record["generated_diagrams"]) == 2
    assert gateway.context == before and gateway.uploads == gateway.writes == 0
    condition, solution = [
        ET.fromstring(s["svg_text"]) for s in record["generated_diagrams"]
    ]
    ns = raster_primitive.NS
    assert condition.find(ns + 'g[@data-runner-diagram="stationary_points"]') is None
    highlight = solution.find(ns + 'g[@data-runner-diagram="stationary_points"]')
    assert len(highlight.findall(ns + "circle")) == expected
    assert len(highlight.findall(ns + "polyline")) == 2
    assert condition.find(ns + 'path[@data-primitive-curve="true"]').get(
        "d"
    ) == solution.find(ns + 'path[@data-primitive-curve="true"]').get("d")
    plan_solution = next(
        t["value"]["html"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert "Их количество — " + str(expected) in plan_solution
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(plan_solution, "html.parser").select(
            "[data-inline-latex]"
        )
    ]
    assert (
        any("F'(x)=0" in formula for formula in formulas) and "N_{" not in plan_solution
    )
    result = _apply_record(gateway, record, None, RULE)
    assert result["status"] == "applied", result
    assert gateway.uploads == 2 and gateway.writes == 1
    next_record = _prepared_record(gateway, gateway.context, None, RULE)
    assert (
        next_record["status"] == "prepared" and next_record["transformations"] == []
    ), next_record
    assert (
        _apply_record(gateway, next_record, None, RULE)["status"] == "already_complete"
    )
    assert gateway.uploads == 2 and gateway.writes == 1


@pytest.mark.parametrize("task", ["323147", "323155"])
def test_uncertain_extremum_at_interval_boundary_is_not_silently_counted(task):
    gateway = Gateway(CASES[task])
    record = _prepared_record(gateway, CASES[task], None, RULE)
    assert record["status"] != "prepared"
    assert "boundary" in record["message"]
    assert gateway.uploads == gateway.writes == 0


def test_unknown_native_svg_is_read_without_replacing_the_original():
    context = CASES["323153"]
    gateway = Gateway(context)
    before = deepcopy(gateway.files)
    record = _prepared_record(gateway, context, None, RULE)
    assert record["status"] == "prepared", record
    assert len(record["generated_diagrams"]) == 1
    assert not any(
        t["transformation_target_id"] in ("asset:image_1", "section:condition:1")
        for t in record["transformations"]
    )
    assert gateway.files == before
    result = _apply_record(gateway, record, None, RULE)
    assert result["status"] == "applied", result
    assert (
        _prepared_record(gateway, gateway.context, None, RULE)["transformations"] == []
    )
    for key, data in before.items():
        assert gateway.files[key] == data


def test_stationary_inflection_is_not_incorrectly_called_an_extremum():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path stroke="#143B8F" d="M10 55 C36.6666667 45 63.3333333 55 90 45"/></svg>'
    q = SimpleNamespace(
        kind="primitive",
        domain=graph_stationary.interval("(0;1)"),
        interval=graph_stationary.interval("[0.1;0.9]"),
    )
    _entry, points = primitive_svg.read(svg, q)
    assert len(points) == 1 and points[0]["kind"] == "stationary"
    html = primitive_runner.proof(q, points)
    assert "стационарные точки без экстремума" in html
    assert "Их количество — 1" in html


def test_smoothing_changes_only_vertex_neighborhoods_and_preserves_graph_ends():
    import numpy as np

    q, _, _ = primitive_runner._read(CASES["323117"])
    data = (ROOT / "323117.png").read_bytes()
    before = raster_primitive.recover(data, q, smooth_vertices=False)
    after = raster_primitive.recover(data, q)
    assert before["extrema"] == after["extrema"]
    assert after["diagnostics"]["vertex_smoothing"]["removed_knots"] > 0
    assert before["knots"][:2] == after["knots"][:2]
    assert before["knots"][-2:] == after["knots"][-2:]
    assert before["slopes"][:2] == after["slopes"][:2]
    assert before["slopes"][-2:] == after["slopes"][-2:]
    regions = after["diagnostics"]["vertex_smoothing"]["regions"]
    retained = {p[0]: (p, slope) for p, slope in zip(after["knots"], after["slopes"])}
    for point, slope in zip(before["knots"], before["slopes"]):
        if not any(lo < point[0] < hi for lo, hi in regions):
            assert retained[point[0]] == (point, slope)
    knots = np.array(after["knots"])
    slopes = np.array(after["slopes"])
    hard = tuple(
        i for i, p in enumerate(knots) if any(p[0] == e["x"] for e in after["extrema"])
    )
    raster_primitive._verify_fit(knots, slopes, hard)


def test_already_downloaded_png_needs_no_extra_source_asset_metadata_permission():
    class RestrictedGateway(Gateway):
        def get_source_asset(self, asset_id):
            if not asset_id.startswith("uploaded-"):
                raise PermissionError("source metadata is unavailable")
            return super().get_source_asset(asset_id)

    gateway = RestrictedGateway(CASES["323117"])
    record = _prepared_record(gateway, gateway.context, None, RULE)
    assert record["status"] == "prepared", record
    result = _apply_record(gateway, record, None, RULE)
    assert result["status"] == "applied", result
    assert gateway.uploads == 2 and gateway.writes == 1


def test_source_apex_next_to_grid_line_does_not_follow_grid_intersection():
    import io

    import numpy as np
    from PIL import Image

    q, _, _ = primitive_runner._read(CASES["323117"])
    data = (ROOT / "323117-source.png").read_bytes()
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    trace, grid = raster_primitive._trace(np.asarray(background), q)
    pixels = trace * [grid.vertical.step, -grid.horizontal.step]
    pixels += [grid.vertical_axis_x, grid.horizontal_axis_y]
    # The true ink goes through y=57..60 here. The old guide incorrectly
    # selected the grid crossing at y=76, then interpolated a false steep drop.
    columns = np.rint(pixels[:, 0])
    apex = pixels[(columns >= 43) & (columns <= 45)]
    assert len(apex) == 3
    assert np.all((apex[:, 1] >= 56) & (apex[:, 1] <= 61))
    model = raster_primitive.recover(data, q)
    peak = next(
        e for e in model["extrema"] if e["kind"] == "max" and -1.2 < e["x"] < -0.9
    )
    assert -1.08 < peak["x"] < -1.0
    assert (
        sum(
            float(q.interval.lower) <= e["x"] <= float(q.interval.upper)
            for e in model["extrema"]
        )
        == 7
    )
