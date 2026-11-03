"""Verify line-ray branches against independent coordinates, never stored answers."""

import itertools
import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from height_bisector_cases import CASES, PARENTS, parent_html, plan, section
from test_altitude_quad_preparation import angle
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.height_bisector_figures import (
    SOURCE,
    selection,
    source_bytes,
)

RULE = "general-triangle-27767-altitude-bisector-intersection"
FRAMES = ["".join(p) for p in itertools.permutations("ABC")]


def synthetic(theta=26, frame="ABC", lines=True):
    case = PARENTS["27767"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    a, b, c = frame
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC {c}H — высота, {a}D — биссектриса, "
        f"O — точка пересечения {'прямых ' if lines else ''}{c}H и {a}D, "
        f"угол {b}{a}D равен {theta}°. Найдите угол {a}O{c}. Ответ дайте в градусах.</p>"
    )
    return case, ctx


def check_rows(html, model):
    theta = float(model.theta)
    values = {
        "HAO": theta,
        "BAD": theta,
        "AHO": 90,
        "AOH": 90 - theta,
        "AOC": float(model.answer),
    }
    for length in [0.7, 1.3]:
        t = math.radians(theta)
        cx, cy = length * math.cos(2 * t), length * math.sin(2 * t)
        points = {
            "A": (0, 0),
            "B": (1, 0),
            "C": (cx, cy),
            "H": (cx, 0),
            "O": (cx, cx * math.tan(t)),
            "D": ((length + cx) / (length + 1), cy / (length + 1)),
        }
        for name, value in values.items():
            assert abs(angle(points, name) - value) < 1e-8, (name, theta)
    reverse = dict(zip(model.frame + "DHO", "ABCDHO"))
    rows = BeautifulSoup(html, "html.parser").select("center [data-inline-latex]")
    assert len(rows) == (5 if theta < 45 else 7)
    for row in rows:
        expression = re.sub(
            r"\\angle\s*([ABCDHO]{3})",
            lambda m: str(values["".join(reverse[n] for n in m[1])]),
            row["data-inline-latex"],
        ).replace(r"^{\circ}", "")
        sides = [TrigonometricParser(s).parse().value for s in expression.split("=")]
        assert len(sides) >= 2 and all(
            abs(float(s - sides[0])) < 1e-9 for s in sides
        ), expression


@pytest.mark.parametrize(
    "case,expected",
    list(zip(CASES, ["116", "24", "128", "123"])),
    ids=[c["task"] for c in CASES],
)
def test_native_preparation_corrects_wrong_ray_answer_and_preserves_text(
    case, expected
):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert result.answer == expected and ctx == before
    if case["task"] == "47567":
        assert "156" in section(ctx, "answer")["html"] and result.answer == "24"
    model = selection(ctx)[0]
    text = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").get_text()
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert (
        BeautifulSoup(section(ctx, "condition")["html"], "html.parser").get_text()
        == text
    )
    if expected != "24":
        assert section(ctx, "condition") == section(before, "condition")
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("frame", FRAMES)
@pytest.mark.parametrize("theta", [12, 26, 38, 52, 66, 78])
def test_both_ray_orders_all_vertex_frames_and_formula_steps(frame, theta):
    case, ctx = synthetic(theta, frame)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == str(90 + theta if theta < 45 else 90 - theta)
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("frame", FRAMES)
def test_external_svg_preserves_perpendicularity_bisection_and_target_rays(frame):
    _, ctx = synthetic(66, frame)
    root = ET.fromstring(selection(ctx)[-1]["svg_text"])
    elements = {e.get("id"): e for e in root if e.get("id")}

    def ends(name):
        e = elements[name]
        return [
            tuple(float(e.get(axis + str(i))) for axis in ["x", "y"]) for i in [1, 2]
        ]

    a, b = ends("AB")
    c, h = ends("CH")
    _, d = ends("AD")
    _, o = ends("AO")
    points = dict(zip("ABCDHO", [a, b, c, d, h, o]))
    assert abs(angle(points, "BAD") - 66) < 1e-4
    assert abs(angle(points, "DAC") - 66) < 1e-4
    assert abs(angle(points, "AHC") - 90) < 1e-4
    assert abs(angle(points, "AOC") - 24) < 1e-4
    assert h[0] < a[0] and o[1] > h[1] > c[1]
    assert all(elements[n].get("stroke-dasharray") == "4 4" for n in ["AH", "HO", "AO"])
    assert {"right-H", "bisected-0", "bisected-1"} <= elements.keys()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_unknown_facts_are_never_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "theta,lines", [(0, True), (45, True), (90, True), (110, True), (66, False)]
)
def test_degenerate_or_unsupported_segment_intersections_fail_closed(theta, lines):
    case, ctx = synthetic(theta, lines=lines)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        ("CH — высота", "AH — высота"),
        ("AD — биссектриса", "AD — внешняя биссектриса"),
        ("прямых CH и AD", "прямых CH и BD"),
        ("угол BAD", "угол BCD"),
        ("угол AOC", "угол AOH"),
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
    "theta,frame,lost",
    [
        (26, "ABC", False),
        (66, "ABC", False),
        (26, "CAB", False),
        (66, "CAB", False),
        (66, "CAB", True),
    ],
)
def test_local_frozen_roundtrip_checks_real_ids_and_condition_readback(
    theta, frame, lost
):
    case, ctx = synthetic(theta, frame)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    kwargs = {"parent_solution_html": parent_html("27767")}
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
    assert len(gateway.uploads) == int(theta > 45 or frame != "ABC")
    if not lost:
        assert (
            _apply_record(gateway, record, SOURCE, RULE, **kwargs)["status"]
            == "already_complete"
        )


def test_changed_parent_method_is_rejected():
    with pytest.raises(ContentPlanError):
        plan(CASES[0], parent=parent_html("27767") + "<p>Другой способ</p>")


@pytest.mark.parametrize(
    "theta", ["45{,}0000000000000000001", "89{,}999999999999999999"]
)
def test_unrepresentable_external_geometry_is_rejected(theta):
    case, ctx = synthetic(theta)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_source_pin_is_packaged():
    assert source_bytes(SOURCE).lstrip().startswith((b"<?xml", b"<svg"))


@pytest.mark.parametrize("theta,expected", [("26{,}5", "116,5"), ("66{,}5", "23,5")])
def test_exact_half_degree_values(theta, expected):
    case, ctx = synthetic(theta)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)


@pytest.mark.parametrize("given", ["BAD", "DAB", "CAD", "DAC"])
@pytest.mark.parametrize("target", ["AOC", "COA"])
def test_equivalent_bisected_angles_and_target_ray_order(given, target):
    case, ctx = synthetic()
    condition = section(ctx, "condition")
    condition["html"] = (
        condition["html"]
        .replace("угол BAD", "угол " + given)
        .replace("угол AOC", "угол " + target)
    )
    assert plan(case, ctx).answer == "116"


@pytest.mark.parametrize("change", ["extra", "unknown", "reference", "url"])
def test_unreviewed_condition_assets_are_rejected(change):
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
