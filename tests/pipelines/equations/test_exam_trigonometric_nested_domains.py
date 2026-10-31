"""Nested roots, original ratio poles and explicit pending SVG verification."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_compile import C
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_nested_domains.json"
    ).read_text()
)
CASES = DATA["cases"]
PENDING = DATA["pending_cases"]
ALL = [*CASES, *PENDING]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {
    "530063": "0 1",
    "530699": "1/6",
    "535423": "",
    "547543": "0 1/8 1/4 3/8 1/2 5/8 3/4 7/8",
    "556614": "-3 -11/4 -2",
    "556621": "-2 -4/3 -1",
    "562491": "-5/4",
}
RESIDUES = {
    "530063": "0 1",
    "530699": "1/6 5/6",
    "535423": "3/4",
    "547543": "0 1/8 1/4 3/8 1/2 5/8 3/4 7/8 9/8 5/4 11/8 3/2 13/8 7/4 15/8",
    "556614": "0 3/4 1 5/4",
    "556621": "0 2/3 1 4/3",
    "562491": "3/4",
}
ORIGINAL = {
    "530063": sp.tan(X) * s * s - sp.tan(X),
    "530699": (2 * s * s - 3 * s + 1) / sp.tan(X),
    "535423": (1 + 2 * s * s - 3 * sp.sqrt(2) * s + sp.sin(2 * X)) / (2 * s * c - 1)
    - 1,
    "547543": (sp.cos(2 * X) * sp.cos(8 * X) - sp.cos(10 * X)) / (c + 1),
    "556614": 2 * s + sp.sqrt(2) * sp.tan(X),
    "556621": 2 * s + sp.tan(X),
}
ORIGINAL["562491"] = ORIGINAL["535423"]
POLES = {
    "530063": (c,),
    "530699": (s, c),
    "535423": (2 * s * c - 1,),
    "547543": (c + 1,),
    "556614": (c,),
    "556621": (c,),
    "562491": (2 * s * c - 1,),
}


def case(task):
    return next(c for c in ALL if c["task"] == task)


def parent(example):
    return next(
        s["html"]
        for c in ALL
        if c["task"] == example["group"]
        for s in c["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example):
    prepared = deepcopy(example["context"])
    prepared["normalized_content"]["assets"] = []
    for section in prepared["normalized_content"]["sections"]:
        section["asset_keys"] = []
    _, f, i, b = read(prepared)
    return analyze(f, i, b, parent(example))


def plan(example, context=None):
    handler = get_handler(get_group_profile(example["group"]).content_rule_key)
    return handler.plan(
        PlanInput(context or example["context"], parent_solution_html=parent(example))
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_one_rule_without_claiming_unverified_figures_are_ready(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"], "14")


@pytest.mark.parametrize("example", ALL, ids=lambda c: c["task"])
def test_math_only_full_and_selected_roots_are_independent_of_saved_content(example):
    task = example["task"]
    a = analysis(example)
    assert select(a.series, (0, 2, True, False))[0] == tuple(
        map(sp.Rational, RESIDUES[task].split())
    )
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    for q in select(a.series, (0, 2, True, False))[0]:
        assert all(sp.simplify(p.subs(X, q * sp.pi)) != 0 for p in POLES[task])
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
    for k in range(32):
        q = sp.Rational(k, 16)
        allowed = all(sp.simplify(p.subs(X, q * sp.pi)) != 0 for p in POLES[task])
        zero = allowed and sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
        assert (q in select(a.series, (0, 2, True, False))[0]) == zero


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(example):
    original = deepcopy(example["context"])
    p = plan(example)
    assert example["context"] == original
    changed = deepcopy(original)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>не использовать</p>"
    assert (plan(example, changed).answer, plan(example, changed).solution_html) == (
        p.answer,
        p.solution_html,
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        item = next(
            s
            for s in changed["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        )
        item.update(t["value"])
    assert plan(example, changed).transformations == ()
    assert not original["normalized_content"]["assets"]
    assert (
        get_handler(get_group_profile(example["group"]).content_rule_key).diagram_specs(
            original
        )
        == ()
    )


@pytest.mark.parametrize("example", PENDING, ids=lambda c: c["task"])
def test_real_context_is_blocked_until_its_original_svg_has_been_audited(example):
    handler = get_handler(get_group_profile(example["group"]).content_rule_key)
    with pytest.raises(UnsupportedCondition, match="audited source circle"):
        handler.diagram_specs(example["context"])
    with pytest.raises(UnsupportedCondition, match="audited source circle"):
        plan(example)


def test_equal_product_split_preserves_zero_tangent_and_excludes_zero_cosine_branch():
    example = case("530063")
    a = analysis(example)
    p = plan(example)
    assert a.ratio_product.method == "split_equal" and a.poles == (C,)
    assert not a.branches[1].values and set(a.branches[1].excluded) == {
        -sp.S.One,
        sp.S.One,
    }
    soup = BeautifulSoup(p.solution_html, "html.parser")
    text = soup.get_text(" ")
    assert "не деля на тангенс" in text and "косинус равен нулю" in text
    assert "Введём обозначение" not in text and not soup.find("img")


def test_dyadic_series_preserve_parent_order_disjointness_and_excluded_pi():
    a = analysis(case("547543"))
    assert a.angle_product.nested and a.angle_product.note and a.angle_product.addition
    assert a.series == (
        (sp.Rational(1, 8), sp.Rational(1, 4)),
        (sp.Rational(1, 4), sp.Rational(1, 2)),
        (sp.Rational(1, 2), sp.S.One),
        (sp.S.Zero, sp.Integer(2)),
    )
    seen = set()
    for series in a.series:
        roots = set(select((series,), (0, 2, True, False))[0])
        assert not roots & seen
        seen |= roots
    assert (
        seen == set(map(sp.Rational, RESIDUES["547543"].split()))
        and sp.S.One not in seen
    )
    _, _, html = render(a, "")
    soup = BeautifulSoup(html, "html.parser")
    parts = soup.find("ol").find_all("li", recursive=False)
    assert (
        "Примечание" in parts[1].get_text()
        and "непересекающимися" in parts[1].get_text()
    )
    assert len(a.selected) == 8 and "Введём обозначение" not in soup.get_text()


@pytest.mark.parametrize("task", ["556614", "556621"])
def test_integer_n_is_preserved_in_all_rendered_math_without_changing_source_identifiers(
    task,
):
    example = case(task)
    a = analysis(example)
    assert a.parameter == "n"
    marker = '<img data-asset-key="image_1" src="/assets/preview-k"/>'
    answer, answer_html, html = render(a, marker)
    assert marker in html and " k" not in answer_html
    assert r"\in\mathbb Z" in answer and " n" in answer and " k" not in answer
    assert " k" not in " ".join(
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )
