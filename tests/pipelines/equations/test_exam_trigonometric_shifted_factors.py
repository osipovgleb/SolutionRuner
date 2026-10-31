"""Exact shifted factors, pi-scaled real roots, and reviewed source circles."""

import gzip
import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_scalar import compare
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    compare_q,
    decode,
    ordered,
)
from solution_runner.pipelines.equations.exam_trigonometric_linear_phase import branch
from solution_runner.pipelines.equations.exam_trigonometric_pi_scale import finish
from solution_runner.pipelines.equations.exam_trigonometric_proof import (
    polynomial,
    render,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_shifted_factors.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {
    "509626": "-2 -5/4 -1",
    "689036": "2 7/3 3",
    "485996": "-2 -5/6",
    "525068": "-9/2 -11/3 -7/2",
    "525096": "-11/2 -31/6 -9/2",
    "514602": "-4 -17/6",
    "514609": "-3 -5/3",
    "514616": "3/2 5/3 7/3",
    "514630": "5/4 5/2",
    "520658": "-1 -1/6 0",
    "520699": "-1/2 -1/6 1/2",
    "529578": "3/4 5/4 5/3",
    "658798": "-7/3",
    "658884": "14/3",
    "660675": "-19/6 -17/6",
}
RESIDUES = {
    "509626": "0 3/4 1 7/4",
    "689036": "0 1/3 1 4/3",
    "485996": "0 7/6 11/6",
    "525068": "1/3 1/2 3/2",
    "525096": "1/2 5/6 3/2",
    "514602": "0 7/6 11/6",
    "514609": "1/3 2/3 1",
    "514616": "1/3 3/2 5/3",
    "514630": "1/2 3/4 5/4",
    "520658": "0 1/6 1 11/6",
    "520699": "1/2 7/6 3/2 11/6",
    "529578": "1/3 3/4 5/4 5/3",
    "658798": "1/3 5/3",
    "658884": "2/3 4/3",
    "660675": "5/6 7/6",
}
ORIGINAL = {
    "485973": 2 * sp.sin(2 * X) - 4 * c + s - 1,
    "509626": sp.sin(2 * X) + 2 * s * s,
    "689036": 2 * s * s - sp.sqrt(3) * sp.sin(2 * X),
    "485996": sp.sin(2 * X) - 2 * s + c - 1,
    "505308": sp.sin(8 * sp.pi * X)
    + 1
    - sp.cos(4 * sp.pi * X)
    - sp.sqrt(2) * sp.cos(4 * sp.pi * X - sp.pi / 4),
    "525068": sp.sin(2 * X + sp.pi / 6) - c - sp.cos(X + sp.pi / 6) * s,
    "525096": sp.sin(2 * X - sp.pi / 3) - c - sp.cos(X - sp.pi / 3) * s,
    "514602": sp.sin(2 * X) - 2 * s - sp.sin(X + 3 * sp.pi / 2) - 1,
    "514609": sp.sin(2 * X) + 2 * sp.cos(X - sp.pi / 2) - sp.sqrt(3) * c - sp.sqrt(3),
    "514616": sp.sin(2 * X) - s + 2 * sp.sin(X - 3 * sp.pi / 2) - 1,
    "514630": sp.sin(2 * X) + sp.sqrt(2) * s - 2 * sp.sin(sp.pi / 2 - X) - sp.sqrt(2),
    "520658": sp.sin(2 * X) - 2 * sp.sqrt(3) * sp.cos(X + 7 * sp.pi / 6) - 3 * c,
    "520699": sp.sin(2 * X) - 2 * sp.cos(X - 4 * sp.pi / 3) - sp.sqrt(3) * s,
    "529578": 4 * c * c + 2 * (sp.sqrt(2) - 1) * sp.sin(sp.pi / 2 - X) - sp.sqrt(2),
    "658798": 6 * c * c + 5 * sp.sin(sp.pi / 2 + X) - 4,
    "658884": 6 * c * c + 11 * sp.sin(3 * sp.pi / 2 + X) - 7,
    "660675": 2 * s * s + 3 * sp.sqrt(3) * sp.sin(sp.pi / 2 + X) + 4,
}
FACTORED = {
    "485973": (s - 1) * (4 * c + 1),
    "509626": 2 * s * (c + s),
    "689036": 2 * s * (s - sp.sqrt(3) * c),
    "485996": (c - 1) * (2 * s + 1),
    "505308": (2 * sp.cos(4 * sp.pi * X) - 1) * (sp.sin(4 * sp.pi * X) - 1),
    "525068": c * (sp.sin(X + sp.pi / 6) - 1),
    "525096": c * (sp.sin(X - sp.pi / 3) - 1),
    "514602": (c - 1) * (2 * s + 1),
    "514609": (c + 1) * (2 * s - sp.sqrt(3)),
    "514616": (2 * c - 1) * (s + 1),
    "514630": (s - 1) * (2 * c + sp.sqrt(2)),
    "520658": s * (2 * c - sp.sqrt(3)),
    "520699": c * (2 * s + 1),
    "529578": (2 * c - 1) * (2 * c + sp.sqrt(2)),
    "658798": (2 * c - 1) * (3 * c + 4),
    "658884": (2 * c + 1) * (3 * c - 7),
    "660675": -(2 * c + sp.sqrt(3)) * (c - 2 * sp.sqrt(3)),
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
    _, formula, interval, bounds = read(c["context"])
    return analyze(formula, interval, bounds, parent(c))


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_common_trigonometric_rule(g):
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
def test_original_identities_and_complete_selected_root_sets(c):
    task = c["task"]
    a = analysis(c)
    assert sp.trigsimp(sp.expand_trig(ORIGINAL[task] - FACTORED[task])) == 0
    if task == "485973":
        expected = (
            sp.Rational(1, 2),
            1 - sp.acos(sp.Rational(1, 4)) / sp.pi,
            1 + sp.acos(sp.Rational(1, 4)) / sp.pi,
        )
        assert a.selected == expected
        assert select(a.series, (0, 2, True, False))[0] == expected
    elif task == "505308":
        physical = tuple(
            sp.Rational(v)
            for v in [
                "-7/12",
                "-5/12",
                "-3/8",
                "-1/12",
                "1/12",
                "1/8",
                "5/12",
                "7/12",
                "5/8",
            ]
        )
        assert a.scale == 4 * sp.pi
        assert tuple(sp.cancel(q * sp.pi) for q in a.selected) == physical
        assert {(sp.cancel(q * sp.pi), sp.cancel(p * sp.pi)) for q, p in a.series} == {
            (-sp.Rational(1, 12), sp.Rational(1, 2)),
            (sp.Rational(1, 12), sp.Rational(1, 2)),
            (sp.Rational(1, 8), sp.Rational(1, 2)),
        }
        assert all(
            compare(v, 2 - sp.sqrt(7)) >= 0 and compare(v, sp.sqrt(7) - 2) <= 0
            for v in physical
        )
    else:
        assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
        assert select(a.series, (0, 2, True, False))[0] == ordered(
            map(sp.Rational, RESIDUES[task].split())
        )
    physical_roots = [q * sp.pi for q in a.selected]
    for root in physical_roots:
        assert sp.simplify(sp.expand_trig(ORIGINAL[task].subs(X, root))) == 0


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    original = deepcopy(c["context"])
    p = plan(c)
    assert c["context"] == original
    changed = deepcopy(original)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>не использовать</p>"
    assert plan(c, changed).answer == p.answer
    assert plan(c, changed).solution_html == p.solution_html
    for t in p.transformations:
        assert not t["transformation_target_id"].startswith("section:condition")
        key = t["transformation_target_id"]
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
        == original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize(
    "c", [c for c in CASES if c["task"] != "505308"], ids=lambda c: c["task"]
)
def test_circle_bytes_markers_intervals_and_selected_labels(c):
    a = analysis(c)
    asset = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[asset]
    assert (
        hashlib.sha256(
            gzip.decompress((DIRECTORY / (asset + ".svgz")).read_bytes())
        ).hexdigest()
        == entry["sha256"]
    )
    assert ordered(decode(m["angle"]) for m in entry["green_markers"]) == ordered(
        decode(q) for q in entry["residues"]
    )
    assert tuple(decode(q) for q in entry["labels"]) == a.selected
    assert (
        tuple(decode(q) for q in entry["bounds"][:2]) + tuple(entry["bounds"][2:])
        == a.bounds
    )
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            c["context"]
        )
        == ()
    )


