"""Shifted angles reuse the exact polynomial solver and audited source circles."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, parent_style
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_reductions.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
ORIGINAL = {
    "526215": sp.cos(2 * X) + sp.sqrt(2) * sp.cos(sp.pi / 2 + X) + 1,
    "660752": sp.cos(2 * X) - sp.sqrt(3) * sp.cos(X - sp.pi) + 1,
    "660755": sp.cos(2 * X) + sp.sqrt(3) * sp.sin(X + sp.pi) - 1,
    "660884": sp.cos(2 * X) - sp.sqrt(2) * sp.sin(X + sp.pi) - 1,
    "513071": sp.cos(2 * X) - sp.sqrt(2) * sp.cos(3 * sp.pi / 2 + X) - 1,
    "513092": 2 * sp.cos(2 * X) + 4 * sp.cos(3 * sp.pi / 2 - X) + 1,
    "505422": sp.cos(2 * X) + sp.sqrt(2) * sp.sin(sp.pi / 2 + X) + 1,
    "548383": sp.cos(2 * X) + sp.sqrt(2) * sp.cos(sp.pi / 2 - X) - 1,
    "526289": 8 * sp.sin(X) ** 2 - 2 * sp.sqrt(3) * sp.cos(sp.pi / 2 - X) - 9,
}
RESIDUES = {
    "526215": "1/4 3/4",
    "660752": "1/2 5/6 7/6 3/2",
    "660755": "0 1 4/3 5/3",
    "660884": "0 1/4 3/4 1",
    "513071": "0 1 5/4 7/4",
    "513092": "1/6 5/6",
    "505422": "1/2 3/4 5/4 3/2",
    "548383": "0 1/4 3/4 1",
    "526289": "4/3 5/3",
}
SELECTED = {
    "526215": "9/4 11/4",
    "660752": "3/2 5/2 17/6",
    "660755": "2 3 10/3",
    "660884": "-13/4 -3 -2",
    "513071": "7/4 2 3",
    "513092": "13/6 17/6",
    "505422": "-11/4 -5/2 -3/2",
    "548383": "11/4 3 4",
    "526289": "-7/3",
}


def parent(c):
    p = next(t for t in CASES if t["task"] == c["group"])
    return next(
        s["html"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_the_same_rule_at_the_original_catalog_position(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (p.source_group_id, p.snapshot_theme_id, p.group_order_index) == (
        g["uuid"],
        g["theme_uuid"],
        g["order"],
    )
    assert p.theme_order_index == 4 and p.category_key == "14"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_exact_root_sets_and_independently_written_original_equations(c):
    _, formula, interval, bounds = read(c["context"])
    a = analyze(formula, interval, bounds, parent(c))
    assert a.residues == tuple(map(sp.Rational, RESIDUES[c["task"]].split()))
    assert a.selected == tuple(map(sp.Rational, SELECTED[c["task"]].split()))
    for q in (*a.residues, *a.selected):
        assert sp.simplify(ORIGINAL[c["task"]].subs(X, q * sp.pi)) == 0
    assert a.residues == tuple(
        sp.Rational(i, 12)
        for i in range(24)
        if sp.simplify(ORIGINAL[c["task"]].subs(X, sp.pi * i / 12)) == 0
    )
    assert a.substitution == ("t" if c["group"] == "526215" else None)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_condition_and_assets(c):
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
            s["html"] = "<p>UNUSED99999</p>"
    assert plan(c, ctx) == p
    for t in p.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        section = next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        )
        section.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    image = BeautifulSoup(p.solution_html, "html.parser").find_all("img")
    assert len(image) == 1
    assert (
        image[0]["data-asset-id"] == ctx["normalized_content"]["assets"][0]["asset_id"]
    )
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    assert handler.diagram_specs(ctx) == ()
    assert "Примечание" not in p.solution_html


def test_a_figure_alone_does_not_supply_an_unknown_selection_method():
    c = next(c for c in CASES if c["task"] == "513071")
    source = parent(c)
    assert parent_style(source)[-1] == "circle"
    with pytest.raises(UnsupportedCondition):
        parent_style(source.replace("ука­зан­ном", "неизвестном"))
    with pytest.raises(UnsupportedCondition):
        parent_style(str(BeautifulSoup(source, "html.parser").find("img")))


def test_factoring_preserves_zero_branch_and_adapts_to_a_nonzero_child_constant():
    c = next(c for c in CASES if c["task"] == "513071")
    html = plan(c).solution_html
    assert "Вынесем общий множитель" in html and "D=" not in html
    assert r"(\sin x)=0" in html and r"x=\pi k" in html
    child = next(c for c in CASES if c["task"] == "513092")
    html = plan(child).solution_html
    assert "Разложим квадратный трёхчлен" in html and "D=" not in html
    assert "не входит в отрезок" in html
