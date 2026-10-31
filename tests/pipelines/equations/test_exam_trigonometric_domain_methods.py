"""Original ratio domains, reciprocal substitutions and primary inequality selection."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    decode,
    ordered,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_domain_methods.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)

D = sp.atan(sp.Rational(1, 3)) / sp.pi
E = sp.atan(sp.Rational(2, 5)) / sp.pi
SELECTED = {
    "514241": "-1 -11/12 -7/12 0",
    "507985": "-3 -17/6 -2",
    "510459": "-2 -5/3 -1",
    "519632": (sp.Rational(15, 4), 4 - E),
    "519633": (2 + D, sp.Rational(11, 4), 3 + D),
    "500637": "-2",
    "510293": "-2",
    "511362": "7/3",
    "500638": "3",
    "523375": "-17/6 -13/6",
    "523400": "-11/6 -7/6",
    "507694": "-1 -3/4 -1/4 0 1/4",
    "511475": "-5/6 -1/2 -1/6 1/6 1/2",
    "507698": "-1/2 -1/4 1/4 1/2 3/4",
}
RESIDUES = {
    "514241": "0 1/12 5/12 1 13/12 17/12",
    "507985": "0 5/6 1 7/6",
    "510459": "0 1/3 1 5/3",
    "519632": (sp.Rational(3, 4), 1 - E, sp.Rational(7, 4), 2 - E),
    "519633": (D, sp.Rational(3, 4), 1 + D, sp.Rational(7, 4)),
    "500637": "0",
    "510293": "0",
    "511362": "1/3 5/3",
    "500638": "1",
    "523375": "7/6 11/6",
    "523400": "1/6 5/6",
    "507694": "0 1/4 3/4 1 5/4 7/4",
    "511475": "1/6 1/2 5/6 7/6 3/2 11/6",
    "507698": "1/4 1/2 3/4 5/4 3/2 7/4",
}
ORIGINAL = {
    "514241": 4 * s * s - sp.tan(X),
    "507985": 2 * sp.cos(sp.pi / 2 + X) - sp.sqrt(3) * sp.tan(X),
    "510459": 2 * sp.cos(sp.pi / 2 - X) - sp.tan(X),
    "519632": 2 / sp.tan(X) ** 2 + 7 / sp.tan(X) + 5,
    "519633": 1 / sp.tan(X) ** 2 - 2 / sp.tan(X) - 3,
    "500637": 7 * sp.tan(X) ** 2 - 1 / c + 1,
    "511362": 1 / sp.cot(X) ** 2 - 3 / c + 3,
    "500638": 4 * sp.tan(X) ** 2 + 3 / c + 3,
    "523375": 7 / (1 - c * c) + 9 / s - 10,
    "523400": 4 / (1 - c * c) - 5 / s - 6,
    "507694": sp.tan(X) + sp.cos(3 * sp.pi / 2 - 2 * X),
    "511475": sp.cot(X) - 2 * sp.cos(sp.pi / 2 - 2 * X),
    "507698": sp.cot(X) + sp.cos(sp.pi / 2 + 2 * X),
}
ORIGINAL["510293"] = ORIGINAL["500637"]


def allowed(task, q):
    angle = q * sp.pi
    variables = (
        (s, c)
        if task in ("519632", "519633", "511362")
        else (s,)
        if task in ("523375", "523400", "511475", "507698")
        else (c,)
    )
    return all(sp.simplify(v.subs(X, angle)) != 0 for v in variables)


def expected(value):
    return (
        tuple(map(sp.Rational, value.split()))
        if isinstance(value, str)
        else tuple(map(sp.sympify, value))
    )


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for p in CASES
        if p["task"] == c["group"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None):
    ctx = context or c["context"]
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in handler.diagram_specs(ctx)
    )
    return handler.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_one_shared_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_full_and_selected_roots_are_independent_and_respect_original_domain(c):
    task = c["task"]
    a = analysis(c)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == expected(RESIDUES[task]) and a.selected == expected(SELECTED[task])
    for q in roots:
        assert allowed(task, q) and sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
    for k in range(24):
        q = sp.Rational(k, 12)
        zero = (
            sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
            if allowed(task, q)
            else False
        )
        assert (q in roots) == zero


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    original = deepcopy(c["context"])
    p = plan(c)
    assert c["context"] == original
    changed = deepcopy(original)
    for s in changed["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>не использовать</p>"
    assert (
        plan(c, changed).answer == p.answer
        and plan(c, changed).solution_html == p.solution_html
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = changed["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, changed).transformations == ()
    assert (
        changed["normalized_content"]["assets"][
            : len(original["normalized_content"]["assets"])
        ]
        == original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_source_geometry_and_prepared_diagrams_are_certified(c):
    from xml.etree import ElementTree as ET

    a = analysis(c)
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    data = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    original = ET.fromstring(data)
    paths = {n.get("d") for n in original.iter()}
    cx, cy, _ = entry["circle"]
    for point in entry["green_markers"]:
        q = decode(point["angle"])
        assert point["path_d"] in paths and allowed(c["task"], q)
        assert (
            math.hypot(
                point["x"] - cx - point["radius"] * math.cos(float(q) * math.pi),
                point["y"] - cy + point["radius"] * math.sin(float(q) * math.pi),
            )
            < 5
        )
    all_points = entry["green_markers"] + entry.get("restored_markers", [])
    assert ordered(decode(p["angle"]) for p in all_points) == expected(
        RESIDUES[c["task"]]
    )
    validate(entry, a)
    specs = get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
        c["context"]
    )
    assert len(specs) == (1 if c["task"] in ("510459", "519633") else 0)
    assert len(BeautifulSoup(plan(c).solution_html, "html.parser").find_all("img")) == 1


def test_minus_font_repair_and_missing_root_preserve_every_original_element():
    from lxml import etree

    aid = case("510459")["context"]["normalized_content"]["assets"][0]["asset_id"]
    original = etree.fromstring(
        gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    )
    corrected = etree.fromstring(
        (DIRECTORY / CIRCLES[aid]["corrected_file"]).read_bytes()
    )
    points = corrected.xpath('//*[@data-role="restored-root"]')
    assert len(points) == 1 and points[0].get("data-q") == "1"
    assert float(points[0].get("cx")) == pytest.approx(2 * 100.513 - 162.4255)
    corrected.remove(points[0])
    changed = 0
    for before, after in zip(original.iter(), corrected.iter(), strict=True):
        if before.get("font-family") == "'SymbolMT'":
            assert after.get("font-family") == "'Times New Roman'"
            after.set("font-family", "'SymbolMT'")
            changed += 1
    assert changed == 8 and etree.tostring(original) == etree.tostring(corrected)


def test_prepared_tangent_axis_uses_parent_method_and_exact_child_geometry():
    from xml.etree import ElementTree as ET

    c = case("519633")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    root = ET.fromstring((DIRECTORY / e["corrected_file"]).read_text())
    points = [n for n in root.iter() if n.get("data-role") == "root"]
    qs = []
    selected = []
    for p in points:
        q = sp.Rational(p.get("data-q-rational"))
        if p.get("data-q-atan"):
            q += sp.atan(sp.Rational(p.get("data-q-atan"))) / sp.pi
        qs.append(q)
        assert float(p.get("cx")) == pytest.approx(
            120 + 64 * math.cos(float(q) * math.pi)
        )
        assert float(p.get("cy")) == pytest.approx(
            110 - 64 * math.sin(float(q) * math.pi)
        )
        if p.get("data-selected") == "true":
            selected.append(q)
    assert ordered(qs) == expected(RESIDUES["519633"])
    assert ordered(selected) == ordered(q % 2 for q in expected(SELECTED["519633"]))
    axis = next(n for n in root.iter() if n.get("data-role") == "ratio-axis")
    assert (
        axis.get("data-function") == "tg" and axis.get("x1") == axis.get("x2") == "184"
    )
    for n in root.iter():
        if n.get("data-role") == "ratio-projection":
            v = float(sp.Rational(n.get("data-value")))
            assert float(n.get("x2")) == 184 and float(n.get("y2")) == pytest.approx(
                110 - 64 * v
            )
            assert (float(n.get("y2")) - 110) / (
                float(n.get("x2")) - 120
            ) == pytest.approx((float(n.get("y1")) - 110) / (float(n.get("x1")) - 120))
    bounds = [
        sp.Rational(n.get("data-q"))
        for n in root.iter()
        if n.get("data-role") == "interval-bound"
    ]
    assert bounds == [2, sp.Rational(7, 2)]
    text = " ".join(root.itertext())
    assert all(label in text for label in ("11π", "arctg(1/3) + 2π", "3π + arctg(1/3)"))
    for field, value in (
        ("function", "ctg"),
        ("function", "sin"),
        ("levels", ["-1", "3"]),
    ):
        bad = deepcopy(e)
        bad["ratio_axis"][field] = value
        with pytest.raises(UnsupportedCondition, match="ratio axis"):
            validate(bad, analysis(c))


@pytest.mark.parametrize("task", ["500637", "510293", "511362", "500638"])
def test_double_inequality_is_primary_and_circle_remains_a_note_after_part_a(task):
    a = analysis(case(task))
    assert (
        a.selection_method == "inequalities"
        and a.circle_note
        and a.image_position == "after-steps"
    )
    html = BeautifulSoup(plan(case(task)).solution_html, "html.parser")
    text = html.get_text(" ")
    assert "параметра каждой серии" in text and "Примечание" in text
    assert text.index("параметра каждой серии") < text.index("Примечание")
    assert html.find("img").find_parent("li") == html.find("ol").find(
        "li", recursive=False
    )
    if task == "510293":
        assert r"-2\pi" in plan(case(task)).answer.replace(" ", "")


@pytest.mark.parametrize("task", ["523375", "523400"])
def test_complement_denominator_preserves_original_poles_and_direct_method(task):
    a = analysis(case(task))
    assert S in a.poles and 1 - C * C in a.poles
    assert a.substitution is None and a.fraction is not None
    html = plan(case(task)).solution_html
    assert "Введём обозначение" not in html
    assert "знаменател" in BeautifulSoup(html, "html.parser").get_text()


def test_scaled_angle_filter_keeps_both_sine_double_angle_values():
    a = analysis(case("514241"))
    branch = next(b for b in a.branches if b.angle_scale == 2)
    assert branch.values == (sp.Rational(1, 2),) and len(branch.residues) == 4
    assert a.poles == (C,)


def test_paragraph_marker_without_space_does_not_hide_extra_instructions():
    context = deepcopy(case("510293")["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert "б)Най" in condition["html"]
    condition["html"] += "<p>Дополнительно найдите сумму корней.</p>"
    with pytest.raises(UnsupportedCondition):
        read(context)


def test_pole_filter_rejects_unreviewed_angle_scales():
    from dataclasses import replace

    from solution_runner.pipelines.equations.exam_trigonometric_domain import (
        without_poles,
    )

    a = analysis(case("514241"))
    branch = a.branches[1]
    for scale in (sp.Rational(1, 2), 0, 13):
        with pytest.raises(UnsupportedCondition, match="bounded positive integer"):
            without_poles((replace(branch, angle_scale=scale),), a.poles)
