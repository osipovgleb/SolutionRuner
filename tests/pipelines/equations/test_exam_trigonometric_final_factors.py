"""Final affine factors, half angles, and interval selection by inequalities."""

import gzip
import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    decode,
    ordered,
    turn,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_final_factors.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {
    "694140": "17/4",
    "694561": "1 5/4 3/2",
    "694818": "-6 -14/3 -4",
    "694837": "-8 -20/3 -6",
    "696382": "9/2 14/3",
    "696450": "4 25/6",
    "697347": "13/4 7/2",
    "697375": "7 29/4",
    "697901": "4 9/2 6",
    "697930": "8 25/3 10",
    "701415": "-11/6 -5/6",
    "701416": "5/4",
}
RESIDUES = {
    "694140": "1/4 7/4",
    "694561": "0 1/4 1/3 1/2 3/4 1 5/4 3/2 5/3 7/4",
    "694818": "0 2/3",
    "694837": "0 4/3",
    "696382": "1/2 2/3 3/2 5/3",
    "696450": "0 1/6 1 7/6",
    "697347": "1/4 1/2 5/4 3/2",
    "697375": "0 1/4 1 5/4",
    "697901": "0 1/2",
    "697930": "0 1/3",
    "701415": "1/6 7/6",
    "701416": "1/4 5/4",
}
ORIGINAL = {
    "694140": sp.sqrt(10) - sp.sqrt(2) * s - sp.sqrt(20) * c - sp.sin(sp.pi + 2 * X),
    "694561": sp.cos(3 * X - sp.pi / 2)
    + sp.cos(5 * X + 3 * sp.pi / 2)
    - sp.sin(sp.pi - 4 * X),
    "694818": sp.cos(sp.pi / 2 + X / 2) - sp.sin(sp.pi + X),
    "694837": sp.cos(sp.pi / 2 - X / 2) + sp.sin(sp.pi - X),
    "696382": sp.cos(sp.pi / 2 - 2 * X) + sp.sqrt(12) * c * c,
    "696450": sp.cos(sp.pi / 2 + 2 * X) + sp.sqrt(12) * s * s,
    "697347": c * c + sp.sin(X - sp.pi / 4) ** 2 - sp.Rational(1, 2),
    "697375": s * s + sp.cos(X + sp.pi / 4) ** 2 - sp.Rational(1, 2),
    "697901": s - sp.sqrt(2) * sp.cos(sp.pi / 2 - X / 2),
    "697930": s + sp.sqrt(3) * sp.cos(3 * sp.pi / 2 - X / 2),
    "701415": 2 * sp.cos(X - sp.pi / 3) + 2 * sp.sin(3 * sp.pi / 2 + X),
    "701416": 2 * sp.cos(X - sp.pi / 4) - 2 * sp.sqrt(2) * sp.sin(sp.pi / 2 + X),
}
IDENTITY = {
    "694140": (1 - sp.sqrt(2) * c) * (sp.sqrt(10) - sp.sqrt(2) * s),
    "694561": sp.sin(4 * X) * (2 * c - 1),
    "694818": sp.sin(X / 2) * (2 * sp.cos(X / 2) - 1),
    "694837": sp.sin(X / 2) * (2 * sp.cos(X / 2) + 1),
    "696382": 2 * c * (s + sp.sqrt(3) * c),
    "696450": 2 * s * (sp.sqrt(3) * s - c),
    "697347": c * (c - s),
    "697375": s * (s - c),
    "697901": sp.sin(X / 2) * (2 * sp.cos(X / 2) - sp.sqrt(2)),
    "697930": sp.sin(X / 2) * (2 * sp.cos(X / 2) - sp.sqrt(3)),
    "701415": sp.sqrt(3) * s - c,
    "701416": sp.sqrt(2) * (s - c),
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
    ctx = context or c["context"]
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in handler.diagram_specs(ctx)
    )
    return handler.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_one_shared_rule(g):
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
def test_original_algebra_and_complete_and_selected_roots_are_independent(c):
    task = c["task"]
    a = analysis(c)
    assert sp.trigsimp(sp.expand_trig(ORIGINAL[task] - IDENTITY[task])) == 0
    assert a.selected == tuple(map(sp.sympify, SELECTED[task].split()))
    assert select(a.series, (0, 2, True, False))[0] == tuple(
        map(sp.Rational, RESIDUES[task].split())
    )
    for q in a.selected:
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    original = deepcopy(c["context"])
    p = plan(c)
    assert c["context"] == original
    changed = deepcopy(original)
    for s in changed["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>не использовать</p>"
    assert (
        plan(c, changed).answer == p.answer
        and plan(c, changed).solution_html == p.solution_html
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = changed["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, changed).transformations == ()
    assert (
        changed["normalized_content"]["assets"][
            : len(original["normalized_content"]["assets"])
        ]
        == original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_figures_match_complete_or_selected_points_and_keep_original_bytes(c):
    a = analysis(c)
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    specs = handler.diagram_specs(c["context"])
    assert specs == ()
    assets = c["context"]["normalized_content"]["assets"]
    if not assets:
        assert a.selection_method == "inequalities"
        assert not BeautifulSoup(plan(c).solution_html, "html.parser").find("img")
        return
    asset = assets[0]["asset_id"]
    e = CIRCLES[asset]
    assert (
        hashlib.sha256(
            gzip.decompress((DIRECTORY / (asset + ".svgz")).read_bytes())
        ).hexdigest()
        == e["sha256"]
    )
    cx, cy, _ = e["circle"]
    for m in e["green_markers"]:
        q = float(sp.Rational(m["angle"])) * math.pi
        assert (
            math.hypot(
                m["x"] - cx - m["radius"] * math.cos(q),
                m["y"] - cy + m["radius"] * math.sin(q),
            )
            < 1
        )
    validate(e, a)
    expected = (
        ordered(turn(q) for q in a.selected)
        if e.get("point_scope") == "selected"
        else select(a.series, (0, 2, True, False))[0]
    )
    assert tuple(map(decode, e["residues"])) == expected
    assert len(BeautifulSoup(plan(c).solution_html, "html.parser").find_all("img")) == 1


@pytest.mark.parametrize("task", ["694818", "694837", "697901", "697930"])
def test_half_angle_uses_full_four_pi_period_and_integer_selection(task):
    a = analysis(case(task))
    assert a.scale == sp.Rational(1, 2)
    assert a.series[0] == (0, 2) and all(period == 4 for _, period in a.series[1:])
    actual = select(a.series, (0, 4, True, False))[0]
    for k in range(48):
        q = sp.Rational(k, 12)
        assert (sp.simplify(IDENTITY[task].subs(X, q * sp.pi)) == 0) == (q in actual)
    html = plan(case(task)).solution_html
    assert "целого параметра" in html and "D=" not in html
    assert "Вынесем общий множитель и приравняем каждый множитель к нулю" in html


def test_half_angle_unknown_selection_method_does_not_silently_choose_inequalities():
    c = case("694818")
    unknown = re.sub(r"<span[^>]*data-inline-latex[^>]*>.*?</span>", "", parent(c))
    from solution_runner.pipelines.equations.exam_trigonometric_style import (
        parent_style,
    )

    with pytest.raises(UnsupportedCondition):
        parent_style(unknown)


def test_impossible_sine_level_is_excluded_and_never_copied_from_saved_solution():
    a = analysis(case("694140"))
    assert any(sp.sqrt(5) in b.candidates and not b.values for b in a.branches)
    html = plan(case("694140")).solution_html
    assert "не входит в отрезок" in html and "|\\sin x|<1" not in html


@pytest.mark.parametrize("task", ["696382", "696450"])
def test_zero_factor_is_kept_before_local_cotangent_division(task):
    a = analysis(case(task))
    assert len(a.branches) == 2 and a.branches[0].variable == (
        C if task == "696382" else S
    )
    html = plan(case(task)).solution_html
    assert "\\ctg" in html and "только в этой ветви разделим на синус" in html


def test_interval_or_root_changes_reject_an_incompatible_source_circle():
    c = case("701416")
    a = analysis(c)
    asset = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    with pytest.raises(UnsupportedCondition):
        validate(CIRCLES[asset], replace(a, selected=(sp.Rational(1, 4),)))


@pytest.mark.parametrize("task", ["697347", "697375"])
def test_factorization_displays_the_reduced_product_before_its_branches(task):
    from solution_runner.pipelines.equations.exam_trigonometric_proof import formula

    html = plan(case(task)).solution_html
    product = -C * (S - C) if task == "697347" else S * (S - C)
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert formula(product) + "=0" in formulas
    assert html.index("Произведение равно нулю") < html.index(
        "Рассмотрим линейный множитель"
    )
