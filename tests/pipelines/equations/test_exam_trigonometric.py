"""Complete periodic sets, exact endpoints and audited circle reuse."""

import gzip
import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import C, S, analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_inverse import decode
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_14_trigonometric.json").read_text()
)
CASES = DATA["cases"]
QUARTERS = ("1/4", "3/4", "5/4", "7/4")
SIXTHS = ("1/6", "5/6", "7/6", "11/6")
THIRDS = ("1/3", "2/3", "4/3", "5/3")
RESIDUES = {
    "507595": ("0", "2/3", "4/3"),
    "501709": ("1/6", "1/2", "5/6", "3/2"),
    "500917": ("1/3", "1", "5/3"),
    "647135": ("1/6", "1/2", "5/6", "3/2"),
    "510018": ("0", "1/6", "5/6", "1"),
    "511337": SIXTHS,
    "500131": QUARTERS,
    "505547": SIXTHS,
    "500592": SIXTHS,
    "511392": ("2/3", "4/3"),
    "513093": ("5/6", "7/6"),
    "504850": ("1/3", "5/3"),
    "514649": ("5/6", "7/6"),
    "504543": QUARTERS,
    "510671": QUARTERS,
    "507292": ("1/2", "3/2"),
    "504564": SIXTHS,
    "500366": QUARTERS,
    "500587": SIXTHS,
    "501482": THIRDS,
    "514505": THIRDS,
}
SELECTED = {
    "507595": ("-2", "-4/3"),
    "501709": ("-7/2", "-19/6", "-5/2"),
    "500917": ("5/3", "7/3"),
    "647135": ("5/2", "17/6", "7/2"),
    "510018": ("-2", "-11/6", "-7/6"),
    "511337": ("-17/6", "-13/6", "-11/6"),
    "500131": ("-7/4", "-5/4", "-3/4"),
    "505547": ("7/6", "11/6", "13/6"),
    "500592": ("7/6", "11/6", "13/6"),
    "511392": ("-14/3",),
    "513093": ("-19/6", "-17/6"),
    "504850": ("-7/3", "-5/3"),
    "514649": ("-7/6",),
    "504543": ("-7/4", "-5/4"),
    "510671": ("-7/4", "-5/4"),
    "507292": ("3/2", "5/2"),
    "504564": ("13/6", "17/6"),
    "500366": ("-13/4", "-11/4", "-9/4"),
    "500587": ("7/6", "11/6", "13/6"),
    "501482": ("10/3", "11/3", "13/3"),
    "514505": ("-11/3", "-10/3", "-8/3"),
}
X = sp.Symbol("x", real=True)
ORIGINAL = {
    "507595": sp.cos(2 * X) - sp.sin(X + sp.pi / 2),
    "501709": sp.sin(2 * X) - sp.sin(sp.pi / 2 + X),
    "500917": sp.cos(2 * X) - sp.sin(3 * sp.pi / 2 - X),
    "647135": sp.sin(2 * X) - sp.sin(X - 3 * sp.pi / 2),
    "510018": sp.cos(2 * X) - 1 + sp.cos(sp.pi / 2 - X),
    "511337": sp.cos(2 * X) + sp.sin(X) ** 2 - sp.Rational(3, 4),
    "500131": sp.cos(2 * X) + sp.Rational(1, 2) - sp.cos(X) ** 2,
    "505547": sp.cos(2 * X) + sp.sin(X) ** 2 - sp.Rational(3, 4),
    "500592": sp.cos(2 * X) + 3 * sp.sin(X) ** 2 - sp.Rational(5, 4),
    "511392": 6 * sp.sin(X) ** 2 + 15 * sp.sin(3 * sp.pi / 2 + X) - 12,
    "513093": 8 * sp.sin(X) ** 2 + 2 * sp.sqrt(3) * sp.cos(X) + 1,
    "504850": 4 * sp.sin(X) ** 2 + 8 * sp.sin(3 * sp.pi / 2 + X) + 1,
    "514649": 2 * sp.sin(X) ** 2 + 4 - 3 * sp.sqrt(3) * sp.sin(3 * sp.pi / 2 + X),
    "504543": 4 * sp.cos(X) ** 4 - 4 * sp.cos(X) ** 2 + 1,
    "510671": 4 * sp.cos(X) ** 4 - 4 * sp.cos(X) ** 2 + 1,
    "507292": 2 * sp.sin(X) ** 4 + 3 * sp.cos(2 * X) + 1,
    "504564": 16 * sp.cos(X) ** 4 - 24 * sp.cos(X) ** 2 + 9,
    "500366": sp.cos(2 * X) + sp.sin(X) ** 2 - sp.Rational(1, 2),
    "500587": sp.cos(2 * X) - sp.sin(sp.pi / 2 - X) ** 2 + sp.Rational(1, 4),
    "501482": sp.cos(2 * X) + sp.sin(X) ** 2 - sp.Rational(1, 4),
    "514505": sp.cos(2 * X) + sp.cos(3 * sp.pi / 2 - X) ** 2 - sp.Rational(1, 4),
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for s in case(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c, context=None):
    _, formula, interval, bounds = read(context or c["context"])
    return analyze(formula, interval, bounds, parent(c))


def plan(c, context=None, prototype=None):
    context = context or c["context"]
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    specs = handler.diagram_specs(context)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in specs
    )
    return handler.plan(
        PlanInput(
            context,
            parent_solution_html=parent(c) if prototype is None else prototype,
            generated_solution_assets=generated,
        )
    )


