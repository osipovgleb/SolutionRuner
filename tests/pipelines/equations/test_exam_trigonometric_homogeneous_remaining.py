"""Close the homogeneous theme while preserving factors, cotangents and powers."""

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
    T,
    U,
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    decode,
    ordered,
    turn,
)
from solution_runner.pipelines.equations.exam_trigonometric_methods import (
    compile_reviewed,
)
from solution_runner.pipelines.equations.exam_trigonometric_power_identity import (
    fold_sixth,
)
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_homogeneous_remaining.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
A = sp.atan(sp.Rational(1, 2)) / sp.pi
SELECTED = {
    "560711": (1 - A, sp.Rational(5, 3)),
    "628639": tuple(map(sp.Rational, ("5/6", "5/4", "11/6", "9/4", "17/6"))),
    "677067": (sp.Rational(21, 4), 5 + sp.atan(5) / sp.pi),
    "697029": (-sp.Rational(23, 4),),
    "697049": (-sp.Rational(19, 4),),
    "697990": tuple(map(sp.Rational, ("5/6", "13/12", "4/3"))),
    "701422": (sp.Rational(1, 6),),
    "701423": tuple(map(sp.Rational, ("13/4", "17/4"))),
}
RESIDUES = {
    "560711": (sp.Rational(2, 3), 1 - A, sp.Rational(5, 3), 2 - A),
    "628639": tuple(map(sp.Rational, ("1/4", "5/6", "5/4", "11/6"))),
    "677067": (
        sp.Rational(1, 4),
        sp.atan(5) / sp.pi,
        sp.Rational(5, 4),
        1 + sp.atan(5) / sp.pi,
    ),
    "697029": (sp.Rational(1, 4), sp.Rational(5, 4)),
    "697049": (sp.Rational(1, 4), sp.Rational(5, 4)),
    "697990": tuple(sp.Rational(1, 12) + sp.Rational(k, 4) for k in range(8)),
    "701422": (sp.Rational(1, 6), sp.Rational(7, 6)),
    "701423": (sp.Rational(1, 4), sp.Rational(5, 4)),
}
ORIGINAL = {
    "560711": 2 * sp.sin(X) ** 2
    + sp.sin(X) * sp.cos(X)
    + sp.sqrt(3) * (sp.sin(2 * X) + sp.cos(X) ** 2),
    "628639": (sp.cot(sp.pi / 2 - X) - 1)
    * (sp.cos(X) ** 2 + sp.sqrt(3) * sp.sin(2 * X) / 2),
    "677067": 2 * sp.cos(X) ** 2 + 3 * sp.sin(2 * X) - 4 - 3 * sp.cos(2 * X),
    "697029": 2 * sp.cos(X - sp.pi / 4)
    - sp.sqrt(2) * sp.sin(X)
    - 2 * sp.sin(X + sp.pi / 4)
    + sp.sqrt(2) * sp.cos(X),
    "697049": 2 * sp.cos(X + sp.pi / 4)
    + sp.sqrt(2) * sp.sin(X)
    - 2 * sp.sin(X - sp.pi / 4)
    - sp.sqrt(2) * sp.cos(X),
    "697990": 8 * (sp.sin(X) ** 6 + sp.cos(X) ** 6) - sp.sqrt(3) * sp.sin(4 * X) - 5,
    "701422": sp.sin(X + sp.pi / 6) - sp.sqrt(3) * sp.sin(sp.pi - X),
    "701423": 2 * sp.sin(X + sp.pi / 4) - 2 * sp.sqrt(2) * sp.sin(sp.pi - X),
}
FACTORED = {
    "560711": (sp.sin(X) + sp.sqrt(3) * sp.cos(X)) * (2 * sp.sin(X) + sp.cos(X)),
    "628639": (sp.sin(X) - sp.cos(X)) * (sp.cos(X) + sp.sqrt(3) * sp.sin(X)),
    "677067": -(sp.sin(X) - sp.cos(X)) * (sp.sin(X) - 5 * sp.cos(X)),
    "697029": sp.sqrt(2) * (sp.cos(X) - sp.sin(X)),
    "697049": sp.sqrt(2) * (sp.cos(X) - sp.sin(X)),
    "697990": 3 * sp.cos(4 * X) - sp.sqrt(3) * sp.sin(4 * X),
    "701422": (sp.cos(X) - sp.sqrt(3) * sp.sin(X)) / 2,
    "701423": sp.sqrt(2) * (sp.cos(X) - sp.sin(X)),
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
def test_independent_equations_factors_and_all_periodic_roots(c):
    task = c["task"]
    a = analysis(c)
    assert sp.trigsimp(sp.expand(sp.expand_trig(ORIGINAL[task] - FACTORED[task]))) == 0
    assert select(a.series, (0, 2, True, False))[0] == RESIDUES[task]
    assert a.selected == SELECTED[task]
    for q in (*RESIDUES[task], *a.selected):
        assert (
            sp.simplify(sp.expand(sp.expand_trig(ORIGINAL[task].subs(X, q * sp.pi))))
            == 0
        )
        if a.poles:
            assert sp.cos(q * sp.pi) != 0


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
    ) == (1 if c["task"] == "560711" else 0)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_exact_circle_scopes_and_multiple_turns(c):
    a = analysis(c)
    assets = c["context"]["normalized_content"]["assets"]
    if not assets:
        assert (
            a.selection_method == "inequalities" and "<img" not in plan(c).solution_html
        )
        return
    e = CIRCLES[assets[0]["asset_id"]]
    visible = ordered(decode(p["angle"]) for p in e["green_markers"])
    expected = (
        ordered(turn(q) for q in a.selected)
        if e.get("point_scope") == "selected"
        else RESIDUES[c["task"]]
    )
    assert visible == expected == tuple(decode(q) for q in e["residues"])
    assert tuple(decode(q) for q in e["labels"]) == a.selected
    if c["task"] == "628639":
        assert len(e["green_markers"]) == len(a.selected) == 5 and len(visible) == 4
        assert (
            len(
                {
                    round(p["radius"], 2)
                    for p in e["green_markers"]
                    if p["angle"] == "5/6"
                }
            )
            == 2
        )