@pytest.mark.parametrize("n", [n for n in range(-11, 13) if n % 6])
@pytest.mark.parametrize("value", [-1, 1])
def test_phase_extremes_keep_one_full_two_pi_series(n, value):
    phase = sp.Rational(n, 12)
    expr = 2 * sp.cos(phase * sp.pi) * S + 2 * sp.sin(phase * sp.pi) * C - 2 * value
    b = branch(expr)
    assert b.angle_shift == phase and b.values == (value,)
    expected = (sp.Rational(1, 2) if value == 1 else sp.Rational(3, 2)) - phase
    assert b.residues == (expected % 2,)
    assert (
        sp.simplify(
            expr.subs({S: sp.sin(expected * sp.pi), C: sp.cos(expected * sp.pi)})
        )
        == 0
    )
    html = polynomial(b)
    assert "разделить на косинус" not in html and "синуса суммы" in html


@pytest.mark.parametrize(
    "expression",
    [S + C - 1, S + C - 3, S * C - 1, S + 1, S + C, S + sp.sqrt(2) * C - sp.sqrt(3)],
)
def test_unreviewed_phases_and_nonextreme_linear_levels_fail_closed(expression):
    assert branch(expression) is None


@pytest.mark.parametrize(
    "task,phase", [("525068", sp.Rational(1, 6)), ("525096", -sp.Rational(1, 3))]
)
def test_shifted_factor_and_zero_cosine_are_both_kept(task, phase):
    a = analysis(case(task))
    b = next(b for b in a.branches if b.angle_shift)
    assert b.angle_shift == phase and b.variable == S and b.values == (1,)
    assert (sp.Rational(1, 2), 1) in a.series
    html = render(a, "")[2]
    assert "синуса суммы" in html and "На тригонометрический множитель не делим" in html
    assert "разделить на косинус" not in html


