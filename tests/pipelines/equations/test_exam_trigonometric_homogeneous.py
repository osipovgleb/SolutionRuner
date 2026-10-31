"""Independent roots, guarded homogeneous division and exact inverse endpoints."""

import json
import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_input import read_interval
from solution_runner.pipelines.equations.exam_trigonometric import (
    C,
    S,
    T,
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_homogeneous import convert
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    compare_q,
    decode,
    ordered,
    turn,
)
from solution_runner.pipelines.equations.exam_trigonometric_methods import Equation
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_homogeneous.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
AT = lambda q: sp.atan(sp.Rational(q)) / sp.pi
SELECTED = {
    "500000": (-1 + AT("1/3"), -sp.Rational(3, 4)),
    "511330": (AT("4/3"), sp.Rational(3, 4), AT("4/3") + 1),
    "500006": (sp.Rational(7, 4), AT("1/2") + 2),
    "501044": tuple(map(sp.Rational, ("11/6", "7/3", "17/6"))),
    "677081": tuple(map(sp.Rational, ("4/3", "11/6", "7/3"))),
    "518911": (-sp.Rational(17, 4), AT("3") - 4, -sp.Rational(13, 4)),
    "518958": (-sp.Rational(23, 4), -AT("1/2") - 5, -sp.Rational(19, 4)),
    "520189": tuple(map(sp.Rational, ("-37/6", "-35/6", "-31/6"))),
    "520208": tuple(map(sp.Rational, ("-14/3", "-13/3", "-11/3"))),
    "485964": (sp.Rational(7, 4),),
    "511326": tuple(map(sp.Rational, ("-7/12", "-1/12", "5/12"))),
    "485965": tuple(map(sp.Rational, ("3/4", "7/4"))),
    "549973": (sp.Rational(1, 4), 1 - AT("2")),
    "551761": (-AT("2"), -AT("1/2"), AT("3")),
}
LEVELS = {
    "500000": (1, sp.Rational(1, 3)),
    "511330": (-1, sp.Rational(4, 3)),
    "500006": (-1, sp.Rational(1, 2)),
    "501044": (-sp.sqrt(3),),
    "677081": (-sp.sqrt(3),),
    "518911": (-1, 3),
    "518958": (1, -sp.Rational(1, 2)),
    "520189": (-1 / sp.sqrt(3), 1 / sp.sqrt(3)),
    "520208": (-sp.sqrt(3), sp.sqrt(3)),
    "485964": (-1,),
    "511326": (-1 / sp.sqrt(3),),
    "485965": (-1,),
    "549973": (-2, 1),
    "551761": (-2, -sp.Rational(1, 2), 3),
}
ORIGINAL = {
    "500000": 2 * sp.cos(X) ** 2 + 2 * sp.sin(2 * X) - 3,
    "511330": 14 * sp.cos(X) ** 2 + sp.sin(2 * X) - 6,
    "500006": 6 * sp.sin(X) ** 2 + sp.sin(2 * X) - 2,
    "501044": sp.sqrt(3) * sp.sin(2 * X) + 3 * sp.cos(2 * X),
    "677081": sp.sqrt(3) * sp.sin(2 * X) + 3 * sp.cos(2 * X),
    "518911": sp.sin(2 * X) + 2 * sp.cos(X) ** 2 + sp.cos(2 * X),
    "518958": 2 * sp.sin(X) ** 2 - 2 * sp.cos(2 * X) - sp.sin(2 * X),
    "520189": 4 * sp.sin(X - 7 * sp.pi / 2) - 3 / sp.cos(X),
    "520208": 4 * sp.sin(X - 5 * sp.pi / 2) + 1 / sp.cos(X),
    "485964": sp.sin(X)
    + (sp.cos(X / 2) - sp.sin(X / 2)) * (sp.cos(X / 2) + sp.sin(X / 2)),
    "511326": sp.sqrt(3) * sp.cos(2 * X) - 3 + 3 * (sp.sin(X) + sp.cos(X)) ** 2,
    "485965": sp.cos(X) - (sp.cos(X / 2) - sp.sin(X / 2)) ** 2 + 1,
    "549973": sp.cos(2 * X)
    - sp.sin(X) ** 3 * sp.cos(X)
    + 1
    - sp.sin(X) ** 2
    - sp.sin(X) * sp.cos(X) ** 3,
    "551761": 2 * sp.sin(X) ** 3
    - sp.sin(X) ** 2 * sp.cos(X)
    - 13 * sp.sin(X) * sp.cos(X) ** 2
    - 6 * sp.cos(X) ** 3
    - sp.sin(sp.pi / 3 + X)
    + sp.cos(sp.pi / 6 - X),
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


def plan(c, context=None):
    context = context or c["context"]
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler.diagram_specs(context)
    )
    return handler.plan(
        PlanInput(
            context, parent_solution_html=parent(c), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_existing_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 5, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_satisfy_independent_original_equations(c):
    a = analysis(c)
    task = c["task"]
    scale = 2 if task in ("501044", "677081", "511326") else 1
    expected = ordered(
        turn(sp.atan(t) / sp.pi / scale + sp.Rational(k, scale))
        for t in LEVELS[task]
        for k in range(2 * scale)
    )
    assert select(a.series, (0, 2, True, False))[0] == expected
    assert a.selected == SELECTED[task]
    assert a.homogeneous is not None and a.scale == scale
    for q in (*expected, *a.selected):
        assert (
            sp.simplify(sp.expand(sp.expand_trig(ORIGINAL[task].subs(X, q * sp.pi))))
            == 0
        )
        assert sp.cos(scale * q * sp.pi) != 0
    leading = a.homogeneous.polynomial.coeff(S, a.homogeneous.degree)
    assert leading != 0
    assert all(a.homogeneous.polynomial.subs({C: 0, S: sign}) != 0 for sign in (-1, 1))


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
        kind = "assets" if key.startswith("asset:") else "sections"
        items = ctx["normalized_content"][kind]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert all(
        asset in ctx["normalized_content"]["assets"]
        for asset in before["normalized_content"]["assets"]
    )
    assert len(ctx["normalized_content"]["assets"]) - len(
        before["normalized_content"]["assets"]
    ) == (1 if c["task"] == "518958" else 0)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_source_circle_points_and_labels_match_exact_inverse_angles(c):
    a = analysis(c)
    assets = c["context"]["normalized_content"]["assets"]
    if not assets:
        assert (
            a.selection_method == "inequalities" and "<img" not in plan(c).solution_html
        )
        return
    entry = CIRCLES[assets[0]["asset_id"]]
    expected = (
        ordered(turn(q) for q in a.selected)
        if entry.get("point_scope") == "selected"
        else select(a.series, (0, 2, True, False))[0]
    )
    assert ordered(decode(p["angle"]) for p in entry["green_markers"]) == expected
    assert tuple(decode(q) for q in entry["labels"]) == a.selected
    assert tuple(decode(q) for q in entry["bounds"][:2]) == a.bounds[:2]


def test_open_inverse_boundary_is_a_root_but_is_not_selected():
    a = analysis(case("549973"))
    lower = -AT("2")
    assert a.bounds == (lower, sp.S.One, False, False)
    assert sp.trigsimp(ORIGINAL["549973"].subs(X, lower * sp.pi)) == 0
    assert lower not in a.selected
    assert lower in select(a.series, (lower, 1, True, False))[0]


def test_parent_grouping_and_inequality_selection_are_retained():
    html = plan(case("551761")).solution_html
    assert html.index("Сгруппируем") < html.index("D=49")
    assert "t=" in html and r"\ne0" in html
    html = plan(case("511326")).solution_html
    assert "Решим неравенства" in html and "<img" in html
    assert analysis(case("511326")).scale == 2
    for task in ("520189", "520208"):
        a = analysis(case(task))
        assert a.poles and a.reciprocal is None


def test_local_correction_moves_only_two_inaccurate_markers():
    entry = CIRCLES["5111c958-36c8-4f64-ade3-0b6f1ea64093"]
    root = ET.parse(DIRECTORY / entry["corrected_file"]).getroot()
    paths = {e.get("d"): e for e in root.iter() if e.tag.endswith("path")}
    cx, cy, _ = entry["circle"]
    corrected = 0
    for p in entry["green_markers"]:
        transform = paths[p["path_d"]].get("transform")
        if not p.get("inaccurate"):
            assert transform is None
            continue
        dx, dy = map(
            float, transform.removeprefix("translate(").removesuffix(")").split()
        )
        angle = float(decode(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] + dx - cx - p["radius"] * math.cos(angle),
                p["y"] + dy - cy + p["radius"] * math.sin(angle),
            )
            < 1e-6
        )
        corrected += 1
    assert corrected == 2
    assert len([e for e in root.iter() if e.get("transform")]) == 4


@pytest.mark.parametrize("raw", [S * C, S**3 + C**3 + 1, S**4 + C**4 - 1])
def test_unreviewed_or_zero_cosine_branches_are_not_silently_divided(raw):
    equation = Equation(raw, (), sp.S.One)
    assert convert(equation, T) == equation


@pytest.mark.parametrize(
    "text",
    [
        r"Укажите корни этого уравнения, принадлежащие промежутку (-\arctan 2+1;\pi)",
        r"Укажите корни этого уравнения, принадлежащие промежутку (-\arctan x;\pi)",
        r"Укажите корни этого уравнения, принадлежащие промежутку (-\arctan 1001;\pi)",
    ],
)
def test_unreviewed_inverse_endpoints_fail_closed(text):
    with pytest.raises(UnsupportedCondition):
        read_interval(text)


@pytest.mark.parametrize(
    "a,b",
    [
        (AT("3") + AT("2"), 1),
        (-AT("2"), -AT("1/2")),
        (AT("2"), AT("1/2")),
        (AT("3"), 1 - AT("2")),
    ],
)
def test_exact_inverse_comparison_uses_quadrants(a, b):
    assert compare_q(a, sp.sympify(b)) == (1 if float(a) > float(b) else -1)
