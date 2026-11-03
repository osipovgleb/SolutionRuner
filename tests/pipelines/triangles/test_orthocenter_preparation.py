"""Verify actual altitude rays against independent line intersections."""

import itertools
import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from orthocenter_cases import CASES, PARENTS, parent_html, plan, section
from test_altitude_quad_preparation import angle
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.orthocenter_figures import (
    SOURCE,
    selection,
    source_bytes,
)

RULE = "general-triangle-27779-orthocenter-altitudes-angle"
FRAMES = ["".join(p) for p in itertools.permutations("ABC")]
CONFIGURATIONS = [(60, 82), (21, 11), (120, 20), (20, 120), (30, 60)]


def synthetic(alpha=60, beta=82, frame="ABC"):
    case = PARENTS["27779"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    a, b, c = frame
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC угол {a} равен {alpha}°, угол {b} равен {beta}°. {a}D, {b}E и {c}F — высоты, пересекающиеся в точке O. Найдите угол {a}OF. Ответ дайте в градусах.</p>"
    )
    return case, ctx


def cross(u, v):
    return u[0] * v[1] - u[1] * v[0]


def intersect(p, u, q, v):
    difference = (q[0] - p[0], q[1] - p[1])
    t = cross(difference, v) / cross(u, v)
    return p[0] + t * u[0], p[1] + t * u[1]


def coordinates(alpha, beta):
    a, b = math.radians(float(alpha)), math.radians(float(beta))
    origin, base = (0, 0), (7, 0)
    c = intersect(origin, (math.cos(a), math.sin(a)), base, (-math.cos(b), math.sin(b)))
    bc, ac = (c[0] - 7, c[1]), c
    altitude_a, altitude_b = (-bc[1], bc[0]), (-ac[1], ac[0])
    d = intersect(origin, altitude_a, base, bc)
    e = intersect(base, altitude_b, origin, ac)
    f = intersect(c, (0, 1), origin, (1, 0))
    o = intersect(origin, altitude_a, c, (0, 1))
    return dict(zip("ABCDEFO", [origin, base, c, d, e, f, o]))


def check_rows(html, model):
    points = coordinates(model.alpha, model.beta)
    complement = abs(90 - model.beta)
    values = {"B": model.beta, "AFO": 90, "OAF": complement, "AOF": 90 - complement}
    for name in ["AFO", "OAF", "AOF"]:
        assert abs(angle(points, name) - float(values[name])) < 1e-8
    assert abs(angle(points, "ABC") - float(model.beta)) < 1e-8
    reverse = dict(zip(model.frame + "DEFO", "ABCDEFO"))
    rows = BeautifulSoup(html, "html.parser").select("center [data-inline-latex]")
    assert len(rows) == 7
    for row in rows:
        expression = re.sub(
            r"\\angle\s*([ABCDEFO]{3}|[ABC])",
            lambda m: "(" + sp.latex(values["".join(reverse[n] for n in m[1])]) + ")",
            row["data-inline-latex"],
        ).replace(r"^{\circ}", "")
        sides = [TrigonometricParser(s).parse().value for s in expression.split("=")]
        assert len(sides) == 2 and sp.simplify(sides[0] - sides[1]) == 0, expression


