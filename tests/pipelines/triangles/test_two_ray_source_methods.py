"""Euclidean ray geometry independently checks all six source families."""

import math
from copy import deepcopy
from fractions import Fraction

import pytest
from bs4 import BeautifulSoup
from ray_source_cases import (
    CASES,
    DATA,
    GROUPS,
    generated,
    parent_html,
    plan,
    section,
    solution_html,
)
from test_construction_parent_sources import angle, verify

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.triangles.right.construction_angles import read_context

PARAMETERS = {
    "27770": (29, 61, "HD", 16),
    "47625": (4, 86, "HD", 41),
    "47627": (30, 60, "HD", 15),
    "47629": (41, 49, "HD", 4),
    "27771": (24, 66, "HD", 24),
    "47669": (19, 71, "HD", 19),
    "47671": (28, 62, "HD", 28),
    "47673": (45, 45, "HD", 45),
    "27772": (24, 66, "HM", 42),
    "500908": (5, 85, "HD", 40),
    "502085": (28, 62, "HM", 34),
    "504535": (40, 50, "HM", 10),
    "27773": (25, 65, "HM", 65),
    "560723": (26, 64, "HM", 64),
    "560772": (32, 58, "HM", 58),
    "47759": (30, 60, "HM", 60),
    "27774": (24, 66, "DM", 21),
    "639663": (24, 66, "DM", 21),
    "639740": (17, 73, "DM", 28),
    "641148": (69, 21, "DM", 24),
    "27775": (31, 59, "DM", 31),
    "505462": (25, 65, "DM", 25),
    "47847": (11, 79, "DM", 11),
    "47849": (22, 68, "DM", 22),
}


def coordinates(alpha):
    # Perpendicular legs, independent of the renderer's hypotenuse coordinate model.
    a, b, c = (
        (math.cos(math.radians(alpha)), 0),
        (0, math.sin(math.radians(alpha))),
        (0, 0),
    )
    ab = (b[0] - a[0], b[1] - a[1])
    t = -(a[0] * ab[0] + a[1] * ab[1]) / (ab[0] ** 2 + ab[1] ** 2)
    h = (a[0] + t * ab[0], a[1] + t * ab[1])
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    d = (a[0] * b[1] / (a[0] + b[1]),) * 2
    return {"A": a, "B": b, "C": c, "H": h, "M": m, "D": d}


def geometry_values(alpha):
    p = coordinates(alpha)
    angles = ["ACD", "BCD", "DCH", "ACH", "BCH", "HCB", "ACM", "MCH", "MCD", "MCB"]
    values = {r"\angle " + n: angle(p[n[0]], p[n[1]], p[n[2]]) for n in angles}
    if abs(alpha - 45) > 1e-10:
        values[r"\angle CMB"] = angle(p["C"], p["M"], p["B"])
    values.update(
        {
            r"\angle A": angle(p["C"], p["A"], p["B"]),
            r"\angle B": angle(p["A"], p["B"], p["C"]),
            r"\angle C": angle(p["A"], p["C"], p["B"]),
        }
    )
    for segment in ["AM", "MC", "MB", "CM"]:
        values[segment] = math.dist(p[segment[0]], p[segment[1]])
    return values


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_all_bindings_require_reviewed_parent_generated_metadata_and_frozen_manifest(g):
    p = get_group_profile(g["key"])
    h = get_handler(g["rule"])
    assert (
        p.source_group_id == g["group_uuid"] and p.existing_solution_policy == "rewrite"
    )
    assert h.requires_frozen_manifest and h.diagram_builder
    assert ("parent_solution_html", "parent_solution_html") in h.inputs
    assert g["group_size"] >= 3


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_answer_and_formula_matches_independent_construction(case):
    alpha, beta, pair, expected = PARAMETERS[case["task"]]
    model = read_context(case["context"]).require_rule(GROUPS[case["group"]]["rule"])
    assert (model.a, model.b, model.pair, model.answer) == (alpha, beta, pair, expected)
    result = plan(case)
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert (
        Fraction(result.answer.replace(",", "."))
        == Fraction(saved.replace(",", "."))
        == expected
    )
    verify(solution_html(result), geometry_values(alpha))
    methods = BeautifulSoup(solution_html(result), "html.parser").select("section")
    assert [m["data-solution-title"] for m in methods] == ["Решение"]


def replay(ctx, transformations):
    content = ctx["normalized_content"]
    for t in transformations:
        target = t["transformation_target_id"]
        if target.startswith("asset:"):
            key = target.removeprefix("asset:")
            existing = next(
                (a for a in content["assets"] if a["asset_key"] == key), None
            )
            if t["operation"] == "remove":
                assert existing is not None
                content["assets"].remove(existing)
            elif existing is not None:
                existing.update(t["value"])
            else:
                content["assets"].append(dict(t["value"]))
        else:
            next(
                s
                for s in content["sections"]
                if s["transformation_target_id"] == target
            ).update(t["value"])


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_old_answers_are_unused_inputs_immutable_and_local_replay_empty(case):
    ctx = deepcopy(case["context"])
    for key in ["answer", "solution"]:
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert plan(case, ctx).transformations == ()
    old = BeautifulSoup(section(before, "condition")["html"], "html.parser")
    new = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
    old.img.decompose()
    new.img.decompose()
    assert str(old) == str(new)


@pytest.mark.parametrize("group", [g["key"] for g in DATA["groups"]])
@pytest.mark.parametrize("change", ["extra", "missing", "changed_method"])
def test_unreviewed_or_missing_parent_blocks_before_preparing(group, change):
    case = next(c for c in CASES if c["task"] == group)
    html = parent_html(group)
    if change == "extra":
        html += "<p>Другой метод.</p>"
    elif change == "missing":
        html = ""
    else:
        html = html.replace(r"\angle", r"\sin")
    with pytest.raises(ContentPlanError):
        plan(case, parent=html)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_instructions_are_not_discarded(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Удвойте результат.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ["47673", "641148"])
def test_generated_svg_checksum_mismatch_is_rejected(task):
    case = next(c for c in CASES if c["task"] == task)
    g = GROUPS[case["group"]]
    assets = tuple(dict(a, sha256="0" * 64) for a in generated(case))
    with pytest.raises(ContentPlanError):
        get_handler(g["rule"]).plan(
            PlanInput(
                case["context"],
                parent_asset_id=g["parent_asset"],
                parent_solution_html=parent_html(case["group"]),
                generated_solution_assets=assets,
            )
        )


def test_switch_to_bisector_reuses_the_existing_compatible_svg():
    case = next(c for c in CASES if c["task"] == "500908")
    result = plan(case)
    assert generated(case) == ()
    figure = next(
        t
        for t in result.transformations
        if t["transformation_target_id"] == "asset:image_1"
    )
    assert figure["operation"] == "rewrite"
    assert figure["value"]["asset_id"] == GROUPS["27770"]["parent_asset"]
    assert "медиана" not in solution_html(result)


def test_zero_uses_coincident_height_and_bisector_without_false_strict_inequality():
    case = next(c for c in CASES if c["task"] == "47673")
    result = plan(case)
    assert result.answer == "45" and "H = D" in solution_html(result)
    assert "очевидно больше" not in solution_html(result)
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    assert len(specs) == 1 and 'id="ray-D-H"' in specs[0]["svg_text"]
