"""Ratio domains and mixed zero factors preserve complete root sets and source style."""

import gzip
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    C,
    S,
    T,
    U,
    analyze,
    compile_equation,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    angles,
    level_series,
)
from solution_runner.pipelines.equations.exam_trigonometric_ratios import linear_branch
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_ratios.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "548478": "3 10/3 11/3 4",
    "548806": "2 7/3 8/3 3",
    "549031": "-7/2 -13/4 -11/4 -5/2",
    "548556": "-5/2 -3/2 -4/3",
    "505416": "-15/4 -7/2 -5/2",
    "672870": "14/3",
    "672899": "-7/3",
    "548563": "5/2 7/2 11/3",
    "548493": "3/2 5/2 8/3",
    "548800": "-7/3 -2 -5/3",
    "548807": "-10/3 -3 -8/3",
    "548851": "11/6 5/2",
    "552930": "-31/6 -25/6",
    "556336": "-3 -2 -5/3",
    "505470": "2 13/6 3",
    "505492": "-4 -15/4 -3",
    "556445": "-5 -4 -15/4",
}
RESIDUES = {
    "548478": "0 1 4/3 5/3",
    "548806": "0 1/3 2/3 1",
    "549031": "1/2 3/4 5/4 3/2",
    "548556": "1/2 2/3 4/3 3/2",
    "505416": "1/4 1/2 3/2 7/4",
    "672870": "2/3 4/3",
    "672899": "1/3 5/3",
    "548563": "1/3 1/2 3/2 5/3",
    "548493": "1/2 2/3 4/3 3/2",
    "548800": "0 1/3 5/3",
    "548807": "2/3 1 4/3",
    "548851": "1/2 7/6 11/6",
    "552930": "5/6 11/6",
    "556336": "0 1/3 2/3 1",
    "505470": "0 1/6 1 7/6",
    "505492": "0 1/4 1 5/4",
    "556445": "0 1/4 3/4 1",
}
ORIGINAL = {
    "548478": 2 * sp.cos(3 * sp.pi / 2 + X) ** 2 + sp.sqrt(3) * sp.sin(X),
    "548806": 2 * sp.sin(X) ** 2 - sp.sqrt(3) * sp.cos(sp.pi / 2 - X),
    "549031": 2 * sp.sin(sp.pi / 2 - X) ** 2 + sp.sqrt(2) * sp.cos(X),
    "548556": sp.cos(2 * X) + sp.sin(sp.pi / 2 + X) + 1,
    "505416": sp.cos(2 * X) - sp.sqrt(2) * sp.sin(sp.pi / 2 - X) + 1,
    "672870": 3 * sp.cos(2 * X) - 7 * sp.sin(sp.pi / 2 + X) - 2,
    "672899": 2 * sp.cos(2 * X) - 8 * sp.sin(3 * sp.pi / 2 - X) - 3,
    "548563": sp.cos(2 * X) - sp.sin(sp.pi / 2 + X) + 1,
    "548493": sp.cos(2 * X) + sp.sin(sp.pi / 2 - X) + 1,
    "548800": 1 / sp.cos(X) ** 2 - 3 / sp.cos(X) + 2,
    "548807": 1 / sp.cos(X) ** 2 + 3 / sp.cos(X) + 2,
    "548851": 1 / sp.sin(X) ** 2 + 1 / sp.sin(X) - 2,
    "552930": sp.cot(X) ** 2
    + 2 * sp.sqrt(3) * sp.cot(X)
    + 3 * sp.sin(X) ** 2
    + 3 * sp.sin(X - 3 * sp.pi / 2) ** 2,
    "556336": 2 * sp.cos(3 * sp.pi / 2 + X) ** 2 - sp.sqrt(3) * sp.sin(X),
    "505470": 2 * sp.sqrt(3) * sp.cos(3 * sp.pi / 2 + X) ** 2 - sp.sin(2 * X),
    "505492": 2 * sp.cos(3 * sp.pi / 2 + X) ** 2 - sp.sin(2 * X),
    "556445": 2 * sp.cos(sp.pi / 2 + X) ** 2 - sp.sqrt(2) * sp.sin(X),
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
def test_registration_extends_existing_rule_and_preserves_catalog_position(g):
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
def test_independently_written_equations_have_the_expected_full_and_selected_roots(c):
    a = analysis(c)
    expected = tuple(map(sp.Rational, RESIDUES[c["task"]].split()))
    assert select(a.series, (sp.Integer(0), sp.Integer(2), True, False))[0] == expected
    assert a.selected == tuple(map(sp.Rational, SELECTED[c["task"]].split()))
    for q in (*expected, *a.selected):
        assert sp.simplify(ORIGINAL[c["task"]].subs(X, q * sp.pi)) == 0
    grid = []
    for i in range(24):
        x = sp.pi * i / 12
        if c["task"] in ("548800", "548807") and sp.cos(x) == 0:
            continue
        if c["task"] in ("548851", "552930") and sp.sin(x) == 0:
            continue
        if sp.simplify(ORIGINAL[c["task"]].subs(X, x)) == 0:
            grid.append(sp.Rational(i, 12))
    assert tuple(grid) == expected


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
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
    if c["task"] in ("548478", "549031", "556445"):
        assert len(prepared(c)) == 1
        with pytest.raises(UnsupportedCondition):
            plan(c, generated=())
    else:
        assert prepared(c) == ()


@pytest.mark.parametrize("task", ["505470", "505492"])
def test_mixed_linear_factor_preserves_zero_sine_and_justifies_cosine_division(task):
    a = analysis(case(task))
    assert len(a.branches) == 2
    assert {b.variable for b in a.branches} == {S, T}
    assert a.branches[0].variable == S
    mixed = next(b for b in a.branches if b.variable == T)
    assert mixed.original is not None and mixed.original.free_symbols == {S, C}
    assert 0 in a.residues and 1 in a.residues
    html = plan(case(task)).solution_html
    assert (
        "только в этой ветви можно разделить на косинус" in html
        and r"\cos(x)\ne0" in html
    )
    assert r"(\sin x)=0" in html and r"(\tg x)" in html
    assert html.index(r"(\sin x)=0") < html.index("Рассмотрим линейный множитель")


def test_reciprocal_child_changes_function_without_changing_the_parent_method():
    a = analysis(case("548851"))
    assert a.preferred == S and set(a.poles) == {S, S * S}
    html = plan(case("548851")).solution_html
    assert r"(\sin x)\ne0" in html and r"t=\frac{1}{(\sin x)}" in html
    assert r"t=\frac{1}{(\cos x)}" not in html


def test_cotangent_domain_and_full_square_are_kept_in_the_original_order():
    a = analysis(case("552930"))
    assert a.preferred == U and a.square
    assert sp.expand(a.reduced - (U + sp.sqrt(3)) ** 2) == 0
    html = plan(case("552930")).solution_html
    assert (
        html.index(r"\sin x\ne0")
        < html.index("полный квадрат")
        < html.index(r"(\ctg x)=-")
    )
    assert "cotangent" not in html and r"\ctg" in html
    assert r"\sin((x-\frac{3\pi}{2}))=(\cos x)" in html
    assert level_series(U, 0) == ((sp.Rational(1, 2), sp.Integer(1)),)
    assert angles(U, sp.sqrt(3)) == (sp.Rational(1, 6), sp.Rational(7, 6))
    assert all(sp.sin(q * sp.pi) != 0 for q in a.residues)


@pytest.mark.parametrize(
    "formula",
    [
        r"\ctg 2x=0",
        r"\ctg(x+\frac{\pi}{2})=0",
        r"\ctg x+\sin x=0",
        r"\ctg x+\tg x=0",
        r"\frac{\ctg x}{\ctg x}=1",
    ],
)
def test_unreviewed_cotangent_grammar_fails_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_equation(formula)


@pytest.mark.parametrize("expression", [S + C + 1, S * C + S, S * S + C * C])
def test_nonhomogeneous_or_nonlinear_mixed_factors_are_not_divided(expression):
    assert linear_branch(expression) is None


def test_only_extra_green_boundary_marker_is_removed_and_blue_marker_survives():
    c = case("548478")
    identifier = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[identifier]
    old = ET.fromstring(
        gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    )
    new = ET.fromstring(prepared(c)[0]["svg_text"])
    original = list(old.iter())
    fixed = list(new.iter())
    removed = set(entry["removed_green_paths"])
    assert len(removed) == 2
    assert [e.attrib for e in original if e.get("d") not in removed] == [
        e.attrib for e in fixed
    ]
    extra = next(m for m in entry["green_markers"] if m.get("extra_marker"))
    assert extra["angle"] == "1/2"
    assert sp.simplify(ORIGINAL[c["task"]].subs(X, sp.pi / 2)) != 0
    assert not removed & {e.get("d") for e in fixed}
    assert any(e.get("fill") == "#00487E" for e in fixed)
    assert "1/2" not in entry["residues"]


def test_only_the_nonroot_boundary_label_changes_color():
    c = case("549031")
    identifier = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[identifier]
    old = ET.fromstring(
        gzip.decompress((DIRECTORY / (identifier + ".svgz")).read_bytes())
    )
    new = ET.fromstring(prepared(c)[0]["svg_text"])
    changed = set(entry["recolored_boundary_paths"])
    assert len(changed) == 3
    for a, b in zip(old.iter(), new.iter()):
        assert a.tag == b.tag
        if a.get("d") in changed:
            assert b.get("fill") == "#00487E"
            assert {
                k: v for k, v in a.attrib.items() if k not in ("fill", "style")
            } == {k: v for k, v in b.attrib.items() if k not in ("fill", "style")}
        else:
            assert a.attrib == b.attrib


def test_wrong_sixth_turn_marker_is_moved_to_the_quarter_turn_with_its_outline():
    c = case("556445")
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    root = ET.fromstring(prepared(c)[0]["svg_text"])
    paths = {e.get("d"): e for e in root.iter() if e.tag.endswith("path")}
    cx, cy, radius = entry["circle"]
    assert len(entry["prepared_markers"]) == 2
    for p in entry["prepared_markers"]:
        e = paths[p["path_d"]]
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([-\d.]+) ([-\d.]+)\)", e.get("transform")
            ).groups(),
        )
        assert e.get("data-angle") == "1/4"
        assert (
            math.hypot(
                p["x"] + dx - cx - radius / math.sqrt(2),
                p["y"] + dy - cy + radius / math.sqrt(2),
            )
            < 1e-7
        )
    assert entry["point_scope"] == "selected"


def test_crossed_root_outside_interval_is_not_removed_from_the_general_answer():
    a = analysis(case("548493"))
    assert sp.Rational(4, 3) in a.residues
    assert all(q % 2 != sp.Rational(4, 3) for q in a.selected)


def test_cotangent_square_parent_adapts_to_a_linear_equivalent_condition():
    from bs4 import BeautifulSoup

    c = case("552930")
    ctx = deepcopy(c["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    soup.select_one("[data-inline-latex]")["data-inline-latex"] = r"\ctg x+\sqrt{3}=0"
    condition["html"] = str(soup)
    result = plan(c, ctx)
    assert result.answer == plan(c).answer
    assert "Получили полный квадрат" not in result.solution_html
    assert r"\sin x\ne0" in result.solution_html
