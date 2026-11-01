"""Original poles and zero radicals survive both parent and child product methods."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import cv2
import numpy as np
import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    RASTERS,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_radical_product import (
    compile_product,
    operands,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_radical_products.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
R = sp.Rational
POLYNOMIALS = {
    "484557": (2 * S + sp.sqrt(3), C, ()),
    "512335": (S * S / C**2 - 1, 13 * C, (C,)),
    "512377": (S * S / C**2 - 3, 11 * C, (C,)),
    "512398": (sp.sqrt(2) * S * S + C - sp.sqrt(2), -6 * S, ()),
    "484555": (6 * S * S + 5 * S - 4, -7 * C, ()),
    "511289": (2 * C * C - 5 * C + 2, S, ()),
    "530401": (1 - 3 * S * S / C**2, 7 * S, (C,)),
    "530433": (3 * S * S / C**2 - 1, -5 * C, (C,)),
    "530672": (sp.sqrt(2) * S * S + C - sp.sqrt(2), -6 * S, ()),
    "530692": (2 * C * C + S - 2, 5 * S / C, (C,)),
    "621775": (S * S / C**2 - 3, 18 * C, (C,)),
    "621904": (3 * S * S / C**2 - 1, 7 * C, (C,)),
}
EXPECTED = {
    "484557": ("1/2 3/2 5/3", "3/2 5/3 5/2 7/2"),
    "512335": ("1/4 7/4", "-9/4 -7/4"),
    "512377": ("1/3 5/3", "-7/3 -5/3"),
    "512398": ("0 1 3/2 7/4", "2 3 7/2"),
    "484555": ("1/2 5/6 3/2", "-5/2 -3/2 -7/6"),
    "511289": ("0 1/3 1", "-2 -5/3 -1"),
    "530401": ("0 1/6 5/6 1", "-2 -11/6 -7/6 -1"),
    "530433": ("5/6 7/6", "-19/6 -17/6"),
    "530672": ("0 1 3/2 7/4", "2 3 7/2"),
    "530692": ("0 1/6 1", "1 2 13/6"),
    "621775": ("1/3 5/3", "13/3"),
    "621904": ("1/6 11/6", "35/6"),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(e):
    return next(
        s["html"]
        for s in case(e["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(e):
    _, f, i, b = read(e["context"])
    return analyze(f, i, b, parent(e))


def plan(e, context=None):
    ctx = context or e["context"]
    handler = get_handler(get_group_profile(e["group"]).content_rule_key)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler.diagram_specs(ctx)
    )
    return handler.plan(
        PlanInput(
            ctx, parent_solution_html=parent(e), generated_solution_assets=generated
        )
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_catalog_registration_reuses_the_same_trigonometric_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"], "14")


@pytest.mark.parametrize("e", CASES, ids=lambda c: c["task"])
def test_complete_series_and_selected_roots_follow_original_equations(e):
    key = e["task"]
    a = analysis(e)
    full, wanted = (tuple(map(R, row.split())) for row in EXPECTED[key])
    assert select(a.series, (sp.S.Zero, sp.Integer(2), True, False))[0] == full
    assert a.selected == wanted
    p, rad, poles = POLYNOMIALS[key]
    for q in (*full, *wanted):
        subst = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        assert all(sp.simplify(pole.subs(subst)) != 0 for pole in poles)
        assert sp.simplify((p * sp.sqrt(rad)).subs(subst)) == 0
    value = sp.lambdify((S, C), (p, rad), "math")
    window = select(a.series, (-4, 4, True, True))[0]
    for k in range(-96, 97):
        q = R(k, 24)
        si, co = math.sin(float(q) * math.pi), math.cos(float(q) * math.pi)
        if poles and abs(co) < 1e-10:
            actual = False
        else:
            pv, rv = value(si, co)
            actual = rv >= -1e-10 and (abs(rv) < 1e-10 or abs(pv) < 1e-10)
        assert (q in window) == actual, (key, q)


@pytest.mark.parametrize("e", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(e):
    original = deepcopy(e["context"])
    ctx = deepcopy(original)
    p = plan(e)
    assert e["context"] == original
    assert p.condition_html == next(
        s["html"]
        for s in original["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    for sec in ctx["normalized_content"]["sections"]:
        if sec["key"] in ("answer", "solution"):
            sec["html"] = "<p>Не использовать.</p>"
    assert plan(e, ctx) == p
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = ctx["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(e, ctx).transformations == ()
    assert all(
        a in ctx["normalized_content"]["assets"]
        for a in original["normalized_content"]["assets"]
    )
    assert len(ctx["normalized_content"]["assets"]) == len(
        original["normalized_content"]["assets"]
    ) + (e["task"] == "511289")


def test_zero_sine_is_retained_in_parent_but_zero_cosine_is_a_child_tangent_pole():
    parent_a = analysis(case("530401"))
    child = analysis(case("530433"))
    assert parent_a.series[0] == (sp.S.Zero, sp.S.One)
    assert {sp.S.Zero, sp.S.One} <= set(parent_a.residues)
    assert child.poles == (C,)
    assert not {sp.S.Half, R(3, 2)} & set(child.residues)
    assert "Нулевое подкоренное выражение" in plan(case("530433")).solution_html
    assert (
        "первом случае" in plan(case("530401")).solution_html
        or "Сначала" in plan(case("530401")).solution_html
    )


def test_ratio_radicand_keeps_zero_tangent_and_excludes_zero_cosine():
    a = analysis(case("530692"))
    p = plan(case("530692"))
    assert a.poles == (C,) and a.radical_product.radicand == 5 * S / C
    assert a.domain == 5 * S * C
    assert a.series == ((sp.S.Zero, sp.S.One), (R(1, 6), sp.Integer(2)))
    assert "уже рассмотрены в первом случае" in p.solution_html
    assert "квадрат знаменателя положителен" in p.solution_html


def test_each_parent_keeps_its_own_order_and_negative_series_offsets():
    assert analysis(case("512398")).series == (
        (sp.S.Zero, sp.S.One),
        (R(-1, 4), sp.Integer(2)),
        (R(-1, 2), sp.Integer(2)),
    )
    assert analysis(case("530672")).series == (
        (sp.S.Zero, sp.S.One),
        (R(-1, 2), sp.Integer(2)),
        (R(-1, 4), sp.Integer(2)),
    )
    assert analysis(case("511289")).series == (
        (sp.S.Zero, sp.S.One),
        (R(1, 3), sp.Integer(2)),
    )
    assert analysis(case("530401")).series == (
        (sp.S.Zero, sp.S.One),
        (R(1, 6), sp.Integer(2)),
        (R(5, 6), sp.Integer(2)),
    )


@pytest.mark.parametrize(
    "e",
    [
        c
        for c in CASES
        if c["context"]["normalized_content"]["assets"] and c["task"] != "621904"
    ],
    ids=lambda c: c["task"],
)
def test_exact_native_svg_geometry_preserves_valid_and_crossed_points(e):
    asset = e["context"]["normalized_content"]["assets"][0]
    entry = CIRCLES[asset["asset_id"]]
    raw = gzip.decompress((DIRECTORY / (asset["asset_id"] + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    root = ET.fromstring(raw)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    assert entry["native_circle_path"] in paths
    cx, cy, _ = entry["circle"]
    for point in entry["green_markers"] + entry["excluded_markers"]:
        assert point["path_d"] in paths and point["native_circle_path"] in paths
        q = float(R(point["angle"])) * math.pi
        assert (
            math.hypot(
                point["x"] - cx - point["radius"] * math.cos(q),
                point["y"] - cy + point["radius"] * math.sin(q),
            )
            < 5
        )
    assert "corrected_file" not in entry
    validate(entry, analysis(e))
    assert (
        get_handler(get_group_profile(e["group"]).content_rule_key).diagram_specs(
            e["context"]
        )
        == ()
    )
    if e["task"] == "512335":
        assert root.get("viewBox") == "0 0 4800 5000"
        assert entry["native_scale"] == pytest.approx(48 * 96 / 25.4 / 4800)
        assert any(n.get("class", "").find("fil6") >= 0 for n in root.iter())


def test_original_png_circle_and_selected_marker_are_certified_in_native_pixels():
    e = case("621904")
    asset = e["context"]["normalized_content"]["assets"][0]
    entry = RASTERS[asset["asset_id"]]
    raw = (DIRECTORY / entry["file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    grey = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE)
    assert grey.shape == (178, 173)
    cx, cy, radius = entry["circle"]
    hough = cv2.HoughCircles(
        grey,
        cv2.HOUGH_GRADIENT,
        1,
        40,
        param1=100,
        param2=30,
        minRadius=50,
        maxRadius=65,
    )
    assert hough is not None
    hx, hy, hr = hough[0][0]
    assert abs(hx - cx) < 2 and abs(hy - cy) < 2 and abs(hr - radius) < 2
    point = entry["selected_markers"][0]
    q = float(R(point["angle"])) * math.pi
    assert (
        math.hypot(
            point["x"] - cx - radius * math.cos(q),
            point["y"] - cy + radius * math.sin(q),
        )
        < 1
    )
    assert grey[point["y"], point["x"]] < 50
    validate(entry, analysis(e))
    assert entry["point_scope"] == "selected"
    assert len(BeautifulSoup(plan(e).solution_html, "html.parser").find_all("img")) == 1


def test_assetless_child_gets_a_local_circle_with_its_own_domain_and_roots():
    e = case("511289")
    handler = get_handler(get_group_profile(e["group"]).content_rule_key)
    (spec,) = handler.diagram_specs(e["context"])
    root = ET.fromstring(spec["svg_text"])
    points = [n for n in root.iter() if n.get("data-role") == "selected-root"]
    assert {n.get("data-root") for n in points} == {"-2", "-5/3", "-1"}
    for point in points:
        q = float(point.get("data-angle")) * math.pi
        assert (
            math.hypot(
                float(point.get("cx")) - 93.492 - 62.56 * math.cos(q),
                float(point.get("cy")) - 110.891 + 62.56 * math.sin(q),
            )
            < 1e-6
        )
    arc = next(n for n in root.iter() if n.get("data-role") == "interval-arc")
    assert arc.get("data-bounds") == "-5/2;-1" and " 0 1 0 " in arc.get("d")
    cross = next(n for n in root.iter() if n.get("data-role") == "excluded-root")
    assert cross.get("data-angle") == "5/3"
    p = plan(e)
    assert (
        BeautifulSoup(p.solution_html, "html.parser")
        .find("img")["src"]
        .startswith("/assets/preview-")
    )


@pytest.mark.parametrize(
    "factor,radicand",
    [
        (r"\sin x", r"\sin x+1"),
        (r"\tg^2 2x-1", r"\cos x"),
        (r"\tg^3 x-1", r"\cos x"),
        (r"\sin x", r"\tg x+1"),
    ],
)
def test_unreviewed_radicands_angles_and_degrees_fail_closed(factor, radicand):
    with pytest.raises(UnsupportedCondition):
        compile_product(factor, radicand)


def test_product_recognition_is_exact_and_does_not_take_additive_radicals():
    assert operands(r"(\sin x)\cdot\sqrt{\cos x}=0") == (r"\sinx", r"\cosx")
    assert operands(r"(\sin x)+\sqrt{\cos x}=0") is None
    assert operands(r"(\sin x)\sqrt{\cos x}=1") is None


def test_linear_tangent_factor_uses_the_same_domain_and_does_not_restore_its_pole():
    from solution_runner.pipelines.equations.exam_trigonometric_domain import (
        radical_product,
    )
    from solution_runner.pipelines.equations.exam_trigonometric_radical_product import (
        cases,
    )

    compiled = radical_product(r"(\tg x+1)\sqrt{-5\cos x}=0")
    zero, positive = cases(compiled, C, False)
    assert compiled.poles == (C,)
    assert not any(b.residues for b in zero)
    assert {q for b in positive for q in b.residues} == {R(3, 4)}


def test_original_raster_cannot_be_reused_for_a_different_interval_or_unknown_asset():
    from dataclasses import replace

    e = case("621904")
    entry = RASTERS[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    with pytest.raises(UnsupportedCondition):
        validate(entry, replace(analysis(e), bounds=(R(4), R(6), True, True)))
    ctx = deepcopy(e["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        read(ctx)
