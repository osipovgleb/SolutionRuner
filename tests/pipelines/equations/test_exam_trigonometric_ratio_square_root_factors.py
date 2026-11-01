"""Parent square levels, independent parameters and a vanishing whole root factor."""

import gzip
import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import replace
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
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S, T, U
from solution_runner.pipelines.equations.exam_trigonometric_radical_product import (
    admissible_factor,
    cases,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_ratio_square_root_factors.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
ORIGINAL = {
    "630661": (
        (3 * (S / C) ** 2 - 1) / (2 * S + 1),
        (C, 2 * S + 1),
        (),
        (R(1, 6), R(5, 6)),
        (R(13, 6), R(17, 6)),
    ),
    "630669": (
        (3 * (S / C) ** 2 - 1) / (2 * S - 1),
        (C, 2 * S - 1),
        (),
        (R(7, 6), R(11, 6)),
        (R(19, 6), R(23, 6)),
    ),
    "642003": (
        (3 * (C / S) ** 2 - 1) / (2 * C + 1),
        (S, 2 * C + 1),
        (),
        (R(1, 3), R(5, 3)),
        (-R(7, 3), -R(5, 3)),
    ),
    "642021": (
        ((C / S) ** 2 - 3) / (2 * S - 1),
        (S, 2 * S - 1),
        (),
        (R(7, 6), R(11, 6)),
        (-R(17, 6), -R(13, 6)),
    ),
    "653512": (
        (2 * S * C - S) * (sp.sqrt(2) - sp.sqrt(-2 * C / S)),
        (S,),
        ((-2 * C / S, False),),
        (R(3, 4), R(5, 3), R(7, 4)),
        (-R(19, 3), -R(25, 4)),
    ),
    "701089": (
        (4 * S**4 + 10 * S * S - 6) / sp.sqrt(-S),
        (),
        ((-S, True),),
        (R(5, 4), R(7, 4)),
        (-R(11, 4),),
    ),
}


def case(key):
    return next(e for e in CASES if e["task"] == key)


def parent(e):
    return section(case(e["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(e, context=None):
    _, formula, interval, bounds = read(context or e["context"])
    return analyze(formula, interval, bounds, parent(e))


def generated(e, context=None):
    h = get_handler(get_group_profile(e["group"]).content_rule_key)
    return tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(context or e["context"])
    )


def plan(e, context=None):
    ctx = context or e["context"]
    return get_handler(get_group_profile(e["group"]).content_rule_key).plan(
        PlanInput(
            ctx,
            parent_solution_html=parent(e),
            generated_solution_assets=generated(e, ctx),
        )
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_profiles_extend_the_shared_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"], "14")


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_full_and_selected_roots_follow_the_original_equation_and_domain(e):
    a = analysis(e)
    expr, poles, domain, full, selected = ORIGINAL[e["task"]]
    assert select(a.series, (sp.S.Zero, sp.Integer(2), True, False))[0] == full
    assert a.selected == selected
    for q in (*full, *selected):
        sub = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        assert all(sp.simplify(p.subs(sub)) != 0 for p in poles)
        assert all(
            sp.simplify(d.subs(sub)) > (0 if strict else -R(1, 10**12))
            for d, strict in domain
        )
        assert sp.simplify(expr.subs(sub)) == 0
    value = sp.lambdify((S, C), expr, "math")
    pv = [sp.lambdify((S, C), p, "math") for p in poles]
    dv = [(sp.lambdify((S, C), d, "math"), strict) for d, strict in domain]
    window = select(a.series, (-4, 4, True, True))[0]
    for k in range(-96, 97):
        q = R(k, 24)
        si, co = math.sin(float(q) * math.pi), math.cos(float(q) * math.pi)
        si = 0.0 if abs(si) < 1e-12 else si
        co = 0.0 if abs(co) < 1e-12 else co
        valid = all(abs(p(si, co)) > 1e-9 for p in pv)
        valid = valid and all(
            d(si, co) > (1e-9 if strict else -1e-9) for d, strict in dv
        )
        actual = valid and abs(value(si, co)) < 1e-8
        assert (q in window) == actual, (e["task"], q)


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_saved_answers_are_unused_and_local_replay_is_idempotent(e):
    before = deepcopy(e["context"])
    p = plan(e)
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>Не использовать.</p>"
    assert plan(e, ctx) == p
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        if key.startswith("asset:"):
            assert e["task"] == "642021" and t["operation"] == "add"
            ctx["normalized_content"]["assets"].append(t["value"])
        else:
            next(
                s
                for s in ctx["normalized_content"]["sections"]
                if s["transformation_target_id"] == key
            ).update(t["value"])
    assert plan(e, ctx).transformations == ()
    assert section(ctx["normalized_content"], "condition") == section(
        before["normalized_content"], "condition"
    )
    assert (
        ctx["normalized_content"]["assets"][:1]
        == before["normalized_content"]["assets"]
    )
    assert e["context"] == before
    assert len(generated(e)) == (1 if e["task"] == "642021" else 0)


@pytest.mark.parametrize(
    "key,variable,level",
    [
        ("630661", T, R(1, 3)),
        ("630669", T, R(1, 3)),
        ("642003", U, R(1, 3)),
        ("642021", U, sp.Integer(3)),
    ],
)
def test_parent_square_level_is_shown_without_a_discriminant(key, variable, level):
    e = case(key)
    a = analysis(e)
    b = a.branches[0]
    html = plan(e).solution_html
    assert b.variable == variable and b.square_level
    assert (
        sp.simplify(-b.polynomial.subs(variable, 0) / b.polynomial.coeff(variable, 2))
        == level
    )
    assert "Выразим квадрат функции" in html and "D=" not in html
    assert "исходный знаменатель в нуль" in html


@pytest.mark.parametrize(
    "key,wanted",
    [
        ("630661", ((R(1, 6), 2), (R(5, 6), 2))),
        ("630669", ((-R(1, 6), 2), (-R(5, 6), 2))),
        ("642003", ((-R(1, 3), 2), (R(1, 3), 2))),
        ("642021", ((-R(5, 6), 2), (-R(1, 6), 2))),
    ],
)
def test_parent_family_order_and_child_negative_offsets_are_preserved(key, wanted):
    assert analysis(case(key)).series == wanted


@pytest.mark.parametrize("key", ["642003", "642021"])
def test_independent_integer_parameters_are_bound_in_both_final_families(key):
    e = case(key)
    a = analysis(e)
    p = plan(e)
    assert a.family_parameters == ("k", "n")
    nodes = formulas(p.solution_html)
    named = [
        f
        for f in nodes
        if f.startswith("x=") and re.search(r"(?<![A-Za-z])n(?![A-Za-z])", f)
    ]
    assert named and all(r"n\in\mathbb Z" in f for f in named)
    assert all(r"k\in\mathbb Z" not in f for f in named)
    assert "q" not in re.sub(r"\\[A-Za-z]+", "", " ".join(nodes))
    assert r"k,n\in\mathbb Z" in p.answer


def test_vanishing_whole_root_factor_keeps_both_parent_cases_and_original_poles():
    e = case("653512")
    a = analysis(e)
    root, first = cases(a, a.preferred, a.allow_inverse)
    assert a.radical_product.root_offset == -sp.sqrt(2)
    assert a.poles == (S,) and admissible_factor(a) == (2 * C - 1, S)
    assert root[0].variable == U and root[0].values == (-sp.S.One,)
    assert set(root[0].residues) == {R(3, 4), R(7, 4)}
    assert first[0].residues == (R(5, 3),)
    html = plan(e).solution_html
    assert "вся скобка с корнем" in html and r"\sqrt{- (\ctg x)}=1" in html
    assert "Нулевой радикал сам по себе не обращает" in html
    assert "скобка строго положительна" not in html
    assert "Исходный знаменатель равен нулю" not in html


def test_biquadratic_parent_method_keeps_negative_square_level_and_strict_denominator():
    e = case("701089")
    a = analysis(e)
    html = plan(e).solution_html
    nodes = formulas(html)
    assert a.centered_power[0:2] == (S, sp.S.Zero)
    assert r"(\sin x)^{2}=-3" in nodes
    assert "0\\le u\\le1" in html and "биквадратное" in html
    assert r"- (\sin x)>0" in nodes
    assert r"(\sin x)=- \frac{\sqrt{2}}{2}" in nodes
    assert r"(\sin x)=\frac{\sqrt{2}}{2}" in nodes
    assert "Квадрат синуса или косинуса лежит от 0 до 1" in html


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_all_original_svg_bytes_and_native_markers_match_the_model(e):
    a = analysis(e)
    aid = e["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    validate(entry, a)
    svg = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == entry["sha256"]
    root = ET.fromstring(svg)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    assert entry["native_circle_path"] in paths
    cx, cy, _ = entry["circle"]
    full = ORIGINAL[e["task"]][3]
    for p in entry["green_markers"]:
        assert p["path_d"] in paths and p["native_circle_path"] in paths
        angle = float(R(p["angle"])) * math.pi
        distance = math.hypot(
            p["x"] - cx - p["radius"] * math.cos(angle),
            p["y"] - cy + p["radius"] * math.sin(angle),
        )
        assert R(p["angle"]) in full
        if p.get("inaccurate"):
            assert entry["corrected_file"] and distance > 5
        else:
            assert distance < 5
    for p in entry.get("excluded_markers", []):
        assert p["path_d"] in paths
        assert e["task"] == "653512" and R(p["angle"]) == R(1, 3)
        sub = {S: sp.sin(R(p["angle"]) * sp.pi), C: sp.cos(R(p["angle"]) * sp.pi)}
        assert sp.simplify((-2 * C / S).subs(sub)) < 0


def test_corrected_child_figure_moves_both_fill_and_outline_of_exactly_two_markers():
    e = case("642021")
    aid = e["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    old = ET.fromstring(gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes()))
    new = ET.fromstring((DIRECTORY / entry["corrected_file"]).read_bytes())
    assert old.attrib == new.attrib
    expected = {
        path: p for p in entry["corrected_markers"] for path in p["source_paths"]
    }
    assert len(expected) == 4 and len(list(old.iter())) == len(list(new.iter()))
    count = 0
    for a, b in zip(old.iter(), new.iter()):
        assert a.tag == b.tag
        assert a.text == b.text or not ((a.text or "") + (b.text or "")).strip()
        assert a.tail == b.tail or not ((a.tail or "") + (b.tail or "")).strip()
        if a.get("d") in expected:
            p = expected[a.get("d")]
            assert b.attrib == {**a.attrib, "transform": p["transform"]}
            count += 1
        else:
            assert a.attrib == b.attrib
    assert count == 4
    cx, cy, radius = entry["circle"]
    for p, source in zip(entry["corrected_markers"], entry["green_markers"]):
        dx, dy = map(
            float,
            re.fullmatch(r"translate\(([^ ]+) ([^)]+)\)", p["transform"]).groups(),
        )
        assert math.isclose(source["x"] + dx, p["x"], abs_tol=1e-9) and math.isclose(
            source["y"] + dy, p["y"], abs_tol=1e-9
        )
        angle = float(R(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - cx - radius * math.cos(angle),
                p["y"] - cy + radius * math.sin(angle),
            )
            < 1e-9
        )
        assert 5 < math.hypot(dx, dy) < 10


def test_blue_three_quarter_circle_and_native_axes_define_the_biquadratic_figure():
    e = case("701089")
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    root = ET.fromstring(
        gzip.decompress(
            (
                DIRECTORY
                / (
                    e["context"]["normalized_content"]["assets"][0]["asset_id"]
                    + ".svgz"
                )
            ).read_bytes()
        )
    )
    axes = entry["native_axes"]
    assert len(axes) == 2 and all(
        any(n.tag.endswith("line") and n.attrib == a for n in root.iter()) for a in axes
    )
    vertical = next(a for a in axes if a["x1"] == a["x2"])
    horizontal = next(a for a in axes if a["y1"] == a["y2"])
    assert entry["circle"][:2] == [float(vertical["x1"]), float(horizontal["y1"])]
    tokens = re.findall(r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)", entry["native_circle_path"])
    assert tokens.pop(0) == "M"
    current = complex(float(tokens.pop(0)), float(tokens.pop(0)))
    ends = [[current.real, current.imag]]
    while tokens:
        cmd = tokens.pop(0)
        assert cmd in ("c", "S", "s")
        n = 6 if cmd == "c" else 4
        values = [float(tokens.pop(0)) for _ in range(n)]
        end = complex(*values[-2:])
        current = end if cmd == "S" else current + end
        ends.append([current.real, current.imag])
    assert len(ends) == 4
    assert all(
        math.dist(a, b) < 1e-9 for a, b in zip(ends, entry["native_quarter_endpoints"])
    )
    assert math.isclose(
        entry["circle"][2],
        (max(p[0] for p in ends) - min(p[0] for p in ends)) / 2,
        abs_tol=1e-9,
    )


def test_prepared_child_correction_requires_its_exact_local_model_hash():
    e = case("642021")
    h = get_handler(get_group_profile(e["group"]).content_rule_key)
    g = deepcopy(generated(e))
    g[0]["sha256"] = "wrong"
    with pytest.raises(UnsupportedCondition):
        h.plan(
            PlanInput(
                e["context"],
                parent_solution_html=parent(e),
                generated_solution_assets=g,
            )
        )


@pytest.mark.parametrize("e", CASES, ids=lambda e: e["task"])
def test_unknown_source_and_changed_interval_are_rejected(e):
    ctx = deepcopy(e["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(e, ctx)
    a = analysis(e)
    entry = CIRCLES[e["context"]["normalized_content"]["assets"][0]["asset_id"]]
    with pytest.raises(UnsupportedCondition):
        validate(
            entry, replace(a, bounds=(sp.Integer(-10), sp.Integer(10), True, True))
        )
