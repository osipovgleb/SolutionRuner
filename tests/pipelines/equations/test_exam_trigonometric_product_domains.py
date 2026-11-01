"""Linear radical domains, commuted factors and zero cotangent on native figures."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import (
    all_group_profiles,
    get_group_profile,
)
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
from solution_runner.pipelines.equations.exam_trigonometric_radical_product import (
    cases,
    compile_product,
    operands,
)
from solution_runner.pipelines.equations.exam_trigonometric_radical_product_proof import (
    homogeneous_domain,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_product_domains.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
ORIGINAL = {
    "512356": (2 * C * C + S - 2, 5 * S / C, (C,)),
    "544273": (-2 * S * S + 3 * S - 1, C - S, ()),
    "546442": (S * S - R(1, 4), C / S, (S,)),
    "548180": (C / S - sp.sqrt(3), S - C, (S,)),
    "621853": (2 * C * C + C - 1, S - C, ()),
    "626816": (2 * C * C + 3 * C + 1, S / C - 1, (C,)),
}
EXPECTED = {
    "512356": ("0 1/6 1", "1 2 13/6"),
    "544273": ("1/6 1/4 5/4", "1/6 1/4"),
    "546442": ("1/6 1/2 7/6 3/2", "-3/2 -5/6 -1/2"),
    "548180": ("1/4 7/6 5/4", "9/4"),
    "621853": ("1/4 1/3 1 5/4", "1/4 1/3"),
    "626816": ("1/4 5/4 4/3", "5/4 4/3"),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(e):
    return next(
        s["html"]
        for s in e["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(e, context=None):
    _, f, i, b = read(context or e["context"])
    return analyze(f, i, b, parent(e))


def plan(e, context=None):
    return get_handler(get_group_profile(e["group"]).content_rule_key).plan(
        PlanInput(context or e["context"], parent_solution_html=parent(e))
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_registration_extends_the_existing_rule(g):
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
def test_full_series_and_interval_roots_satisfy_the_original_equation(e):
    key = e["task"]
    a = analysis(e)
    full, selected = (tuple(map(R, row.split())) for row in EXPECTED[key])
    assert select(a.series, (sp.S.Zero, sp.Integer(2), True, False))[0] == full
    assert a.selected == selected
    polynomial, radicand, poles = ORIGINAL[key]
    for q in (*full, *selected):
        sub = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        assert all(sp.simplify(p.subs(sub)) != 0 for p in poles)
        assert sp.simplify((polynomial * sp.sqrt(radicand)).subs(sub)) == 0
    value = sp.lambdify((S, C), (polynomial, radicand), "math")
    window = select(a.series, (-4, 4, True, True))[0]
    for k in range(-96, 97):
        q = R(k, 24)
        si, co = math.sin(float(q) * math.pi), math.cos(float(q) * math.pi)
        if (S in poles and abs(si) < 1e-10) or (C in poles and abs(co) < 1e-10):
            actual = False
        else:
            pv, rv = value(si, co)
            actual = rv >= -1e-10 and (abs(rv) < 1e-10 or abs(pv) < 1e-10)
        assert (q in window) == actual, (key, q)


@pytest.mark.parametrize("e", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_sources(e):
    before = deepcopy(e["context"])
    ctx = deepcopy(before)
    p = plan(e)
    assert e["context"] == before
    for sec in ctx["normalized_content"]["sections"]:
        if sec["key"] in ("answer", "solution"):
            sec["html"] = "<p>Не использовать.</p>"
    assert plan(e, ctx) == p
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith(("asset:", "section:condition"))
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        ).update(t["value"])
    assert plan(e, ctx).transformations == ()
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert (
        get_handler(get_group_profile(e["group"]).content_rule_key).diagram_specs(
            before
        )
        == ()
    )
    image = BeautifulSoup(p.solution_html, "html.parser").find("img")
    assert image["src"] == before["normalized_content"]["assets"][0]["url"]


def test_cotangent_zero_is_a_valid_root_and_the_first_factor_stays_a_sine_square():
    e = case("546442")
    a = analysis(e)
    assert a.poles == (S,)
    assert a.series == ((sp.S.Half, sp.S.One), (R(1, 6), sp.S.One))
    assert a.branches[0].variable == C and a.branches[1].variable == S
    assert a.branches[1].square_level
    assert a.radical_product.radicand == C / S
    assert {sp.S.Half, R(3, 2)} <= set(a.residues)
    assert "(\\sin x)^{2}=\\frac{1}{4}" in formulas(plan(e).solution_html)
    assert not any(
        "Нулевое подкоренное выражение" in text for text in [plan(e).solution_html]
    )


@pytest.mark.parametrize(
    "key,lower,upper",
    [
        ("544273", R(-3, 4), R(1, 4)),
        ("621853", R(1, 4), R(5, 4)),
        ("548180", R(1, 4), R(5, 4)),
    ],
)
def test_homogeneous_domain_keeps_the_full_closed_interval(key, lower, upper):
    nodes = formulas(plan(case(key)).solution_html)
    from solution_runner.pipelines.equations.exam_trigonometric_proof import pi

    expected = (
        pi(lower) + r"+2\pi n\le x\le " + pi(upper) + r"+2\pi n,\quad n\in\mathbb Z"
    )
    assert expected in nodes
    assert any(r"\sin\left(" in f and "=" in f for f in nodes)


def test_affine_tangent_domain_checks_the_accepted_series_with_periodicity_and_oddness():
    e = case("626816")
    a = analysis(e)
    p = plan(e)
    nodes = formulas(p.solution_html)
    assert a.poles == (C,) and a.radical_product.radicand == (S - C) / C
    assert r"(\tg x)\ge 1" in nodes
    compact = " ".join("".join(f.split()) for f in nodes)
    assert r"\tg\left(-\frac{2\pi}{3}+2\pi k\right)".replace(" ", "") in compact
    assert any(r"\sqrt{3}" in f and ">0" in f for f in nodes)
    assert "периодичность" in p.solution_html and "нечётность" in p.solution_html
    assert a.series == ((R(1, 4), sp.S.One), (R(-2, 3), sp.Integer(2)))


def test_final_parent_family_order_is_distinct_from_the_order_of_zero_cases():
    assert analysis(case("544273")).series == (
        (R(1, 6), sp.Integer(2)),
        (R(1, 4), sp.S.One),
    )
    assert analysis(case("621853")).series == (
        (R(1, 4), sp.S.One),
        (R(1, 3), sp.Integer(2)),
        (sp.S.One, sp.Integer(2)),
    )


@pytest.mark.parametrize("e", CASES, ids=lambda c: c["task"])
def test_all_native_markers_intersections_and_pole_crosses_are_preserved(e):
    asset = e["context"]["normalized_content"]["assets"][0]
    entry = CIRCLES[asset["asset_id"]]
    raw = gzip.decompress((DIRECTORY / (asset["asset_id"] + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    root = ET.fromstring(raw)
    nodes = list(root.iter())
    paths = {n.get("d") for n in nodes if n.tag.endswith("path")}
    cx, cy, _ = entry["circle"]
    assert entry["native_circle_path"] in paths
    for point in entry["green_markers"] + entry["excluded_markers"]:
        if "native_lines" in point:
            assert all(
                any(n.tag.endswith("line") and dict(n.attrib) == attrs for n in nodes)
                for attrs in point["native_lines"]
            )
        else:
            assert point["path_d"] in paths
        if "intersection_axis" in point:
            axis = point["intersection_axis"]
            assert any(n.tag.endswith("line") and dict(n.attrib) == axis for n in nodes)
            assert abs(point["x"] - float(axis["x1"])) < 1e-8
            assert (
                min(float(axis["y1"]), float(axis["y2"]))
                < point["y"]
                < max(float(axis["y1"]), float(axis["y2"]))
            )
        q = float(R(point["angle"])) * math.pi
        assert (
            math.hypot(
                point["x"] - cx - point["radius"] * math.cos(q),
                point["y"] - cy + point["radius"] * math.sin(q),
            )
            < 5
        )
    validate(entry, analysis(e))
    assert "corrected_file" not in entry


def test_blue_boundary_and_implicit_axis_intersection_both_represent_zero_cotangent_roots():
    e = case("546442")
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    roots = entry["green_markers"]
    assert len(roots) == 4
    assert {R(p["angle"]) for p in roots if p.get("boundary_marker")} == {
        sp.S.Half,
        R(3, 2),
    }
    assert len([p for p in roots if "intersection_axis" in p]) == 1
    assert {R(p["angle"]) for p in roots} == set(analysis(e).residues)
    assert R(1, 6) not in {R(q) % 2 for q in entry["labels"]}
    assert [p["angle"] for p in entry["excluded_markers"]] == ["0"]


def test_original_sine_poles_are_required_even_where_the_linear_radicand_is_positive():
    e = case("548180")
    a = analysis(e)
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    assert a.poles == (S,)
    assert {p["angle"] for p in entry["excluded_markers"] if p.get("pole_marker")} == {
        "0",
        "1",
    }
    with pytest.raises(UnsupportedCondition, match="every crossed"):
        validate(entry, replace(a, poles=()))


@pytest.mark.parametrize("key", ["621853", "626816"])
def test_selected_only_figures_keep_a_separate_certificate_of_every_full_root(key):
    e = case(key)
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    assert entry["point_scope"] == "selected"
    assert tuple(map(R, entry["complete_residues"])) == analysis(e).residues
    assert len(entry["residues"]) < len(entry["complete_residues"])


def test_dividing_by_cosine_in_the_zero_case_does_not_add_an_original_cosine_pole():
    compiled = compile_product(r"\cos x", r"\sin x-\cos x")
    zero, positive = cases(compiled, S, False)
    assert compiled.poles == ()
    assert {q for b in zero for q in b.residues} == {R(1, 4), R(5, 4)}
    assert {q for b in positive for q in b.residues} == {sp.S.Half}


@pytest.mark.parametrize(
    "formula",
    [
        r"(\sin x)\sqrt{\cos x}=0",
        r"\sqrt{\cos x}(\sin x)=0",
        r"\sqrt{\cos x}\cdot(\sin x)=0",
        r"(\sin x)(\sqrt{\cos x})=0",
        r"(\sqrt{\cos x})(\sin x)=0",
    ],
)
def test_only_the_order_of_the_two_product_factors_changes(formula):
    assert operands(formula) == (r"\sinx", r"\cosx")


@pytest.mark.parametrize(
    "formula",
    [
        r"(\sin x)(\sqrt{\cos x}+1)=0",
        r"\sqrt{\cos x}+(\sin x)=0",
        r"\sqrt{\cos x}(\sin x)=1",
    ],
)
def test_additive_radical_factors_are_not_misread_as_a_plain_product(formula):
    assert operands(formula) is None


@pytest.mark.parametrize(
    "radicand",
    [
        r"\sin x+1",
        r"\sin x-\cos x+1",
        r"\frac{\sin x-\cos x}{\sin x+\cos x}",
        r"\sin^2x",
    ],
)
def test_nonhomogeneous_or_unreviewed_rational_domains_fail_closed(radicand):
    with pytest.raises(UnsupportedCondition):
        compile_product(r"\sin x", radicand)


def test_unreviewed_halfplane_phase_fails_closed_before_rendering():
    with pytest.raises(UnsupportedCondition, match="reviewed exact phase"):
        homogeneous_domain(S - 2 * C)


def test_conflicting_parent_scope_is_recorded_and_never_registered_from_its_answer():
    (g,) = DATA["rejected_sources"]
    assert g["group"]["key"] == "507428"
    ctx = g["tasks"][0]["context"]
    condition = next(
        s["html"]
        for s in ctx["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    solution = next(
        s["html"]
        for s in ctx["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    assert r"\sqrt{-\sin x-1}" in formulas(condition)[0]
    assert any(r"\sqrt{-\sin x}-1" in f for f in formulas(solution))
    assert "507428" not in all_group_profiles()
    assert -sp.sin(4 * sp.pi / 3) - 1 < 0
    with pytest.raises(UnsupportedCondition):
        compile_product(r"2\cos x+1", r"-\sin x-1")


@pytest.mark.parametrize("e", CASES, ids=lambda c: c["task"])
def test_unknown_source_and_changed_bounds_cannot_reuse_the_original_circle(e):
    ctx = deepcopy(e["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        read(ctx)
    a = analysis(e)
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    with pytest.raises(UnsupportedCondition):
        validate(
            entry, replace(a, bounds=(a.bounds[0], a.bounds[1] + 1, *a.bounds[2:]))
        )


def test_positive_constant_in_an_affine_tangent_radicand_keeps_both_zero_cases():
    compiled = compile_product(r"\sin x", r"\tg x+1")
    zero, positive = cases(compiled, S, False)
    assert compiled.poles == (C,)
    assert {q for b in zero for q in b.residues} == {R(3, 4), R(7, 4)}
    assert {q for b in positive for q in b.residues} == {sp.S.Zero, sp.S.One}
