"""Safe squaring retains original signs, poles, zero radicals and branch parameters."""

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
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import decode
from solution_runner.pipelines.equations.exam_trigonometric_radical_equation import (
    compile_radical,
)
from solution_runner.pipelines.equations.exam_trigonometric_safe_square import (
    parameter_roles,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_safe_square.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
PHI = sp.S.Half + sp.acos(sp.Rational(2, 3)) / sp.pi
ORIGINAL = {
    "537133": sp.sqrt(sp.sin(X) ** 2 + 3 * sp.sin(X) - sp.Rational(17, 9)) + sp.cos(X),
    "539879": sp.sqrt(sp.sin(X) ** 2 + sp.sqrt(3) * sp.sin(X) + 1) - sp.cos(X),
    "562249": sp.sin(X) - sp.sqrt((sp.sqrt(3) * sp.cos(X) + 2) / 2),
    "633557": sp.cos(X) + sp.sqrt((2 - sp.sqrt(2)) * (sp.sin(X) + 1) / 2),
    "639333": sp.sqrt(2 + sp.sqrt(6) - (6 * sp.sqrt(2) - 2 * sp.sqrt(3)) * sp.sin(X))
    - 2 * sp.sin(X)
    + sp.sqrt(2),
    "676856": sp.sqrt(1 - sp.sin(X / 2) * sp.cos(X / 2)) - sp.sin(5 * sp.pi / 2 + X),
    "676933": sp.sqrt(1 + sp.sin(X / 2) * sp.cos(X / 2)) - sp.sin(3 * sp.pi / 2 - X),
    "679330": sp.sqrt(sp.cos(X) ** 2 - sp.cos(X)) / sp.sin(X) - 1,
}
EXPECTED = {
    "537133": ((PHI,), (PHI - 2, PHI)),
    "539879": (("0", "5/3"), ("-1/3", "0")),
    "562249": (("1/2", "5/6"), ("-7/6",)),
    "633557": (("3/4", "3/2"), ("-21/4", "-9/2")),
    "639333": (("1/3", "2/3"), ("-4/3",)),
    "676856": (("0", "1/6"), ("-4", "-23/6")),
    "676933": (("1", "7/6"), ("3", "19/6")),
    "679330": (("2/3",), ("-10/3", "-4/3")),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(example):
    return next(
        s["html"]
        for s in case(example["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example, context=None):
    _, f, i, b = read(context or example["context"])
    return analyze(f, i, b, parent(example))


def plan(example, context=None):
    return get_handler(get_group_profile(example["group"]).content_rule_key).plan(
        PlanInput(context or example["context"], parent_solution_html=parent(example))
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_uses_the_existing_rule_and_exact_catalog_coordinates(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"], "14")


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_full_series_and_interval_roots_satisfy_the_original_equation(example):
    key = example["task"]
    a = analysis(example)
    full, selected = (tuple(map(sp.sympify, row)) for row in EXPECTED[key])
    assert select(a.series, (sp.S.Zero, sp.Integer(2), True, False))[0] == full
    assert a.selected == selected
    assert a.radical_equation.kind == "safe_square"
    for q in (*full, *selected):
        assert sp.simplify(ORIGINAL[key].subs(X, q * sp.pi)) == 0
    value = sp.lambdify(X, ORIGINAL[key], modules="math")
    window = select(a.series, (-2, 2, True, True))[0]
    for k in range(-48, 49):
        q = sp.Rational(k, 24)
        try:
            actual = abs(value(float(q) * math.pi)) < 1e-7
        except (ValueError, ZeroDivisionError):
            actual = False
        assert (q in window) == actual, (key, q)


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_plans_ignore_saved_answers_and_child_solutions_and_replay_is_idempotent(
    example,
):
    original = deepcopy(example["context"])
    p = plan(example)
    assert original == example["context"]
    context = deepcopy(original)
    for sec in context["normalized_content"]["sections"]:
        if sec["key"] in ("answer", "solution"):
            sec["html"] = "<p>Не использовать.</p>"
    other = plan(example, context)
    assert (other.answer, other.solution_html) == (p.answer, p.solution_html)
    for t in p.transformations:
        target = t["transformation_target_id"]
        assert not target.startswith(("asset:", "section:condition"))
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["transformation_target_id"] == target
        ).update(t["value"])
    assert plan(example, context).transformations == ()
    assets = original["normalized_content"]["assets"]
    images = BeautifulSoup(p.solution_html, "html.parser").find_all("img")
    assert len(images) == len(assets)
    if assets:
        assert images[0]["src"] == assets[0]["url"]
    assert (
        get_handler(get_group_profile(example["group"]).content_rule_key).diagram_specs(
            original
        )
        == ()
    )


def test_child_changes_angles_but_retains_the_parents_zero_and_nonzero_branch_letters():
    e = case("676933")
    a = analysis(e)
    assert a.series == ((sp.S.One, sp.Integer(2)), (sp.Rational(-5, 6), sp.Integer(2)))
    assert a.family_parameters == ("k", "m")
    assert a.radical_equation.parameters == ("k", "m", "n")
    p = plan(e)
    nodes = formulas(p.solution_html)
    assert r"x=2 \pi n - \frac{\pi}{6},\quad n\in\mathbb Z" in nodes
    assert r"x=2 \pi m - \frac{5 \pi}{6},\quad m\in\mathbb Z" in nodes
    selection = BeautifulSoup(p.solution_html, "html.parser").find(
        "li", attrs={"data-list-marker": "б)"}
    )
    assert any("k" in f for f in formulas(str(selection)))
    assert any("m" in f for f in formulas(str(selection)))
    assert not any("n" in f.replace(r"\in", "") for f in formulas(str(selection)))
    assert r"k,m\in\mathbb Z" in p.answer
    assert "19" in p.answer


def test_zero_radical_boundary_is_retained_and_parent_root_scope_is_repaired():
    e = case("633557")
    a = analysis(e)
    assert sp.Rational(3, 2) in a.residues
    assert a.radical_equation.radicand.subs(S, -1) == 0
    nodes = formulas(plan(e).solution_html)
    assert any(
        r"\text{подкоренное выражение}=0" in f and r"\text{правая часть}=0" in f
        for f in nodes
    )
    assert nodes[0] == read(e["context"])[1]
    assert r"\sqrt{\frac{2-\sqrt{2}}{2}}\cdot" not in " ".join(nodes)


def test_original_sine_pole_is_checked_before_clearing_or_squaring():
    e = case("679330")
    a = analysis(e)
    assert a.poles == (S,) and a.radical_equation.cleared == S
    assert sp.S.One in a.branches[0].excluded
    nodes = formulas(plan(e).solution_html)
    assert nodes.index(r"(\sin x)\ne0") < nodes.index(r"(\sin x)> 0")
    assert nodes.index(r"(\sin x)> 0") < next(
        i for i, f in enumerate(nodes) if f.startswith(r"\sqrt{(")
    )
    assert r"\text{исходный знаменатель}=0" in nodes


def test_inverse_sine_uses_existing_exact_bounds_and_parent_arcsine_display():
    e = case("537133")
    a = analysis(e)
    p = plan(e)
    assert a.sine_inverse and a.series == ((PHI, sp.Integer(2)),)
    assert a.selection_method == "circle"
    assert r"\arcsin" in p.answer and r"\arccos" not in p.answer
    assert any("- \\frac{13}{6}" in f for f in formulas(p.solution_html))


@pytest.mark.parametrize("key", ["537133", "539879", "562249", "633557", "639333"])
def test_native_figures_keep_all_valid_markers_and_crossed_candidates(key):
    e = case(key)
    asset = e["context"]["normalized_content"]["assets"][0]
    entry = CIRCLES[asset["asset_id"]]
    raw = gzip.decompress((DIRECTORY / (asset["asset_id"] + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    nodes = list(ET.fromstring(raw).iter())
    cx, cy, _ = entry["circle"]
    for point in entry["green_markers"] + entry["excluded_markers"]:
        if "path_d" in point:
            assert any(n.get("d") == point["path_d"] for n in nodes)
        else:
            assert any(dict(n.attrib) == point["element"] for n in nodes)
        angle = float(decode(point["angle"])) * math.pi
        radius = point["radius"]
        assert (
            math.hypot(
                point["x"] - cx - radius * math.cos(angle),
                point["y"] - cy + radius * math.sin(angle),
            )
            < 5
        )
    assert (
        len(entry["green_markers"])
        == {"537133": 3, "539879": 4, "562249": 2, "633557": 2, "639333": 1}[key]
    )
    assert (
        len(entry["excluded_markers"])
        == {"537133": 1, "539879": 2, "562249": 2, "633557": 1, "639333": 0}[key]
    )
    assert "corrected_file" not in entry
    validate(entry, analysis(e))
    if key == "562249":
        assert "1/2" in {m["angle"] for m in entry["green_markers"]}
    if key == "639333":
        assert entry["point_scope"] == "selected"


def test_crossed_marker_must_fail_an_actual_original_restriction():
    e = case("539879")
    entry = deepcopy(
        CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    )
    entry["excluded_markers"][0]["angle"] = "0"
    with pytest.raises(UnsupportedCondition, match="every crossed"):
        validate(entry, analysis(e))


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{1-\sin\frac{x}{2}}=\cos x",
        r"\sqrt{1+\sin\frac{x}{2}\cos\frac{3x}{2}}=\cos x",
        r"\sqrt{1+\sin^3x}=\cos x",
        r"\sqrt{1+\sin x}=\cos^2x",
        r"\frac{\sqrt{\cos^2x-\cos x}}{\sin x+1}=1",
        r"\sqrt{1+\sin 13x}=\cos x",
    ],
)
def test_unreviewed_half_angles_degrees_and_poles_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_radical(formula, "safe_square")


def test_ambiguous_parent_parameter_roles_fail_closed():
    html = parent(case("676933")).replace(r"2\pi m", r"2\pi k")
    with pytest.raises(UnsupportedCondition):
        parameter_roles(html)


def test_half_angle_pair_and_square_identities_remain_exact():
    e = compile_radical(
        r"\sqrt{1-\sin\frac{x}{2}\cos\frac{x}{2}}=\cos x", "safe_square"
    )
    assert e.radical_equation.radicand == 1 - S / 2
    e = compile_radical(r"\sqrt{2\sin^2\frac{x}{2}}=\sin x", "safe_square")
    assert e.radical_equation.radicand == 1 - C
    assert e.poles == ()
