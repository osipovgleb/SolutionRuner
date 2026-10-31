"""Exact angle addition extends the same rule and repairs only proven SVG defects."""

import gzip
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
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_addition.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "520783": "-2 -1 -5/6",
    "520821": "-4 -7/2 -5/2",
    "520802": "-19/6 -3 -2",
    "520852": "2 3 19/6",
    "520878": "5/2 7/2 11/3",
    "520906": "7/2 9/2 14/3",
    "520831": "-3 -2 -11/6",
    "520845": "3 4 17/4",
    "520868": "2 3 10/3",
    "514519": "-7/3",
    "526324": "13/4 15/4",
    "527157": "5/4 7/4",
    "701603": "-19/6",
    "530824": "13/4 15/4 17/4",
    "515762": "9/8 5/4 11/8",
    "530899": "-19/6 -17/6 -13/6",
}
RESIDUES = {
    "520783": "0 1 7/6 11/6",
    "520821": "0 1/2 3/2",
    "520802": "0 1/6 5/6 1",
    "520852": "0 1 7/6 11/6",
    "520878": "1/3 1/2 3/2 5/3",
    "520906": "1/2 2/3 4/3 3/2",
    "520831": "0 1/6 5/6 1",
    "520845": "0 1/4 3/4 1",
    "520868": "0 1 4/3 5/3",
    "514519": "4/3 5/3",
    "526324": "5/4 7/4",
    "527157": "5/4 7/4",
    "701603": "1/6 5/6",
    "530824": "1/4 3/4 5/4 7/4",
    "515762": "1/8 1/4 3/8 5/8 3/4 7/8 9/8 5/4 11/8 13/8 7/4 15/8",
    "530899": "1/6 5/6 7/6 11/6",
}
ORIGINAL = {
    "520783": 2 * sp.sin(X) ** 2 + sp.sqrt(2) * sp.sin(X + sp.pi / 4) - sp.cos(X),
    "520821": sp.cos(X) ** 2 + sp.sin(X) - sp.sqrt(2) * sp.sin(X + sp.pi / 4),
    "520802": sp.sin(X)
    + 2 * sp.sin(2 * X + sp.pi / 6)
    - sp.sqrt(3) * sp.sin(2 * X)
    - 1,
    "520852": 2 * sp.sin(2 * X + sp.pi / 3)
    - sp.sqrt(3) * sp.sin(X)
    - sp.sin(2 * X)
    - sp.sqrt(3),
    "520878": 2 * sp.sin(2 * X + sp.pi / 6)
    - sp.cos(X)
    - sp.sqrt(3) * sp.sin(2 * X)
    + 1,
    "520906": sp.sqrt(2) * sp.sin(sp.pi / 4 + X) + sp.cos(2 * X) - sp.sin(X) + 1,
    "520831": 2 * sp.sin(X + sp.pi / 3) + sp.cos(2 * X) - sp.sqrt(3) * sp.cos(X) - 1,
    "520845": sp.sqrt(6) * sp.sin(X) ** 2 + sp.cos(X) - 2 * sp.sin(X + sp.pi / 6),
    "520868": 2 * sp.sqrt(3) * sp.sin(X + sp.pi / 3)
    - sp.cos(2 * X)
    - 3 * sp.cos(X)
    + 1,
    "514519": 8 * sp.sin(X) ** 2 + 2 * sp.sqrt(3) * sp.cos(3 * sp.pi / 2 - X) - 9,
    "526324": 2 * sp.sin(X) ** 2 + 3 * sp.sqrt(2) * sp.cos(3 * sp.pi / 2 + X) + 2,
    "527157": 6 * sp.cos(X) ** 2 + 5 * sp.sqrt(2) * sp.sin(X) + 2,
    "701603": 6 * sp.cos(X) ** 2 - 5 * sp.sin(X) - 2,
    "530824": 4 * sp.cos(X) ** 4 + 9 * sp.cos(2 * X) - 1,
    "515762": 4 * sp.sin(2 * X) ** 4 + 3 * sp.cos(4 * X) - 1,
    "530899": 8 * sp.cos(X) ** 4 + 3 * sp.cos(2 * X) - 6,
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for s in case(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def prepared(c):
    return tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in get_handler(
            get_group_profile(c["group"]).content_rule_key
        ).diagram_specs(c["context"])
    )


def plan(c, context=None, generated=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c),
            generated_solution_assets=prepared(c) if generated is None else generated,
        )
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_the_same_rule_at_the_original_catalog_position(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 4, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_independent_complete_and_selected_roots_satisfy_original_equations(c):
    a = analysis(c)
    expected = tuple(map(sp.Rational, RESIDUES[c["task"]].split()))
    assert select(a.series, (sp.Integer(0), sp.Integer(2), True, False))[0] == expected
    assert a.selected == tuple(map(sp.Rational, SELECTED[c["task"]].split()))
    for q in (*expected, *a.selected):
        assert sp.simplify(ORIGINAL[c["task"]].subs(X, q * sp.pi)) == 0
    denominator = 24 if c["task"] == "515762" else 12
    grid = tuple(
        sp.Rational(i, denominator)
        for i in range(2 * denominator)
        if sp.simplify(ORIGINAL[c["task"]].subs(X, sp.pi * i / denominator)) == 0
    )
    assert grid == expected


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_condition_and_source_assets(c):
    ctx = deepcopy(c["context"])
    before = deepcopy(ctx)
    p = plan(c, ctx)
    assert ctx == before
    assert p.condition_html == next(
        s["html"]
        for s in ctx["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>UNUSED9999</p>"
    assert plan(c, ctx) == p
    for t in p.transformations:
        key = t["transformation_target_id"]
        if key.startswith("asset:"):
            ctx["normalized_content"]["assets"].append(t["value"])
        else:
            assert key.startswith(("section:answer", "section:solution"))
            next(
                s
                for s in ctx["normalized_content"]["sections"]
                if s["transformation_target_id"] == key
            ).update(t["value"])
    assert plan(c, ctx).transformations == ()
    for asset in before["normalized_content"]["assets"]:
        assert asset in ctx["normalized_content"]["assets"]
    assert "Примечание" not in p.solution_html
    if c["task"] in ("520802", "520878", "527157"):
        assert len(prepared(c)) == 1
        with pytest.raises(UnsupportedCondition):
            plan(c, generated=())
    else:
        assert prepared(c) == ()


@pytest.mark.parametrize("task", ["520878", "701603"])
def test_selected_only_circle_does_not_remove_other_equation_roots(task):
    c = case(task)
    a = analysis(c)
    entry = deepcopy(
        CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    )
    assert entry["point_scope"] == "selected"
    validate(entry, a)
    assert len(a.residues) > len(entry["residues"])
    entry["point_scope"] = "all"
    with pytest.raises(UnsupportedCondition):
        validate(entry, a)
    entry["point_scope"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        validate(entry, a)


@pytest.mark.parametrize(
    "q", [sp.Rational(1, 12), sp.Rational(-1, 6), sp.Rational(1, 4), sp.Rational(1, 3)]
)
def test_shifted_atoms_are_exact_addition_identities(q):
    formula = r"\sin(x+" + sp.latex(q * sp.pi) + ")=0"
    e = compile_reviewed(formula, S, sp.Integer(1))
    assert sp.expand(e.raw - (S * sp.cos(q * sp.pi) + C * sp.sin(q * sp.pi))) == 0


@pytest.mark.parametrize(
    "formula",
    [
        r"\sin(x+\frac{\pi}{5})=0",
        r"\sin(x+\sqrt{2})=0",
        r"\sin(5x)+\cos x=0",
        r"\tg(x+\frac{\pi}{4})=0",
    ],
)
def test_unreviewed_shift_multiple_and_function_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, S, sp.Integer(1))


def test_scalable_delimiters_and_spacing_do_not_change_the_condition():
    for task in ("520821", "520831"):
        c = case(task)
        condition = next(
            s["html"]
            for s in c["context"]["normalized_content"]["sections"]
            if s["key"] == "condition"
        )
        assert r"\left[" in condition and plan(c).condition_html == condition


def test_quartic_parent_keeps_factoring_and_strictly_positive_factors():
    for task in ("530824", "530899"):
        html = plan(case(task)).solution_html
        assert "отрицательный дискриминант" in html
        assert any(
            ">0" in s["data-inline-latex"]
            for s in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
        )
    a = analysis(case("515762"))
    html = plan(case("515762")).solution_html
    assert a.scale == 2 and a.factorization and "u=" not in html
    assert r"(\cos 2 x)" in html


def test_only_the_four_broken_minus_glyphs_are_replaced_by_paths():
    c = case("520802")
    identifier = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[identifier]
    old = ET.fromstring(
        gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    )
    new = ET.fromstring(prepared(c)[0]["svg_text"])
    assert entry["repaired_minus_count"] == 4
    assert len([e for e in old.iter() if (e.text or "").strip() == "−"]) == 4
    assert len([e for e in new.iter() if e.get("data-source-text") == "−"]) == 4
    assert not [e for e in new.iter() if (e.text or "").strip() == "−"]
    old_paths = {e.get("d") for e in old.iter() if e.tag.endswith("path")}
    new_paths = {e.get("d") for e in new.iter() if e.tag.endswith("path")}
    assert old_paths < new_paths and len(new_paths - old_paths) <= 4
    text = lambda root: sorted(
        (e.text or "").strip()
        for e in root.iter()
        if e.tag.endswith(("text", "tspan"))
        and (e.text or "").strip()
        and e.text.strip() != "−"
    )
    assert text(old) == text(new)


@pytest.mark.parametrize("task", ["520878", "527157"])
def test_prepared_markers_and_outlines_have_the_exact_required_angles(task):
    c = case(task)
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    root = ET.fromstring(prepared(c)[0]["svg_text"])
    paths = {e.get("d"): e for e in root.iter() if e.tag.endswith("path")}
    cx, cy, _ = entry["circle"]
    radius = entry["prepared_radius"]
    assert len(entry["prepared_markers"]) == (2 if task == "520878" else 4)
    for p in entry["prepared_markers"]:
        node = paths[p["path_d"]]
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([-\d.]+) ([-\d.]+)\)", node.get("transform")
            ).groups(),
        )
        angle = float(sp.Rational(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] + dx - cx - radius * math.cos(angle),
                p["y"] + dy - cy + radius * math.sin(angle),
            )
            < 1e-7
        )
        assert node.get("data-angle") == p["angle"]
