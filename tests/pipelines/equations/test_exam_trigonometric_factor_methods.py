"""Parent factorization, local cotangent domains, and independent angle scales."""

import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_angle_product import (
    compile_product,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S, U
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    decode,
    ordered,
)
from solution_runner.pipelines.equations.exam_trigonometric_linear_phase import branch
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_factor_methods.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {
    "532052": "-8/3 -7/3 -13/6",
    "541378": "-7/6 -5/6",
    "541822": "7/3",
    "548424": "-4 -15/4 -3",
    "548814": "7/2 15/4 9/2",
    "552113": "-1/2 1/3",
    "553312": "-9/10 -5/6 -7/10 -1/2 -3/10 -1/6 -1/10 1/10 1/6 3/10",
}
RESIDUES = {
    "532052": "1/6 4/3 5/3 11/6",
    "541378": "5/6 7/6",
    "541822": "1/3 5/3",
    "548424": "0 1/4 1 5/4",
    "548814": "1/2 3/4 3/2 7/4",
    "552113": "1/3 1/2 3/2",
    "553312": "1/10 1/6 3/10 1/2 7/10 5/6 9/10 11/10 7/6 13/10 3/2 17/10 11/6 19/10",
}
ORIGINAL = {
    "532052": sp.sin(2 * X) + sp.sqrt(3) * (c - s) - sp.Rational(3, 2),
    "541378": 2 * c**3 + sp.sqrt(3) * c**2 + 2 * c + sp.sqrt(3),
    "541822": 2 * c**3 - c**2 + 2 * c - 1,
    "548424": 2 * sp.cos(3 * sp.pi / 2 + X) ** 2 - sp.sin(2 * X),
    "548814": 2 * sp.sin(sp.pi / 2 - X) ** 2 + sp.sin(2 * X),
    "552113": sp.cot(X) - s - sp.sqrt(3) * c + 1 / s,
    "553312": sp.cos(3 * X) - sp.sin(7 * X - sp.pi / 2) - sp.cos(5 * X),
}
FACTORED = {
    "532052": (2 * c - sp.sqrt(3)) * (2 * s + sp.sqrt(3)) / 2,
    "541378": (c * c + 1) * (2 * c + sp.sqrt(3)),
    "541822": (c * c + 1) * (2 * c - 1),
    "548424": 2 * s * (s - c),
    "548814": 2 * c * (c + s),
    "552113": c * (c - sp.sqrt(3) * s + 1) / s,
    "553312": sp.cos(5 * X) * (2 * sp.cos(2 * X) - 1),
}


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
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_existing_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 6, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_independent_original_equations_full_root_sets_and_interval_selection(c):
    task = c["task"]
    a = analysis(c)
    expression = (
        ORIGINAL[task].xreplace({sp.cot(X): sp.cos(X) / sp.sin(X)}) - FACTORED[task]
    )
    numerator = sp.together(expression).as_numer_denom()[0]
    assert sp.trigsimp(sp.expand(sp.expand_trig(numerator))) == 0
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    assert select(a.series, (0, 2, True, False))[0] == tuple(
        map(sp.Rational, RESIDUES[task].split())
    )
    for root in a.selected:
        assert sp.simplify(sp.expand_trig(ORIGINAL[task].subs(X, root * sp.pi))) == 0
    if task == "552113":
        assert all(sp.sin(q * sp.pi) != 0 for q in a.selected)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    before = deepcopy(c["context"])
    p = plan(c)
    assert c["context"] == before
    changed = deepcopy(before)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>не использовать</p>"
    assert (
        plan(c, changed).answer == p.answer
        and plan(c, changed).solution_html == p.solution_html
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        kind = "assets" if key.startswith("asset:") else "sections"
        items = changed["normalized_content"][kind]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, changed).transformations == ()
    assert (
        changed["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_exact_source_figures_include_open_boundaries_and_crossed_markers(c):
    a = analysis(c)
    asset = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[asset]
    svg = gzip.decompress((DIRECTORY / (asset + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == e["sha256"]
    paths = {n.get("d"): n for n in ET.fromstring(svg).iter() if n.tag.endswith("path")}
    assert ordered(
        decode(m["angle"]) for m in e["green_markers"] + e.get("boundary_markers", [])
    ) == tuple(map(sp.Rational, RESIDUES[c["task"]].split()))
    assert tuple(decode(q) for q in e["labels"]) == a.selected
    for m in e["green_markers"] + e.get("boundary_markers", []):
        assert m["path_d"] in paths
    if c["task"] == "552113":
        m = e["boundary_markers"][0]
        assert m["open"] and paths[m["path_d"]].get("fill") == "#FFFFFF"
    if c["task"] == "553312":
        assert (
            next(m for m in e["green_markers"] if m["angle"] == "1/2")[
                "selection_status"
            ]
            == "open_boundary"
            and sp.Rational(1, 2) not in a.selected
        )
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            c["context"]
        )
        == ()
    )


@pytest.mark.parametrize("task", ["541378", "541822"])
def test_cubic_keeps_the_common_quadratic_before_the_affine_factor(task):
    a = analysis(case(task))
    b = a.branches[0]
    assert b.grouping and b.quadratic_common
    html = plan(case(task)).solution_html
    assert "Сгруппируем слагаемые" in html and "отрицательный дискриминант" in html
    assert r"\left((\cos x)^{2} + 1\right)" in html


def test_two_affine_factors_preserve_the_parents_grouping():
    a = analysis(case("532052"))
    assert next(b.variable for b in a.branches if b.grouping) == S
    assert "Сгруппируем слагаемые" in plan(case("532052")).solution_html


def test_cosine_zero_precedes_only_local_cotangent_division():
    a = analysis(case("548814"))
    assert a.homogeneous is None
    assert a.branches[0].variable == C and a.branches[0].values == (0,)
    assert a.branches[1].variable == U and a.branches[1].values == (-1,)
    assert a.series == ((sp.Rational(1, 2), 1), (sp.Rational(3, 4), 1))
    html = plan(case("548814")).solution_html
    assert (
        "только в этой ветви разделим на синус" in html
        and "(\\sin x)^{2}\\ne0" not in html
    )


def test_clearing_the_original_sine_denominator_filters_shifted_physical_roots():
    a = analysis(case("552113"))
    assert a.poles == (S,) and a.cleared_denominator == S
    b = next(b for b in a.branches if b.angle_shift)
    assert (
        b.variable == C
        and b.angle_shift == sp.Rational(1, 3)
        and b.values == (-sp.Rational(1, 2),)
    )
    assert b.residues == (sp.Rational(1, 3),) and sp.Integer(1) not in a.residues
    html = plan(case("552113")).solution_html
    assert html.index("область определения") < html.index("Умножим уравнение")
    assert (
        "косинуса суммы" in html
        and "Эта серия нарушает исходную область определения" in html
    )


def test_product_retains_separate_five_and_two_angle_series_and_open_endpoints():
    a = analysis(case("553312"))
    assert tuple(b.angle_scale for b in a.branches) == (5, 2)
    assert a.series == (
        (sp.Rational(1, 10), sp.Rational(1, 5)),
        (sp.Rational(1, 6), 1),
        (sp.Rational(5, 6), 1),
    )
    assert a.bounds == (-1, sp.Rational(1, 2), False, False)
    assert sp.Rational(1, 2) not in a.selected and sp.Rational(-1, 2) in a.selected
    assert "своим углом" in plan(case("553312")).solution_html


@pytest.mark.parametrize(
    "level",
    [
        1,
        -1,
        sp.Rational(1, 2),
        -sp.Rational(1, 2),
        sp.sqrt(2) / 2,
        -sp.sqrt(2) / 2,
        sp.sqrt(3) / 2,
        -sp.sqrt(3) / 2,
    ],
)
def test_shifted_linear_table_levels_reconstruct_every_root(level):
    b = branch(sp.sqrt(3) * S + C - 2 * level)
    assert b is not None and b.candidates == (level,)
    for q in b.residues:
        assert (
            sp.simplify(sp.sqrt(3) * sp.sin(q * sp.pi) + sp.cos(q * sp.pi) - 2 * level)
            == 0
        )


@pytest.mark.parametrize(
    "formula",
    [
        r"\cos 3x+\cos 7x+1=0",
        r"\cos 13x+\cos 3x=0",
        r"\frac{\cos 3x+\cos 7x}{\sin x}=0",
        r"\cos 3x+\sin 7x=0",
    ],
)
def test_unreviewed_multiscale_factorizations_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_product(formula)


def test_angle_product_cannot_silently_undo_an_unrelated_translation():
    from solution_runner.pipelines.equations.exam_trigonometric_methods import (
        compile_reviewed,
    )

    with pytest.raises(UnsupportedCondition):
        compile_reviewed(
            r"\cos 3x-\sin(7x-\frac{\pi}{2})=\cos 5x", C, 5, sp.Rational(1, 6)
        )


def test_clearing_a_sum_in_the_denominator_requires_a_separate_domain_proof():
    c = case("552113")
    _, _, interval, bounds = read(c["context"])
    with pytest.raises(UnsupportedCondition):
        analyze(
            r"\ctg x-\sin x-\sqrt{3}\cos x+\frac{1}{\sin x+\cos x}=0",
            interval,
            bounds,
            parent(c),
        )


def test_closed_upper_endpoint_keeps_the_defined_cosine_zero_root():
    c = case("552113")
    _, formula, _, bounds = read(c["context"])
    a = analyze(
        formula, r"[-\frac{3\pi}{4};\frac{\pi}{2}]", bounds[:3] + (True,), parent(c)
    )
    assert a.selected == (-sp.Rational(1, 2), sp.Rational(1, 3), sp.Rational(1, 2))
