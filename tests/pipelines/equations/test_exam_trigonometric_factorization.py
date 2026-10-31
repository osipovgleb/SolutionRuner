"""Every source factor contributes its roots, including variable EX coefficients."""

import gzip
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
from solution_runner.pipelines.equations.exam_trigonometric import (
    C,
    S,
    T,
    analyze,
    select,
    solve_branches,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_factors import (
    source_factors,
)
from solution_runner.pipelines.equations.exam_trigonometric_prepared_circle import (
    RECIPES,
    recipe,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_factorization.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
SELECTED = {
    "500111": "17/6 3 19/6",
    "511420": "-1/2 1/6 1/2",
    "509501": "5/4 5/2",
    "511595": "-5/6 1/6",
    "507638": "1 5/4",
    "511456": "1/4 7/6 5/4",
    "507704": "-3/2 -5/4",
    "485932": "5/2 17/6 7/2",
    "507296": "-5 -19/4 -4",
    "485942": "11/6 5/2",
    "526702": "-3 -11/4 -2",
    "526590": "-5/3 -3/2 -4/3",
    "526598": "-3 -13/6 -2",
    "501507": "9/2 19/4 11/2",
    "502114": "-19/4 -9/2 -17/4",
    "511588": "1 11/6 2",
    "689015": "3 10/3 4",
}
RESIDUES = {
    "500111": "0 5/6 1 7/6",
    "511420": "1/6 1/2 5/6 3/2",
    "509501": "1/2 3/4 5/4",
    "511595": "1/6 5/6 7/6",
    "507638": "1/4 1 5/4",
    "511456": "1/4 7/6 5/4 11/6",
    "507704": "1/2 3/4 7/4",
    "485932": "1/6 1/2 5/6 3/2",
    "507296": "0 3/4 1 5/4",
    "485942": "1/2 7/6 11/6",
    "526702": "0 3/4 1 5/4",
    "526590": "1/3 1/2 2/3 3/2",
    "526598": "0 1/6 1 11/6",
    "501507": "1/4 1/2 3/4 3/2",
    "502114": "1/2 5/4 3/2 7/4",
    "511588": "0 1/6 1 11/6",
    "689015": "0 2/3 1 4/3",
}
ORIGINAL = {
    "500111": sp.sin(2 * X) + sp.sqrt(3) * sp.sin(X),
    "511420": sp.sin(sp.pi / 2 + X) - sp.sin(2 * X),
    "509501": sp.sin(2 * X) + sp.sqrt(2) * sp.sin(X) - 2 * sp.cos(X) - sp.sqrt(2),
    "511595": 2 * sp.sin(2 * X)
    + 2 * sp.sqrt(3) * sp.sin(X)
    - 2 * sp.cos(X)
    - sp.sqrt(3),
    "507638": sp.cos(X) ** 2 - sp.sin(2 * X) / 2 + sp.cos(X) - sp.sin(X),
    "511456": 2 * sp.sin(X) ** 2 - sp.sin(2 * X) + sp.sin(X) - sp.cos(X),
    "507704": sp.sin(2 * X) / 2 + sp.sin(X) ** 2 - sp.sin(X) - sp.cos(X),
    "485932": sp.cos(3 * sp.pi / 2 + 2 * X) - sp.cos(X),
    "507296": sp.cos(sp.pi / 2 + 2 * X) - sp.sqrt(2) * sp.sin(X),
    "485942": sp.sin(3 * sp.pi / 2 - 2 * X) - sp.sin(X),
    "526702": sp.cos(sp.pi / 2 + 2 * X) - sp.sqrt(2) * sp.sin(X),
    "526590": 2 * sp.sin(3 * sp.pi / 2 + X) * sp.cos(sp.pi / 2 + X)
    - sp.sqrt(3) * sp.cos(2 * sp.pi - X),
    "526598": 2 * sp.sin(sp.pi / 2 - X) * sp.cos(3 * sp.pi / 2 + X)
    - sp.sqrt(3) * sp.sin(sp.pi - X),
    "501507": -sp.sqrt(2) * sp.sin(-5 * sp.pi / 2 + X) * sp.sin(X) - sp.cos(X),
    "502114": sp.sqrt(2) * sp.sin(3 * sp.pi / 2 - X) * sp.sin(X) - sp.cos(X),
    "511588": 2 * sp.cos(3 * sp.pi / 2 + X) * sp.cos(X) - sp.sqrt(3) * sp.sin(X),
    "689015": 2 * sp.cos(X - 11 * sp.pi / 2) * sp.cos(X) - sp.sin(X),
}
FACTORED = {
    "500111": sp.sin(X) * (2 * sp.cos(X) + sp.sqrt(3)),
    "511420": sp.cos(X) * (1 - 2 * sp.sin(X)),
    "509501": (sp.sin(X) - 1) * (2 * sp.cos(X) + sp.sqrt(2)),
    "511595": (2 * sp.sin(X) - 1) * (2 * sp.cos(X) + sp.sqrt(3)),
    "507638": (sp.cos(X) + 1) * (sp.cos(X) - sp.sin(X)),
    "511456": (sp.sin(X) - sp.cos(X)) * (2 * sp.sin(X) + 1),
    "507704": (sp.sin(X) - 1) * (sp.cos(X) + sp.sin(X)),
    "485932": sp.cos(X) * (2 * sp.sin(X) - 1),
    "507296": -sp.sin(X) * (2 * sp.cos(X) + sp.sqrt(2)),
    "485942": (sp.sin(X) - 1) * (2 * sp.sin(X) + 1),
    "526702": -sp.sin(X) * (2 * sp.cos(X) + sp.sqrt(2)),
    "526590": sp.cos(X) * (2 * sp.sin(X) - sp.sqrt(3)),
    "526598": sp.sin(X) * (2 * sp.cos(X) - sp.sqrt(3)),
    "501507": sp.cos(X) * (sp.sqrt(2) * sp.sin(X) - 1),
    "502114": -sp.cos(X) * (sp.sqrt(2) * sp.sin(X) + 1),
    "511588": sp.sin(X) * (2 * sp.cos(X) - sp.sqrt(3)),
    "689015": -sp.sin(X) * (2 * sp.cos(X) + 1),
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


def handler(c):
    return get_handler(get_group_profile(c["group"]).content_rule_key)


def plan(c, context=None):
    ctx = context or c["context"]
    h = handler(c)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(ctx)
    )
    return h.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
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
    ) == (g["uuid"], g["theme_uuid"], 6, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_equations_factors_full_and_selected_roots_are_independent(c):
    task = c["task"]
    a = analysis(c)
    assert sp.trigsimp(sp.expand(sp.expand_trig(ORIGINAL[task] - FACTORED[task]))) == 0
    assert a.residues == tuple(map(sp.Rational, RESIDUES[task].split()))
    assert select(a.series, (0, 2, True, False))[0] == a.residues
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    actual_grid = tuple(
        sp.Rational(i, 12)
        for i in range(24)
        if sp.simplify(ORIGINAL[task].subs(X, sp.pi * i / 12)) == 0
    )
    assert actual_grid == a.residues
    for q in (*a.residues, *a.selected):
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0


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
        a in ctx["normalized_content"]["assets"]
        for a in before["normalized_content"]["assets"]
    )
    assert len(ctx["normalized_content"]["assets"]) - len(
        before["normalized_content"]["assets"]
    ) == (1 if c["task"] in ("507296", "526702") else 0)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_circles_describe_computed_roots_and_preserve_compatible_sources(c):
    a = analysis(c)
    assets = c["context"]["normalized_content"]["assets"]
    specs = handler(c).diagram_specs(c["context"])
    assert bool(specs) == (c["task"] in ("507296", "526702"))
    if not assets:
        e = recipe(c["context"])
        assert e is not None and tuple(map(sp.Rational, e["labels"])) == a.selected
        assert tuple(map(sp.Rational, e["residues"])) == a.residues
        return
    e = CIRCLES[assets[0]["asset_id"]]
    expected = (
        sorted({q % 2 for q in a.selected})
        if e.get("point_scope") == "selected"
        else list(a.residues)
    )
    assert sorted({sp.Rational(p["angle"]) for p in e["green_markers"]}) == expected
    assert tuple(map(sp.Rational, e["labels"])) == a.selected
    if not specs:
        assert assets[0]["asset_id"] in plan(c).solution_html


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_global_division_does_not_remove_zero_function_branches(c):
    a = analysis(c)
    html = plan(c).solution_html
    assert not a.division
    if len(a.branches) > 1:
        assert "На тригонометрический множитель не делим" in html
    if any(q in a.residues for q in (sp.Rational(1, 2), sp.Rational(3, 2))):
        assert any(sp.cos(q * sp.pi) == 0 for q in a.residues)
    if c["group"] == "507638":
        assert any(b.variable == T and b.original is not None for b in a.branches)
        assert "только в этой ветви можно разделить" in html


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("constant", (sp.sqrt(2), sp.sqrt(3)))
def test_variable_expression_coefficient_is_not_discarded(sign, constant):
    raw = S * (2 * C + sign * constant)
    factors = source_factors(raw)
    assert sp.expand(sp.prod(factors) - raw) == 0 and len(factors) == 2
    _, branches = solve_branches(raw, S)
    assert {b.variable for b in branches} == {S, C}
    assert next(b for b in branches if b.variable == S).values == (0,)
    assert next(b for b in branches if b.variable == C).values == (
        -sign * constant / 2,
    )


def test_boundary_roots_and_duplicate_factor_roots_are_not_lost():
    assert analysis(case("509501")).residues == (
        sp.Rational(1, 2),
        sp.Rational(3, 4),
        sp.Rational(5, 4),
    )
    assert analysis(case("511595")).residues == (
        sp.Rational(1, 6),
        sp.Rational(5, 6),
        sp.Rational(7, 6),
    )
    a = analysis(case("501507"))
    assert a.bounds[0] in a.selected and sp.Rational(11, 2) in a.selected
    a = analysis(case("507296"))
    assert a.bounds[0] in a.selected and a.bounds[1] in a.selected


def test_prepared_circle_reuses_audited_template_and_recolors_only_boundary_markers():
    c = case("507296")
    e = recipe(c["context"])
    assert e == RECIPES[0]
    original = ET.fromstring(
        gzip.decompress(
            (DIRECTORY / (e["template_source_asset_id"] + ".svgz")).read_bytes()
        )
    )
    prepared = ET.parse(DIRECTORY / e["file"]).getroot()
    old = list(original.iter())
    new = list(prepared.iter())
    assert len(old) == len(new)
    changed = 0
    for a, b in zip(old, new):
        assert a.tag == b.tag and (a.text or "").strip() == (b.text or "").strip()
        if a.attrib != b.attrib:
            assert a.get("d") == b.get("d") and a.get("d")
            assert {
                k: v for k, v in a.attrib.items() if k not in ("fill", "stroke")
            } == {k: v for k, v in b.attrib.items() if k not in ("fill", "stroke")}
            assert b.get("fill") == "#007A37" or b.get("stroke") == "#007A37"
            changed += 1
    assert changed == 4
    assert "preview-" in plan(c).solution_html


def test_corrected_quarter_points_and_projection_share_the_exact_cosine():
    e = CIRCLES["1f8f79ef-2cfa-434f-978d-10cd97fc9d7a"]
    root = ET.parse(DIRECTORY / e["corrected_file"]).getroot()
    cx, cy, radius = e["circle"]
    paths = {n.get("d"): n for n in root.iter() if n.get("d")}
    changed = 0
    for p in e["green_markers"]:
        if not p.get("inaccurate"):
            continue
        dx, dy = map(
            float,
            paths[p["path_d"]]
            .get("transform")
            .removeprefix("translate(")
            .removesuffix(")")
            .split(),
        )
        q = float(sp.Rational(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] + dx - cx - radius * math.cos(q),
                p["y"] + dy - cy + radius * math.sin(q),
            )
            < 1e-6
        )
        changed += 1
    assert changed == 2
    ray = next(
        n for n in root.iter() if n.tag.endswith("line") and n.get("stroke-dasharray")
    )
    assert float(ray.get("x1")) == float(ray.get("x2"))
    assert abs((float(ray.get("x1")) - cx) / radius + math.sqrt(2) / 2) < 1e-8


