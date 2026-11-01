"""Parent absolute substitutions, mixed linear branches and native SVG corrections."""

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
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_square_radicals import (
    compile_squares,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_square_variants.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
ORIGINAL = {
    "560933": sp.sqrt(sp.sin(X / 2) ** 2 + 2 * sp.sin(X / 2) + 1)
    - sp.sqrt((4 * sp.sin(X / 2) - 6) ** 2)
    + sp.Rational(5, 2),
    "677434": sp.sqrt(1 - c * c) + sp.sqrt(3) * sp.cos(2 * X),
    "692900": s - c - sp.sqrt(1 + sp.sin(2 * X)) + 1,
}
EXPECTED = {
    "560933": ("1/3 5/3", "1/3"),
    "677434": ("1/3 2/3 4/3 5/3", "-2/3 -1/3 1/3"),
    "692900": ("1/3 7/6", "-5/6 1/3"),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(example):
    return next(
        s["html"]
        for s in example["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example):
    _, f, i, b = read(example["context"])
    return analyze(f, i, b, parent(example))


def plan(example, context=None):
    ctx = context or example["context"]
    handler = get_handler(get_group_profile(example["group"]).content_rule_key)
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
            ctx,
            parent_solution_html=parent(example),
            generated_solution_assets=generated,
        )
    )


def replay(context, changes):
    for transformation in changes:
        key = transformation["transformation_target_id"]
        items = context["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(transformation["value"])


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_uses_the_shared_rule_and_exact_catalog_coordinates(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"], "14")


@pytest.mark.parametrize("example", CASES, ids=lambda e: e["task"])
def test_complete_and_selected_roots_follow_original_equations(example):
    key = example["task"]
    a = analysis(example)
    assert select(a.series, (0, 2, True, False))[0] == tuple(
        map(sp.Rational, EXPECTED[key][0].split())
    )
    assert a.selected == tuple(map(sp.Rational, EXPECTED[key][1].split()))
    period = 4 if key == "560933" else 2
    full = select(a.series, (0, period, True, False))[0]
    for q in (*full, *a.selected):
        assert sp.simplify(ORIGINAL[key].subs(X, q * sp.pi)) == 0
    value = sp.lambdify(X, ORIGINAL[key], modules="math")
    window = select(a.series, (-2, 2, True, True))[0]
    for k in range(-48, 49):
        q = sp.Rational(k, 24)
        assert (q in window) == (abs(value(float(q) * math.pi)) < 1e-8)


@pytest.mark.parametrize("example", CASES, ids=lambda e: e["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(example):
    original = deepcopy(example["context"])
    p = plan(example)
    assert example["context"] == original
    changed = deepcopy(original)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>Не использовать.</p>"
    other = plan(example, changed)
    assert (other.answer, other.solution_html) == (p.answer, p.solution_html)
    assert not any(
        t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    replay(changed, p.transformations)
    assert plan(example, changed).transformations == ()
    old_assets = original["normalized_content"]["assets"]
    assert changed["normalized_content"]["assets"][: len(old_assets)] == old_assets
    if example["task"] == "560933":
        assert any(
            t["transformation_target_id"] == "asset:exam_trig_circle"
            for t in p.transformations
        )
    else:
        assert not any(
            t["transformation_target_id"].startswith("asset:")
            for t in p.transformations
        )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def test_absolute_level_keeps_nonnegative_substitution_and_compact_parent_families():
    e = case("677434")
    a = analysis(e)
    p = plan(e)
    d = a.square_radicals
    assert d.method == "absolute_level"
    assert set(d.candidates[0]) == {-sp.sqrt(3) / 3, sp.sqrt(3) / 2}
    assert d.accepted == (sp.sqrt(3) / 2,)
    assert a.series == (
        (sp.Rational(-1, 3), sp.Integer(1)),
        (sp.Rational(1, 3), sp.Integer(1)),
    )
    fs = formulas(p.solution_html)
    assert any(r"t=\left|\sin(" in f and r"0\le t\le1" in f for f in fs)
    assert any("6 t^{2}" in f and r"\sqrt{3}" in f for f in fs)
    assert "не может быть модулем синуса" in p.solution_html
    uid = e["context"]["normalized_content"]["assets"][0]["asset_id"]
    assert "/assets/" + uid in p.solution_html
    assert len(CIRCLES[uid]["green_markers"]) == 4
    assert sp.Rational(2, 3) not in a.selected


def test_second_module_retains_both_parent_branches_and_half_angle_is_exact():
    e = case("560933")
    a = analysis(e)
    p = plan(e)
    d = a.square_radicals
    assert a.scale == sp.Rational(1, 2)
    assert d.method == "remaining_absolute" and d.signs == (1, 0)
    assert d.candidates == ((sp.Rational(19, 6),), (sp.Rational(1, 2),))
    assert d.accepted == (sp.Rational(1, 2),)
    assert a.series == (
        (sp.Rational(1, 3), sp.Integer(4)),
        (sp.Rational(5, 3), sp.Integer(4)),
    )
    assert "Для второго сохраним обе ветви" in p.solution_html
    assert any("19" in f for f in formulas(p.solution_html))
    assert a.selection_method == "circle"


def test_mixed_square_checks_every_linear_branch_and_corrects_the_wrong_cosine_angle():
    e = case("692900")
    a = analysis(e)
    p = plan(e)
    d = a.square_radicals
    assert d.method == "linear_absolute" and d.linears == (S + C,)
    assert a.residues == (sp.Rational(1, 3), sp.Rational(7, 6))
    assert a.series == (
        (sp.Rational(1, 3), sp.Integer(2)),
        (sp.Rational(-5, 6), sp.Integer(2)),
    )
    assert a.selection_method == "neighbors"
    assert "Правая часть отрицательна" in p.solution_html
    assert not any(
        f.replace(" ", "") == r"x=-\frac{\pi}{2}" for f in formulas(p.solution_html)
    )
    assert len(d.cases) == 2 and all(
        sp.Poly(p, S, C).total_degree() == 1 for p in d.cases
    )


@pytest.mark.parametrize("task", ["560933", "677434"])
def test_native_svg_bytes_and_every_marker_have_independent_geometry(task):
    e = case(task)
    uid = e["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[uid]
    raw = gzip.decompress((DIRECTORY / (uid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    root = ET.fromstring(raw)
    cx, cy, radius = entry["circle"]
    for marker in entry["green_markers"]:
        assert any(n.get("d") == marker["path_d"] for n in root.iter())
        angle = float(sp.Rational(marker["angle"])) * math.pi
        distance = math.hypot(
            marker["x"] - cx - radius * math.cos(angle),
            marker["y"] - cy + radius * math.sin(angle),
        )
        assert distance > 5 if marker.get("inaccurate") else distance < 1


def test_half_angle_figure_moves_only_the_selected_marker_and_its_outline():
    e = case("560933")
    uid = e["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[uid]
    original = ET.fromstring(
        gzip.decompress((DIRECTORY / (uid + ".svgz")).read_bytes())
    )
    corrected = ET.fromstring((DIRECTORY / entry["corrected_file"]).read_text())
    assert len(list(original.iter())) == len(list(corrected.iter()))
    moved = []
    for before, after in zip(original.iter(), corrected.iter()):
        attrs = dict(after.attrib)
        if attrs != before.attrib:
            transform = attrs.pop("transform")
            assert attrs == before.attrib and (
                before.get("fill") == "#007A37" or before.get("stroke") == "#007A37"
            )
            dx, dy = map(
                float, transform.removeprefix("translate(").removesuffix(")").split()
            )
            moved.append((dx, dy))
        assert (before.text or "").strip() == (after.text or "").strip()
        assert before.tag == after.tag
    assert len(moved) == 2 and moved[0] == moved[1]
    marker = entry["green_markers"][0]
    cx, cy, r = entry["circle"]
    assert (
        math.hypot(
            marker["x"] + moved[0][0] - cx - r / 2,
            marker["y"] + moved[0][1] - cy + r * math.sqrt(3) / 2,
        )
        < 1e-6
    )


@pytest.mark.parametrize("task", ["560933", "677434"])
def test_unknown_svg_or_changed_interval_fail_closed(task):
    e = case(task)
    changed = deepcopy(e["context"])
    changed["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(e, changed)
    changed = deepcopy(e["context"])
    sec = next(
        s for s in changed["normalized_content"]["sections"] if s["key"] == "condition"
    )
    sec["html"] = (
        sec["html"].replace(r"\frac{3\pi}{2}", r"\frac{5\pi}{2}")
        if task == "560933"
        else sec["html"].replace(r"\frac{\pi}{2}", r"\frac{3\pi}{2}")
    )
    with pytest.raises(UnsupportedCondition):
        plan(e, changed)


def test_reviewed_methods_reject_incompatible_algebra_and_keep_other_coefficients():
    for f, method in (
        (r"\sqrt{(\sin x+1/2)^2}=1", "absolute_level"),
        (r"\sqrt{(\sin x+\cos x)^2}=\sin x+\cos x", "linear_absolute"),
    ):
        with pytest.raises(UnsupportedCondition):
            compile_squares(f, method)
    c = compile_squares(
        r"\sqrt{(\sin 0.5x+1)^2}-\sqrt{(3\sin 0.5x-5)^2}=-2", "remaining_absolute"
    )
    assert c.scale == sp.Rational(1, 2) and c.square_radicals.accepted == (
        sp.Rational(1, 2),
    )


def test_zero_absolute_level_is_not_lost():
    compiled = compile_squares(r"\sqrt{\sin^2 x}+\sin^2 x=0", "absolute_level")
    assert compiled.square_radicals.accepted == (sp.S.Zero,)
    assert compiled.raw == S * S


def test_original_unstructured_figure_remains_before_part_a():
    example = case("560933")
    source = BeautifulSoup(parent(example), "html.parser")
    assert source.find("img").find_parent("li") is None
    assert analysis(example).image_position == "outside"
    soup = BeautifulSoup(plan(example).solution_html, "html.parser")
    assert soup.find("img").find_parent("li") is None
    assert soup.find("img").find_next("ol") is not None
