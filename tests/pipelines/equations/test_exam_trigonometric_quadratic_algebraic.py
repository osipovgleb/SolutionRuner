"""Keep isolated rational radians separate from periodic trigonometric roots."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import mpmath as mp
import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_affine import compile_affine
from solution_runner.pipelines.equations.exam_trigonometric_affine_proof import (
    isolated_selection,
)
from solution_runner.pipelines.equations.exam_trigonometric_affine_selection import (
    combine,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    compare_q,
    decode,
    ordered,
    turn,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.equations.exam_trigonometric_selection import finish
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_quadratic_algebraic.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return section(case(c["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(c, formula=None, prototype=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, i, b, prototype or parent(c))


def plan(c, ctx=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(ctx or c["context"], parent_solution_html=parent(c))
    )


def forms(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_value(task, x):
    return {
        "519635": lambda: (2 * x * x - 5 * x - 12) * (2 * mp.cos(x) + 1),
        "556585": lambda: (2 - 3 * x - 2 * x * x) * (2 * mp.sin(x) - mp.sqrt(3)),
        "556593": lambda: (3 * x * x - 19 * x + 20) * (2 * mp.cos(x) + mp.sqrt(3)),
    }[task]()


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_finite_and_periodic_roots_follow_independent_original_equations(c):
    a = analysis(c)
    e = DATA["expected"][c["task"]]
    periodic = tuple(map(R, e["periodic_full"]))
    finite = tuple(map(R, e["roots"]))
    assert a.affine.quadratic and a.affine.roots == finite and a.affine.algebraic_first
    assert select(a.series, (0, 2, True, False))[0] == periodic
    assert a.selected == tuple(map(decode, e["selected"]))
    with mp.workdps(65):
        for n in range(-192, 193):
            q = R(n, 48)
            x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
            assert (abs(original_value(c["task"], x)) < mp.mpf("1e-43")) == (
                q % 2 in periodic
            )
        for root in finite:
            for delta in [0, R(1, 100), -R(1, 100)]:
                value = root + delta
                x = mp.mpf(int(value.p)) / int(value.q)
                assert (abs(original_value(c["task"], x)) < mp.mpf("1e-43")) == (
                    value in finite
                )
            for k in [-1, 1]:
                x = mp.mpf(int(root.p)) / int(root.q) + 2 * k * mp.pi
                assert abs(original_value(c["task"], x)) > mp.mpf("1e-20")
    expected_inside = {
        "519635": (R(2, 3), 4 / sp.pi, R(4, 3)),
        "556585": (1 / (2 * sp.pi), R(1, 3), R(2, 3)),
        "556593": (4 / (3 * sp.pi), R(5, 6), R(7, 6), 5 / sp.pi),
    }
    assert combine(periodic, finite, (0, 2, True, False)) == expected_inside[c["task"]]


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_original_conditions_and_circles(
    c,
):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ["answer", "solution"]:
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        assert not t["transformation_target_id"].startswith("asset:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            before
        )
        == ()
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_circle_bytes_and_mixed_radian_marker_geometry(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    paths = {n.get("d") for n in ET.fromstring(raw).iter() if n.tag.endswith("path")}
    for p in e["green_markers"]:
        assert p["path_d"] in paths
        f = p["native_frame"]
        assert f["path_d"] in paths
        theta = float(decode(p["angle"]) * sp.pi)
        assert (
            math.hypot(
                p["x"] - f["cx"] - f["rx"] * math.cos(theta),
                p["y"] - f["cy"] + f["ry"] * math.sin(theta),
            )
            < 5
        )
    a = analysis(c)
    validate(e, a)
    assert tuple(map(R, e["isolated_roots"])) == a.affine.roots
    if c["task"] == "519635":
        assert e["label_scope"] == "periodic" and e["labels"] == ["2/3"]
        assert tuple(map(decode, e["isolated_selected"])) == (-3 / (2 * sp.pi),)
    else:
        assert (
            e["point_scope"] == "selected"
            and tuple(map(decode, e["labels"])) == a.selected
        )
        assert tuple(map(decode, e["residues"])) == ordered(turn(q) for q in a.selected)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_algebraic_branch_order_and_separate_selection_are_retained(c):
    html = plan(c).solution_html
    maths = forms(html)
    finite = tuple(map(R, DATA["expected"][c["task"]]["roots"]))
    positions = [maths.index("x=" + sp.latex(root)) for root in finite]
    assert positions == sorted(positions)
    assert html.index("Решим алгебраическое уравнение") < html.index(
        "Решим тригонометрическое уравнение"
    )
    assert "не образуют периодическую серию" in html
    assert html.index("Отдельные алгебраические корни сравним") < html.index(
        "отберём периодические корни"
    )
    if c["task"] == "519635":
        assert "4>\\pi" in maths
    if c["task"] == "556593":
        assert r"\frac{4}{3}<\frac{3 \pi}{2}" in maths


def test_parent_can_choose_trigonometric_branch_first_without_changing_roots():
    c = case("556585")
    prototype = (
        '<p><span data-inline-latex="\\sin x=\\frac{\\sqrt{3}}{2}"></span></p>'
        + parent(c)
    )
    a = analysis(c, prototype=prototype)
    assert not a.affine.algebraic_first and a.selected == analysis(c).selected
    _, _, html = render(a, "")
    assert html.index("Решим тригонометрическое уравнение") < html.index(
        "Решим алгебраическое уравнение"
    )


@pytest.mark.parametrize("closed", [True, False])
def test_repeated_algebraic_zero_is_deduplicated_and_respects_exact_open_endpoint(
    closed,
):
    a = analysis(case("556585"), r"x^2\sin x=0")
    assert a.affine.roots == (0,)
    a = finish(replace(a, bounds=(sp.S.Zero, sp.S.Zero, closed, closed)))
    assert a.selected == ((0,) if closed else ())
    html = isolated_selection(a)
    assert ("граница промежутка не включена" in html) == (not closed)


@pytest.mark.parametrize(
    "q,b,expected",
    [
        (2 - 2 / sp.pi, R(4, 3), 1),
        (1 / (2 * sp.pi), R(1, 6), -1),
        (5 / sp.pi, R(3, 2), 1),
        (355 / (113 * sp.pi), 1, 1),
        (333 / (106 * sp.pi), 1, -1),
    ],
)
def test_mixed_radian_phase_order_uses_certified_pi_enclosures(q, b, expected):
    assert (
        compare_q(q, sp.sympify(b)) == expected
        and compare_q(sp.sympify(b), q) == -expected
    )
    assert compare_q(q, q) == 0


def test_closed_rational_turn_and_radian_coordinate_decoding():
    assert decode({"rational": "2", "scalar": "-2"}) == 2 - 2 / sp.pi
    assert turn(-2 / sp.pi) == decode({"rational": "2", "scalar": "-2"})
    assert decode({"scalar": "5"}) == 5 / sp.pi
    assert ordered([2 - 2 / sp.pi, R(1, 3), 1 / (2 * sp.pi)]) == (
        1 / (2 * sp.pi),
        R(1, 3),
        2 - 2 / sp.pi,
    )


@pytest.mark.parametrize(
    "value",
    [
        {"rational": "1001", "scalar": "0"},
        {"rational": "0", "scalar": "-1001"},
        {"rational": "pi", "scalar": "1"},
        {"rational": "2", "scalar": "1/0"},
        {"rational": "2", "scalar": "-2", "extra": "0"},
    ],
)
def test_unknown_or_unbounded_mixed_coordinates_fail_closed(value):
    with pytest.raises(UnsupportedCondition):
        decode(value)


@pytest.mark.parametrize(
    "formula",
    [
        r"(x^3-1)(2\cos x+1)=0",
        r"(x^2-2)(2\sin x-\sqrt{3})=0",
        r"(x^2+1)(2\cos x+1)=0",
        r"x^2\cos x-x=0",
        r"(x-1)\sin x\cos x=0",
        r"(x^2-1)(2\sin2x-1)=0",
        r"\frac{(x-1)(x+1)\sin x}{x-1}=0",
        r"(x-1001)(x+1)(2\sin x-1)=0",
        r"(x-x)\sin x=0",
    ],
)
def test_unreviewed_algebraic_trig_coupling_and_original_poles_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_affine(formula)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_source_changed_interval_and_changed_isolated_roots_are_rejected(c):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    s = section(ctx["normalized_content"], "condition")
    soup = BeautifulSoup(s["html"], "html.parser")
    soup.select("[data-inline-latex]")[1]["data-inline-latex"] = r"[0;10\pi]"
    s["html"] = str(soup)
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = deepcopy(CIRCLES[aid])
    e["isolated_roots"][0] = "9"
    with pytest.raises(UnsupportedCondition):
        validate(e, analysis(c))


@pytest.mark.parametrize("task,e", DATA["groups"].items())
def test_group_registration_keeps_catalog_order_and_existing_rule(task, e):
    p = get_group_profile(task)
    assert p.source_group_id == e["uuid"] and p.snapshot_theme_id == e["theme_uuid"]
    assert p.group_order_index == e["order_index"] and p.category_key == "14"
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
