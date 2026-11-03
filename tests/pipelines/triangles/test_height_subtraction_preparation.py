"""Verify angle subtraction from complete native text and an audited external foot."""

import itertools
import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from height_subtraction_cases import CASES, PARENTS, parent_html, plan, section
from test_altitude_quad_preparation import angle
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.height_subtraction_figures import (
    SOURCE,
    selection,
    source_bytes,
)

RULE = "general-triangle-27757-altitude-angle"
FRAMES = ["".join(p) for p in itertools.permutations("ABC")]


def synthetic(frame="ABC", explicit=True, alpha=30, delta=22):
    case = PARENTS["27757"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    a, b, c = frame
    premise = f"угол {b} — тупой, " if explicit else ""
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC угол {a} равен {alpha}°, {premise}{c}H — высота, угол {b}{c}H равен {delta}°. Найдите угол {a}{c}{b}. Ответ дайте в градусах.</p>"
    )
    return case, ctx


def check_rows(html, m):
    alpha, delta = map(float, [m.alpha, m.delta])
    points = {
        "A": (1 - 1 / math.tan(math.radians(alpha)), 0),
        "B": (1 - math.tan(math.radians(delta)), 0),
        "C": (1, 1),
        "H": (1, 0),
    }
    assert points["A"][0] < points["B"][0] < points["H"][0]
    values = {
        "A": m.alpha,
        "AHC": 90,
        "ACH": m.intermediate,
        "BCH": m.delta,
        "ACB": m.answer,
    }
    for name in ["AHC", "ACH", "BCH", "ACB"]:
        assert abs(angle(points, name) - float(values[name])) < 1e-8
    assert abs(angle(points, "BAC") - alpha) < 1e-8
    reverse = dict(zip(m.frame + "H", "ABCH"))
    rows = BeautifulSoup(html, "html.parser").select("center [data-inline-latex]")
    assert len(rows) == 7
    for row in rows:
        expression = re.sub(
            r"\\angle\s*([ABCH]{3}|[ABC])",
            lambda match: (
                "(" + sp.latex(values["".join(reverse[n] for n in match[1])]) + ")"
            ),
            row["data-inline-latex"],
        ).replace(r"^{\circ}", "")
        sides = [TrigonometricParser(s).parse().value for s in expression.split("=")]
        assert len(sides) == 2 and sp.simplify(sides[0] - sides[1]) == 0, expression


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_preserve_the_exact_condition_and_ignore_stored_results(case):
    ctx = deepcopy(case["context"])
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    condition = deepcopy(section(ctx, "condition"))
    for key in ["solution", "answer"]:
        section(ctx, key)["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert ctx == before and result.answer == expected and not selection(ctx)[-1]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert section(ctx, "condition") == condition
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("frame", FRAMES)
@pytest.mark.parametrize("explicit", [False, True])
def test_reviewed_image_and_explicit_premise_agree_in_all_vertex_frames(
    frame, explicit
):
    case, ctx = synthetic(frame, explicit)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == "38"
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
    "old,new",
    [
        ("угол B — тупой", "угол B — острый"),
        ("CH — высота", "AH — высота"),
        ("CH — высота", "BH — высота"),
        ("угол BCH", "угол ACH"),
        ("угол ACB", "угол ABC"),
    ],
)
def test_contradictory_image_premise_or_changed_roles_fail_closed(old, new):
    case, ctx = synthetic()
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("alpha,delta", [(0, 22), (30, 0), (70, 20), (70, 22)])
def test_invalid_or_degenerate_triangle_is_rejected(alpha, delta):
    case, ctx = synthetic(alpha=alpha, delta=delta)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "alpha,delta,expected", [("30{,}5", 22, "37,5"), (60, "19{,}5", "10,5")]
)
def test_exact_half_degree_results(alpha, delta, expected):
    case, ctx = synthetic(alpha=alpha, delta=delta)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)


@pytest.mark.parametrize("frame,lost", [("ABC", False), ("CAB", False), ("CAB", True)])
def test_local_frozen_roundtrip_checks_real_ids_and_condition_readback(frame, lost):
    case, ctx = synthetic(frame)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    kwargs = {"parent_solution_html": parent_html("27757")}
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
    assert len(gateway.uploads) == int(frame != "ABC")
    if not lost:
        assert (
            _apply_record(gateway, record, SOURCE, RULE, **kwargs)["status"]
            == "already_complete"
        )


def test_changed_parent_method_is_rejected():
    with pytest.raises(ContentPlanError):
        plan(CASES[0], parent=parent_html("27757") + "<p>Другой способ</p>")


@pytest.mark.parametrize("change", ["extra", "unknown", "reference", "url"])
def test_unknown_condition_images_are_rejected_even_without_textual_obtuse_premise(
    change,
):
    case, ctx = synthetic(explicit=False)
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


def test_source_is_packaged_and_hash_pinned():
    assert source_bytes(SOURCE).lstrip().startswith((b"<?xml", b"<svg"))


def test_reviewed_source_geometry_places_h_beyond_b_and_height_perpendicular():
    root = ET.fromstring(source_bytes(SOURCE))
    lines = root.findall("{http://www.w3.org/2000/svg}line")
    sides = [e for e in lines if e.get("stroke") == "#0D0F0F"]
    a, c = [
        (float(sides[1].get("x" + str(i))), float(sides[1].get("y" + str(i))))
        for i in [1, 2]
    ]
    _, b = [
        (float(sides[2].get("x" + str(i))), float(sides[2].get("y" + str(i))))
        for i in [1, 2]
    ]
    h = (float(lines[0].get("x1")), float(lines[0].get("y1")))
    assert a[0] < b[0] < h[0] and abs(a[1] - b[1]) < 1e-6 and abs(b[1] - h[1]) < 1e-6
    assert abs(c[0] - h[0]) < 1e-6
    assert angle(dict(zip("ABCH", [a, b, c, h])), "ABC") > 90