def test_grouping_precedes_tangent_branches_and_never_replaces_original_domain():
    for task in ("560711", "628639"):
        a = analysis(case(task))
        html = plan(case(task)).solution_html
        assert len(a.branches) == 2 and all(
            b.variable == T and b.original is not None for b in a.branches
        )
        assert a.homogeneous is None and "D=" not in html
        assert "Произведение равно нулю" in html
        assert r"\cos(x)\ne0" in html
    assert "Сгруппируем слагаемые" in plan(case("560711")).solution_html
    html = plan(case("560711")).solution_html
    assert html.index(r"(\tg x)=- \sqrt{3}") < html.index(r"(\tg x)=- \frac{1}{2}")
    a = analysis(case("628639"))
    assert a.poles == (C,)
    assert not any(q in a.residues for q in (sp.Rational(1, 2), sp.Rational(3, 2)))
    html = plan(case("628639")).solution_html
    assert (
        html.index("область определения")
        < html.index("Сокращаем")
        < html.index("Произведение равно нулю")
    )


@pytest.mark.parametrize("task", ("701422", "701423"))
def test_parent_cotangent_and_nonzero_sine_are_preserved(task):
    a = analysis(case(task))
    html = plan(case(task)).solution_html
    assert (
        a.preferred == U
        and a.homogeneous.variable == U
        and a.raw.has(U)
        and not a.raw.has(T)
    )
    assert r"(\sin x)\ne0" in html and r"\ctg x" in html
    assert r"\tg x" not in html


def test_sixth_power_identity_retains_derivation_and_scaled_integer_selection():
    c = case("697990")
    a = analysis(c)
    html = plan(c).solution_html
    assert a.power_angle == 1 and a.scale == 4
    assert a.series == ((sp.Rational(1, 12), sp.Rational(1, 4)),)
    assert html.index("формулу суммы кубов") < html.index("разделим уравнение")
    assert r"(\sin x)^{6}" in html and r"(\cos 4 x)" in html and r"(\tg 4 x)" in html
    assert "Решим неравенства" in html


def test_plain_unicode_intervals_are_read_without_changing_source_markup():
    _, bounds = read_interval(
        "Найдите все корни этого уравнения, принадлежащие отрезку [–6π;–5π]"
    )
    assert bounds == (-6 * sp.pi, -5 * sp.pi, True, True)
    assert (
        "[–6π;\u202f–5π]" in plan(case("697029")).condition_html
        or "–6π" in plan(case("697029")).condition_html
    )


def test_corrected_ray_and_boundary_markers_use_exact_angles():
    e = CIRCLES["6ddcee09-02a8-4e81-ac23-40b22b50cb78"]
    root = ET.parse(DIRECTORY / e["corrected_file"]).getroot()
    cx, cy, radius = e["circle"]
    paths = {p.get("d"): p for p in root.iter() if p.tag.endswith("path")}
    point = next(p for p in e["green_markers"] if p.get("inaccurate"))
    dx, dy = map(
        float,
        paths[point["path_d"]]
        .get("transform")
        .removeprefix("translate(")
        .removesuffix(")")
        .split(),
    )
    x, y = point["x"] + dx, point["y"] + dy
    assert abs((cy - y) / (x - cx) + 0.5) < 1e-8
    ray = next(
        n for n in root.iter() if n.tag.endswith("line") and n.get("x2") == "197.536"
    )
    for i in (1, 2):
        assert (
            abs(
                (float(ray.get("y" + str(i))) - cy)
                / (float(ray.get("x" + str(i))) - cx)
                - 0.5
            )
            < 1e-8
        )
    arc = next(
        n
        for n in root.iter()
        if n.get("stroke") == "#00487E" and n.get("stroke-width") == "1.5"
    )
    assert " A " in arc.get("d")
    start = tuple(
        map(float, arc.get("d").split(" A ")[0].removeprefix("M ").split(","))
    )
    assert (
        math.hypot(
            start[0] - cx - radius * math.cos(5 * math.pi / 6),
            start[1] - cy + radius * math.sin(5 * math.pi / 6),
        )
        < 1e-6
    )


@pytest.mark.parametrize(
    "expression",
    [
        sp.sin(X) ** 6,
        sp.sin(X) ** 6 + 2 * sp.cos(X) ** 6,
        sp.sin(X) ** 6 + sp.cos(2 * X) ** 6,
    ],
)
def test_unpaired_or_unequal_sixth_powers_fail_closed(expression):
    with pytest.raises(UnsupportedCondition):
        fold_sixth(expression)


def test_numeric_power_limit_and_unreviewed_ratio_shifts_still_fail_closed():
    with pytest.raises(UnsupportedCondition):
        TrigonometricParser(r"\sin^{6}30").parse()
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(r"\sin^{5}x+\cos^{5}x=0", T, sp.S.One)
    with pytest.raises(UnsupportedCondition):
        compile_reviewed(r"(\ctg(\frac{\pi}{4}-x)-1)\cos x=0", T, sp.S.One)
