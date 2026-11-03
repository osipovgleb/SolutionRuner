"""Parse actual SVG strokes to check lengths, incidence, right angles and labels."""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from fractions import Fraction
from itertools import pairwise

import pytest
from midpoint_source_cases import replay, section, solution_html
from quantity_source_cases import CASES, plan
from test_parallelogram_quantity_methods import verify
from test_parallelogram_quantity_model import read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_figures import (
    diagram_specs,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_model import (
    read_question,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_sources import (
    source_bytes,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_svg import (
    DETAIL,
    figure_svg,
)
from solution_runner.pipelines.triangles.general.angle_label_positions import (
    _intersects,
)
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag

DYNAMIC = [c for c in CASES if c["group"] in {"27436", "27611"}]


def vector(p, q):
    return q[0] - p[0], q[1] - p[1]


def coordinates(root):
    points, segments = {}, []
    for line in root.findall(_tag("line")):
        ends = [
            tuple(float(line.get(axis + str(i))) for axis in ["x", "y"]) for i in (1, 2)
        ]
        segments.append(ends)
        identifier = line.get("id", "")
        if identifier.startswith(("side-", "height-")):
            pair = identifier.split("-")[1]
            for name, point in zip(pair, ends):
                if name in points:
                    assert points[name] == pytest.approx(point, abs=2e-6)
                points[name] = point
    for polyline in root.findall(_tag("polyline")):
        vertices = [
            tuple(map(float, p.split(","))) for p in polyline.get("points").split()
        ]
        segments.extend(pairwise(vertices))
    return points, segments


def check(m, svg):
    root = ET.fromstring(svg)
    points, segments = coordinates(root)
    ids = [n.get("id") for n in root.iter() if n.get("id")]
    assert len(ids) == len(set(ids))
    ab, ad = vector(points["A"], points["B"]), vector(points["A"], points["D"])
    scale = math.hypot(*ab) / float(m.a)
    assert math.hypot(*ad) / scale == pytest.approx(float(m.b), abs=2e-5)
    assert tuple(
        points["B"][i] + points["D"][i] - points["A"][i] for i in (0, 1)
    ) == pytest.approx(points["C"], abs=2e-6)
    assert abs(ab[0] * ad[1] - ab[1] * ad[0]) / (
        math.hypot(*ab) * math.hypot(*ad)
    ) == pytest.approx(float(m.sine), abs=1e-6)
    heights = (
        [("D", "H", "AB", m.first_height), ("C", "K", "AD", m.second_height)]
        if m.mode == "sine"
        else [("B", "H", "AD", m.second_height), ("B", "G", "CD", m.first_height)]
    )
    for start, foot, base, expected in heights:
        u, v = (
            vector(points[start], points[foot]),
            vector(points[base[0]], points[base[1]]),
        )
        assert sum(u[i] * v[i] for i in (0, 1)) / (
            math.hypot(*u) * math.hypot(*v)
        ) == pytest.approx(0, abs=1e-6)
        assert math.hypot(*u) / scale == pytest.approx(float(expected), abs=2e-5)
        w = vector(points[base[0]], points[foot])
        assert abs(w[0] * v[1] - w[1] * v[0]) / math.hypot(*v) < 2e-6
    boxes = []
    for glyph in root.findall(_tag("g")):
        if not glyph.get("id", "").startswith("label-"):
            continue
        x, y, width, height = _bounds(glyph)
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([^ ]+) ([^)]+)\)", glyph.get("transform")
            ).groups(),
        )
        boxes.append((x + dx, y + dy, width, height))
    if m.mode == "transfer":
        expected = dict(
            zip(("AB", "AD", "BH", "BG"), (m.a, m.b, m.second_height, m.first_height))
        )
        for text in root.findall(_tag("text")):
            for segment in text.get(
                "data-segments", text.get("id").removeprefix("value-")
            ).split():
                assert Fraction(text.text.replace(",", ".")) == Fraction(
                    expected.pop(segment)
                )
            size = float(text.get("font-size"))
            boxes.append(
                (
                    float(text.get("x")),
                    float(text.get("y")) - 0.84 * size,
                    size * 0.5 * len(text.text) + 2,
                    size * 1.1,
                )
            )
        assert expected == {}
    for i, box in enumerate(boxes):
        assert not any(_intersects(p, q, box) for p, q in segments)
        x, y, w, h = box
        for bx, by, bw, bh in boxes[:i]:
            assert not (x < bx + bw and x + w > bx and y < by + bh and y + h > by)
    x, y, w, h = map(float, root.get("viewBox").split())
    assert all(
        x <= bx and y <= by and bx + bw <= x + w + 1e-5 and by + bh <= y + h + 1e-5
        for bx, by, bw, bh in boxes
    )
    return points


