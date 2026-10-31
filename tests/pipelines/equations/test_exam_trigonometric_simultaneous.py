"""Simultaneous squares, affine sine arguments and exact parent cosine phases."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

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
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_parameters import (
    affine_families,
)
from solution_runner.pipelines.equations.exam_trigonometric_sine_pair import (
    compile_pair,
)
from solution_runner.pipelines.equations.exam_trigonometric_sum_squares import (
    compile_squares,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_simultaneous.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
EXPECTED = {
    "635141": ("2/3 4/3", "14/3"),
    "654843": ("1/4 7/4", "17/4"),
    "654932": ("3/4 5/4", "13/4"),
    "647805": ("5/6", "17/6 29/6"),
    "672849": ("0 3/2", "0 3/2"),
    "680457": ("1/6", "1/6"),
    "681577": ("1/2 7/6 11/6", "-7/2 -17/6 -13/6 -3/2"),
    "694272": ("3/2", "-1/2 3/2"),
}
ORIGINAL = {
    "635141": (5 * sp.cos(2 * X) - 3 * c + 1) / (25 * s * s - 9),
    "654843": (3 * sp.cos(2 * X) - 5 * sp.sqrt(2) * c + 5) / (9 * s * s - 7),
    "654932": (5 * sp.cos(2 * X) + 3 * sp.sqrt(2) * c + 3) / (25 * s * s - 23),
    "647805": sp.sin(2 * X) ** 2
    + c * c
    + sp.sqrt(3) * (sp.sin(2 * X) + c)
    + sp.Rational(3, 2),
    "672849": 1 + s - c,
    "680457": sp.tan(X) * (1 - 2 * s) - 2 * c + sp.sqrt(3),
    "681577": sp.sin(-2 * X + sp.pi / 2) - sp.sin(4 * sp.pi - X),
    "694272": (1 - s + sp.sqrt(3) * sp.sin(2 * X)) / (2 * sp.sqrt(3) * c - 3)
    - sp.Rational(1, 3)
    - s,
}
POLES = {task: () for task in ORIGINAL}
POLES.update(
    {
        "635141": (25 * s * s - 9,),
        "654843": (9 * s * s - 7,),
        "654932": (25 * s * s - 23,),
        "680457": (c,),
        "694272": (2 * sp.sqrt(3) * c - 3,),
    }
)


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(example):
    return next(
        s["html"]
        for s in case(example["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example, formula=None):
    _, f, i, b = read(example["context"])
    return analyze(formula or f, i, b, parent(example))


def plan(example, context=None):
    return get_handler(get_group_profile(example["group"]).content_rule_key).plan(
        PlanInput(context or example["context"], parent_solution_html=parent(example))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_the_existing_rule_and_exact_catalog_coordinates(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], g["theme_order"], g["order"], "14")


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_are_independently_expected(example):
    task = example["task"]
    a = analysis(example)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == tuple(map(sp.Rational, EXPECTED[task][0].split()))
    assert a.selected == tuple(map(sp.Rational, EXPECTED[task][1].split()))
    for q in (*roots, *a.selected):
        assert all(sp.simplify(p.subs(X, q * sp.pi)) != 0 for p in POLES[task])
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
    function = sp.lambdify(X, ORIGINAL[task], "math")
    poles = [sp.lambdify(X, p, "math") for p in POLES[task]]
    for k in range(360):
        q = sp.Rational(k, 180)
        angle = float(q) * math.pi
        allowed = all(abs(p(angle)) > 1e-10 for p in poles)
        zero = allowed and abs(function(angle)) < 1e-9
        assert (q in roots) == zero


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(example):
    original = deepcopy(example["context"])
    p = plan(example)
    assert example["context"] == original
    changed = deepcopy(original)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>Не использовать.</p>"
    poisoned = plan(example, changed)
    assert (poisoned.answer, poisoned.solution_html) == (p.answer, p.solution_html)
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith(("section:condition", "asset:"))
        item = next(
            s
            for s in changed["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        )
        item.update(t["value"])
        if key.startswith("section:solution"):
            assert item["asset_keys"] == [
                a["asset_key"] for a in original["normalized_content"]["assets"]
            ]
    assert plan(example, changed).transformations == ()
    assert (
        changed["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    images = BeautifulSoup(p.solution_html, "html.parser").find_all("img")
    assert [i["src"] for i in images] == [
        a["url"] for a in original["normalized_content"]["assets"]
    ]
    assert (
        get_handler(get_group_profile(example["group"]).content_rule_key).diagram_specs(
            original
        )
        == ()
    )


def test_two_squares_keep_the_simultaneous_system_and_positive_offset_neighbors():
    example = case("647805")
    a = analysis(example)
    assert a.sum_squares is not None and a.selection_method == "neighbors"
    assert a.series == ((sp.Rational(5, 6), sp.Integer(2)),)
    text = BeautifulSoup(plan(example).solution_html, "html.parser").get_text(" ")
    assert "полные квадраты" in text and "одновременно" in text
    assert "Все меньшие индексы" in text and "Все большие индексы" in text
    assert "дискриминант" not in text and "Введём обозначение" not in text
    assert analysis(example, r"\sin^{2}2x+\cos^{2}x=0").selected == (
        5 * sp.Rational(1, 2),
        7 * sp.Rational(1, 2),
        9 * sp.Rational(1, 2),
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"\sin^{2}2x+\cos^{2}x+1=0",
        r"\sin^{2}2x+\cos^{2}x+\sin 2x\cos x=0",
        r"-\sin^2 2x-\cos^2 x=0",
    ],
)
def test_square_completion_rejects_a_remainder_cross_term_or_negative_weights(formula):
    with pytest.raises(UnsupportedCondition):
        compile_squares(formula)


def test_parent_cosine_phase_and_series_order_are_retained_after_sign_change():
    a = analysis(case("672849"))
    b = a.branches[0]
    assert b.angle_shift == sp.Rational(1, 4) and b.candidates == (sp.sqrt(2) / 2,)
    assert a.series == ((0, 2), (-sp.Rational(1, 2), 2))
    html = plan(case("672849")).solution_html
    assert r"- \frac{3 \pi}{4}" not in html
    assert b.phase_series == a.series


def test_affine_sine_equality_retains_both_overlapping_parent_branches():
    a = analysis(case("681577"))
    assert a.argument_pair is not None and a.sine_pair is None
    assert a.series == ((-sp.Rational(3, 2), 2), (sp.Rational(7, 6), sp.Rational(2, 3)))
    assert set(select((a.series[0],), (0, 2, True, False))[0]) <= set(
        select((a.series[1],), (0, 2, True, False))[0]
    )
    text = BeautifulSoup(plan(case("681577")).solution_html, "html.parser").get_text(
        " "
    )
    assert "аргументы" in text and "противоположный" in text
    assert "дискриминант" not in text and "формулу произведения" not in text


def test_equal_or_opposite_affine_slopes_are_rejected_without_invented_series():
    with pytest.raises(UnsupportedCondition, match="nonzero bounded slopes"):
        compile_pair(r"\sin(x+\frac{\pi}{2})-\sin(x+\pi)=0")


def test_negative_left_hand_x_is_not_mistaken_for_an_affine_root_family():
    assert affine_families(r'<span data-inline-latex="-x=7\pi/2+2\pi k"></span>') == ()


def test_original_nonmonomial_pole_and_open_upper_root_are_both_excluded():
    a = analysis(case("694272"))
    assert a.branches[0].angle_shift == sp.Rational(1, 3)
    assert a.series == ((-sp.Rational(1, 2), sp.Integer(2)),)
    assert a.bounds == (-sp.Rational(3, 2), sp.Rational(7, 2), True, False)
    assert sp.Rational(7, 2) not in a.selected
    assert sp.Rational(11, 6) not in a.residues
    assert a.poles


@pytest.mark.parametrize("task", ["654843", "654932"])
def test_selected_source_markers_keep_original_svg_bytes_and_colors(task):
    example = case(task)
    asset = example["context"]["normalized_content"]["assets"][0]
    entry = CIRCLES[asset["asset_id"]]
    raw = gzip.decompress((DIRECTORY / (asset["asset_id"] + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    nodes = list(ET.fromstring(raw).iter())
    native = entry["native_ellipse"]
    (marker,) = entry["selected_markers"]
    for shape in (native, marker):
        assert (
            any(n.get("d") == shape["path_d"] for n in nodes)
            if "path_d" in shape
            else any(dict(n.attrib) == shape["element"] for n in nodes)
        )
    cx, cy = native["center"]
    rx, ry = native["radii"]
    q = float(sp.Rational(marker["angle"])) * math.pi
    assert (
        math.hypot(
            marker["x"] - cx - rx * math.cos(q), marker["y"] - cy + ry * math.sin(q)
        )
        < 1
    )
    assert marker["color"] == ("blue" if task == "654843" else "green")
    assert entry["point_scope"] == "selected"
    assert tuple(map(sp.Rational, entry["labels"])) == analysis(example).selected
    assert "corrected_file" not in entry


def test_incompatible_parent_cosine_phase_does_not_override_the_exact_identity():
    example = case("672849")
    _, f, i, b = read(example["context"])
    changed = parent(example).replace(
        r"\cos (x+\frac{\pi}{4})", r"\cos (x+\frac{\pi}{6})"
    )
    assert changed != parent(example)
    a = analyze(f, i, b, changed)
    assert a.branches[0].angle_shift != sp.Rational(1, 6)
    assert select(a.series, (0, 2, True, False))[0] == (0, sp.Rational(3, 2))


def test_opposite_affine_slopes_do_not_create_a_division_by_zero_family():
    with pytest.raises(UnsupportedCondition, match="nonzero bounded slopes"):
        compile_pair(r"\sin(x+\frac{\pi}{2})-\sin(-x+\pi)=0")