def check_svg(diagram, model):
    root = ET.fromstring(diagram["svg_text"])
    identifiers = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(identifiers) == len(set(identifiers))
    elements = {e.get("id"): e for e in root if e.get("id")}

    def ends(name):
        e = elements[name]
        return [
            tuple(float(e.get(axis + str(i))) for axis in ["x", "y"]) for i in [1, 2]
        ]

    a, b = ends("AB")
    c, _ = ends("CA")
    _, d = ends("AD")
    _, e = ends("BE")
    _, f = ends("CF")
    extensions = [
        item
        for name, item in elements.items()
        if name.startswith("altitude-extension-")
    ]
    if model.gamma == 90:
        o = c
        assert math.dist(c, d) < 1e-5 and math.dist(c, e) < 1e-5
        assert len([n for n in identifiers if n.startswith("merged-C-")]) == 6
    else:
        assert extensions
        o = tuple(float(extensions[0].get(axis + "2")) for axis in ["x", "y"])
        for item in extensions:
            assert (
                math.dist(o, tuple(float(item.get(axis + "2")) for axis in ["x", "y"]))
                < 1e-5
            )
    points = dict(zip("ABCDEFO", [a, b, c, d, e, f, o]))
    assert abs(angle(points, "BAC") - float(model.alpha)) < 1e-3
    assert abs(angle(points, "ABC") - float(model.beta)) < 1e-3
    assert abs(angle(points, "AOF") - float(model.answer)) < 1e-3
    for origin, foot, side in [("A", "D", "BC"), ("B", "E", "CA"), ("C", "F", "AB")]:
        u = tuple(points[origin][i] - points[foot][i] for i in [0, 1])
        v = tuple(points[side[0]][i] - points[side[1]][i] for i in [0, 1])
        assert (
            abs(sum(x * y for x, y in zip(u, v)) / (math.hypot(*u) * math.hypot(*v)))
            < 1e-5
        )
    assert {
        "right-D",
        "right-E",
        "right-F",
        *("label-" + n for n in "ABCDEFO"),
    } <= elements.keys()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_correct_external_diagrams_and_ignore_stored_results(case):
    ctx = deepcopy(case["context"])
    condition = deepcopy(section(ctx, "condition"))
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    for key in ["answer", "solution"]:
        section(ctx, key)["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    model, *_, diagram = selection(ctx)
    result = plan(case, ctx)
    assert result.answer == expected and ctx == before
    if diagram:
        check_svg(diagram, model)
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    if not diagram:
        assert section(ctx, "condition") == condition
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("frame", FRAMES)
@pytest.mark.parametrize("alpha,beta", CONFIGURATIONS)
def test_all_vertex_frames_and_orthocenter_topologies(frame, alpha, beta):
    case, ctx = synthetic(alpha, beta, frame)
    model, *_, diagram = selection(ctx)
    result = plan(case, ctx)
    assert result.answer == str(min(beta, 180 - beta))
    if max(alpha, beta, 180 - alpha - beta) >= 90:
        check_svg(diagram, model)
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_facts_are_never_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "alpha,beta", [(0, 40), (40, 0), (90, 40), (40, 90), (100, 80), (120, 90)]
)
def test_degenerate_triangle_or_requested_rays_fail_closed(alpha, beta):
    case, ctx = synthetic(alpha, beta)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        ("AD, BE", "BD, BE"),
        ("CF — высоты", "AF — высоты"),
        ("точке O", "точке D"),
        ("угол AOF", "угол AOC"),
        ("угол B равен", "угол C равен"),
    ],
)
def test_changed_point_roles_are_rejected(old, new):
    case, ctx = synthetic()
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "alpha,beta,frame,lost",
    [
        (60, 82, "ABC", False),
        (21, 11, "ABC", False),
        (120, 20, "CAB", False),
        (20, 120, "ABC", False),
        (30, 60, "CAB", False),
        (21, 11, "CAB", True),
    ],
)
def test_local_frozen_roundtrip_validates_real_ids_and_authoritative_readback(
    alpha, beta, frame, lost
):
    case, ctx = synthetic(alpha, beta, frame)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    kwargs = {"parent_solution_html": parent_html("27779")}
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        SOURCE,
        RULE,
        **kwargs,
    )
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, SOURCE, RULE, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(
        frame != "ABC" or max(alpha, beta, 180 - alpha - beta) >= 90
    )
    if not lost:
        assert (
            _apply_record(gateway, record, SOURCE, RULE, **kwargs)["status"]
            == "already_complete"
        )


def test_changed_parent_method_is_rejected():
    with pytest.raises(ContentPlanError):
        plan(CASES[0], parent=parent_html("27779") + "<p>Другой способ</p>")


@pytest.mark.parametrize("change", ["extra", "unknown", "reference", "url"])
def test_unreviewed_assets_fail_closed(change):
    case, ctx = synthetic()
    asset = ctx["normalized_content"]["assets"][0]
    if change == "extra":
        ctx["normalized_content"]["assets"].append({"asset_key": "image_2"})
    elif change == "unknown":
        asset["asset_id"] = "unknown"
        asset["url"] = "/assets/unknown"
    elif change == "reference":
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            SOURCE, "unknown"
        )
    else:
        asset["url"] = "/assets/unknown"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "alpha,beta",
    [
        ("0{,}0000000000000000001", 120),
        (120, "0{,}0000000000000000001"),
        ("90{,}000000000000000001", 30),
        (30, "59{,}999999999999999999"),
    ],
)
def test_unrepresentable_geometry_is_rejected(alpha, beta):
    case, ctx = synthetic(alpha, beta)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_source_pin_is_packaged():
    assert source_bytes(SOURCE).lstrip().startswith((b"<?xml", b"<svg"))


@pytest.mark.parametrize(
    "alpha,beta,expected",
    [
        ("21{,}5", "11{,}5", "11,5"),
        (20, "120{,}5", "59,5"),
        ("30{,}5", "59{,}5", "59,5"),
    ],
)
def test_exact_half_degrees_and_right_third_vertex(alpha, beta, expected):
    case, ctx = synthetic(alpha, beta)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)


@pytest.mark.parametrize("change", ["facts", "segments"])
def test_equivalent_fact_and_segment_orders(change):
    case, ctx = synthetic(20, 120)
    condition = section(ctx, "condition")
    if change == "facts":
        condition["html"] = condition["html"].replace(
            "угол A равен 20°, угол B равен 120°", "угол B равен 120°, угол A равен 20°"
        )
    else:
        condition["html"] = (
            condition["html"]
            .replace("AD, BE и CF", "DA, EB и FC")
            .replace("угол AOF", "угол FOA")
        )
    assert plan(case, ctx).answer == "60"