@pytest.mark.parametrize(
    "old,new", [(r"[-5\pi;-4\pi]", r"[-4\pi;-3\pi]"), (r"\sqrt{2}", r"\sqrt{3}")]
)
def test_unreviewed_prepared_circle_equations_and_intervals_fail_closed(old, new):
    c = case("507296")
    ctx = deepcopy(c["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert old in section["html"]
    section["html"] = section["html"].replace(old, new)
    assert handler(c).diagram_specs(ctx) == ()
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


def test_prepared_circle_rejects_unknown_assets_and_unmatched_svg_hash():
    c = case("507296")
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"] = [
        {
            "asset_key": "exam_trig_circle",
            "asset_id": "wrong",
            "url": "/wrong",
            "kind": "ordinary_image",
        }
    ]
    with pytest.raises(UnsupportedCondition):
        handler(c).diagram_specs(ctx)
    spec = handler(c).diagram_specs(c["context"])[0]
    with pytest.raises(UnsupportedCondition):
        handler(c).plan(
            PlanInput(
                c["context"],
                parent_solution_html=parent(c),
                generated_solution_assets=(
                    {
                        **spec,
                        "sha256": "0" * 64,
                        "source_asset_id": "preview-wrong",
                        "url": "/assets/preview-wrong",
                    },
                ),
            )
        )