def changed(task, old, new):
    c = case(task)
    context = deepcopy(c["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert old in s["html"]
    s["html"] = s["html"].replace(old, new)
    return c, context


def replay(context, changes):
    for t in changes:
        key = t["transformation_target_id"]
        kind = "assets" if key.startswith("asset:") else "sections"
        items = context["normalized_content"][kind]
        item = next(
            (s for s in items if s.get("transformation_target_id") == key), None
        )
        if item is None:
            item = {"transformation_target_id": key}
            if kind == "sections":
                item["key"] = key.split(":")[1]
            items.append(item)
        item.update(t["value"])


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_six_groups_share_the_same_mathematical_and_diagram_rule(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 4, g["order"], "14")
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_periodic_and_selected_roots_are_independent_of_saved_answers(c):
    a = analysis(c)
    assert a.residues == tuple(sp.Rational(q) for q in RESIDUES[c["task"]])
    assert a.selected == tuple(sp.Rational(q) for q in SELECTED[c["task"]])
    actual_grid = tuple(
        sp.Rational(i, 12)
        for i in range(24)
        if sp.simplify(ORIGINAL[c["task"]].subs(X, sp.pi * i / 12)) == 0
    )
    assert actual_grid == a.residues
    for q in (*a.residues, *a.selected):
        assert sp.simplify(ORIGINAL[c["task"]].subs(X, q * sp.pi)) == 0
    for q in a.residues:
        assert any(((q - offset) / period).is_Integer for offset, period in a.series)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_plans_preserve_conditions_ignore_saved_answers_and_replay_cleanly(c):
    context = deepcopy(c["context"])
    before = deepcopy(context)
    p = plan(c, context)
    assert context == before and p.condition_html == next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    for s in context["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>999999 INVALID</p>"
    assert plan(c, context) == p
    replay(context, p.transformations)
    assert plan(c, context).transformations == ()
    changes = [
        t
        for t in p.transformations
        if t["transformation_target_id"].startswith("asset:")
    ]
    assert len(changes) == (1 if c["task"] == "500131" else 0)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_numbers_are_unused_and_figure_position_is_preserved(c):
    soup = BeautifulSoup(parent(c), "html.parser")
    for span in soup.select("[data-inline-latex]"):
        span["data-inline-latex"] = re.sub(r"\d+", "997", span["data-inline-latex"])
    p = plan(c)
    assert plan(c, prototype=str(soup)) == p
    html = BeautifulSoup(p.solution_html, "html.parser")
    image = html.find("img")
    a = analysis(c)
    if a.image_position == "outside":
        assert image.find_parent("li") is None
    else:
        assert image.find_parent("li")["data-list-marker"] == "а)"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_parent_instructions_and_assets_fail_closed(c):
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype="")
    context = deepcopy(c["context"])
    context["normalized_content"]["assets"].append({"asset_key": "unknown"})
    with pytest.raises(UnsupportedCondition):
        plan(c, context)
    context = deepcopy(c["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    s["html"] = s["html"].replace("Ре­ши­те", "Приближённо решите")
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


@pytest.mark.parametrize(
    "identifier,entry",
    CIRCLES.items(),
    ids=lambda e: e if isinstance(e, str) else e["task"],
)
def test_source_svg_bytes_and_marker_positions_match_the_audited_geometry(
    identifier, entry
):
    svg = gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == entry["sha256"]
    root = ET.fromstring(svg)
    paths = {e.attrib.get("d") for e in root.iter() if e.tag.endswith("path")}
    cx, cy, radius = entry["circle"]
    for point in entry["green_markers"]:
        assert point["path_d"] in paths
        angle = float(decode(point["angle"])) * math.pi
        radius = point.get("radius", entry["circle"][2])
        distance = math.hypot(
            point["x"] - (cx + radius * math.cos(angle)),
            point["y"] - (cy - radius * math.sin(angle)),
        )
        if point.get("inaccurate"):
            assert entry.get("corrected_file") and distance > 5
        else:
            assert distance < 5


def test_corrected_circle_removes_only_the_nonroot_marker_without_altering_labels():
    identifier = "2f370764-2b35-47e0-96f5-5616a00cd4c2"
    entry = CIRCLES[identifier]
    original = ET.fromstring(
        gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    )
    corrected = ET.fromstring((DIRECTORY / entry["corrected_file"]).read_bytes())
    assert original.attrib == corrected.attrib
    for e in (*original.iter(), *corrected.iter()):
        if e.tail is not None and not e.tail.strip():
            e.tail = None
        if e.text is not None and not e.text.strip():
            e.text = None
    old = [ET.tostring(e) for e in original]
    new = [ET.tostring(e) for e in corrected]
    assert len(old) - len(new) == 2
    remaining = [e for e in old if e in new]
    assert remaining == new
    assert sp.simplify(ORIGINAL["500131"].subs(X, 3 * sp.pi / 2)) != 0


def test_factoring_sine_double_angle_keeps_the_zero_cosine_branch():
    a = analysis(case("501709"))
    assert len(a.branches) == 2 and {b.variable for b in a.branches} == {S, C}
    assert sp.Rational(1, 2) in a.residues and sp.Rational(3, 2) in a.residues
    assert "не делим" in plan(case("501709")).solution_html


def test_full_square_and_necessary_nonsquare_child_reduction_are_explained():
    assert "Выделим полный квадрат" in plan(case("504543")).solution_html
    html = plan(case("507292")).solution_html
    assert "не является полным квадратом" in html and "не обращается в нуль" in html
    assert "Not match" not in html


def test_out_of_range_trigonometric_values_are_rejected():
    for task in ("511392", "513093", "504850", "514649"):
        a = analysis(case(task))
        assert any(v not in b.values for b in a.branches for v in b.candidates)
        assert "от −1 до 1" in plan(case(task)).solution_html


@pytest.mark.parametrize(
    "bounds,expected",
    [
        ((sp.Rational(1, 4), sp.Rational(1, 4), True, True), (sp.Rational(1, 4),)),
        ((sp.Rational(1, 4), sp.Rational(3, 4), False, False), ()),
        ((sp.Rational(1, 4), sp.Rational(3, 4), False, True), (sp.Rational(3, 4),)),
    ],
)
def test_exact_series_selection_obeys_open_and_singleton_boundaries(bounds, expected):
    assert select(((sp.Rational(1, 4), sp.Rational(1, 2)),), bounds)[0] == expected


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("507595", r"\sin (x+\frac{\pi}{2})", r"-\sin (x+\frac{\pi}{2})"),
        ("511337", r"0{,}75", r"0{,}3"),
        ("507595", r"[-2\pi;-\pi]", r"[-4\pi;-3\pi]"),
        ("507595", r"\cos 2x", r"\frac{\cos 2x}{\sin x}"),
    ],
)
def test_changed_equation_unsupported_table_and_incompatible_circle_fail_closed(
    task, old, new
):
    c, context = changed(task, old, new)
    with pytest.raises(UnsupportedCondition):
        plan(c, context)