@pytest.mark.parametrize(
    "lc,uc", [(True, True), (True, False), (False, True), (False, False)]
)
def test_rational_real_roots_respect_open_endpoints(lc, uc):
    a = analysis(case("505308"))
    a = replace(
        a,
        bounds=(-sp.Rational(1, 12) / sp.pi, sp.Rational(1, 12) / sp.pi, lc, uc),
        series=((sp.Rational(1, 3), 2), (-sp.Rational(1, 3), 2)),
    )
    result = finish(a)
    assert result.selected == tuple(
        v / sp.pi
        for v, keep in [(-sp.Rational(1, 12), lc), (sp.Rational(1, 12), uc)]
        if keep
    )


@pytest.mark.parametrize(
    "formula",
    [
        r"\sin(\pi x)+\cos x=0",
        r"\sin(\pi^2x)=0",
        r"\frac{\sin(\pi x)}{\cos(\pi x)}=0",
        r"\sin(\sqrt{2}x)=0",
    ],
)
def test_unreviewed_angle_units_fail_closed(formula):
    c = case("505308")
    _, _, interval, bounds = read(c["context"])
    with pytest.raises(UnsupportedCondition):
        analyze(formula, interval, bounds, parent(c))


def test_rational_real_selection_rejects_non_algebraic_and_oversized_bounds():
    a = analysis(case("505308"))
    for lo, hi in [
        (sp.log(2), sp.Integer(2)),
        (-sp.Integer(1001), sp.Integer(1)),
        (-sp.Integer(1000), sp.Integer(1000)),
    ]:
        with pytest.raises(UnsupportedCondition):
            finish(
                replace(
                    a, series=((0, 2),), bounds=(lo / sp.pi, hi / sp.pi, True, True)
                )
            )
    assert compare_q(sp.Rational(-1, 12) / sp.pi, sp.Rational(1, 12) / sp.pi) == -1