@pytest.mark.parametrize("case", DYNAMIC, ids=lambda c: c["task"])
def test_all_native_height_svgs_have_actual_geometry_and_legible_values(case):
    m = read(case["context"])
    svg = figure_svg(m)
    check(m, svg)
    assert svg == figure_svg(m)


@pytest.mark.parametrize(
    "mode,a,b,sine",
    [
        ("sine", 3, 5, r"\frac{4}{5}"),
        ("sine", 5, 3, r"\frac{4}{5}"),
        ("sine", 3, 5, "1"),
        ("transfer", 3, 5, "4"),
        ("transfer", 5, 3, "2"),
        ("transfer", 3, 5, "5"),
    ],
)
def test_endpoint_feet_swapped_sides_and_right_angle_strokes_do_not_collapse(
    mode, a, b, sine
):
    html = (
        f"<p>В параллелограмме ABCD AB={a}, AD={b}, \\sin A={sine}. Найдите большую высоту параллелограмма.</p>"
        if mode == "sine"
        else f"<p>Стороны параллелограмма равны {a} и {b}. Высота, опущенная на первую сторону, равна {sine}. Найдите высоту, опущенную на вторую сторону параллелограмма.</p>"
    )
    m = read_question(html)
    check(m, figure_svg(m))
    case = next(
        c for c in CASES if c["task"] == ("27436" if mode == "sine" else "27611")
    )
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = html
    section(ctx, "condition")["asset_keys"] = []
    if mode == "sine":
        ctx["normalized_content"]["assets"] = []
    result = plan(case, ctx)
    verify(solution_html(result), m)
    if mode == "transfer" and a > b:
        assert "Положение G на исходной схеме соответствует данным" in solution_html(
            result
        )
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


def test_compatible_numeric_parent_is_reused_and_not_regenerated():
    case = next(c for c in CASES if c["task"] == "27611")
    assert diagram_specs(case["context"]) == ()
    result = plan(case)
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )
    assert DETAIL in str(result.transformations)
    root = ET.fromstring(source_bytes(DETAIL))
    black = [e for e in root.findall(_tag("line")) if e.get("stroke") == "#000000"]
    vertices = {
        tuple(float(e.get(axis + str(i))) for axis in ("x", "y"))
        for e in black
        for i in (1, 2)
    }
    lower = sorted(p for p in vertices if p[1] == max(v[1] for v in vertices))
    upper = sorted(p for p in vertices if p[1] == min(v[1] for v in vertices))
    a, d = lower
    b, _ = upper
    scale = math.dist(a, d) / 15
    assert math.dist(a, b) / scale == pytest.approx(9, rel=2e-4)


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in {"27817", "27828", "27829"}],
    ids=lambda c: c["task"],
)
def test_new_rhombus_native_figures_are_reused_exactly_without_duplicates(case):
    context = deepcopy(case["context"])
    assets = deepcopy(context["normalized_content"]["assets"])
    assert diagram_specs(context) == ()
    assert source_bytes(assets[0]["asset_id"]).startswith(b"<?xml")
    result = plan(case, context)
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )
    replay(context, result.transformations)
    assert context["normalized_content"]["assets"] == assets
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize(
    "group",
    [
        "27436",
        "27611",
        "27612",
        "27613",
        "27614",
        "27615",
        "27616",
        "27817",
        "27828",
        "27829",
    ],
)
@pytest.mark.parametrize(
    "change", ["foreign", "url", "keys", "extra_image", "instruction"]
)
def test_foreign_assets_and_unreviewed_conditions_fail_before_svg_preparation(
    group, change
):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    content = ctx["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    if change == "foreign":
        content["assets"][0]["asset_id"] = "foreign"
    elif change == "url":
        content["assets"][0]["url"] += "?other"
    elif change == "keys":
        content["sections"][0]["asset_keys"] = ["foreign"]
    elif change == "extra_image":
        content["assets"].append(deepcopy(content["assets"][0]))
    else:
        condition["html"] += "<p>Округлите ответ до целого.</p>"
    with pytest.raises(ContentPlanError):
        diagram_specs(ctx)
