"""Variable bases, factor branches and original domains are independently checked."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_exponential import X
from solution_runner.pipelines.equations.exam_input import endpoint
from solution_runner.pipelines.equations.exam_logarithmic_algebra import roots
from solution_runner.pipelines.equations.exam_logarithmic_branches import (
    allowed,
    analyze,
)
from solution_runner.pipelines.equations.exam_logarithmic_reference import read
from solution_runner.pipelines.equations.exam_scalar import compare
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_logarithmic_branches.json"
    ).read_text()
)
CASES = DATA["cases"]
EXPECTED = {
    "550261": ((-3, 3), (3,)),
    "555265": ((-sp.Rational(17, 2), -8), (-sp.Rational(17, 2), -8)),
    "561853": ((-1 - sp.sqrt(3), -1 - sp.sqrt(2)), (-1 - sp.sqrt(2),)),
    "643200": ((1, 3), (1,)),
    "643683": ((3, 4), (3,)),
    "643677": ((-2, 2), (-2,)),
    "693985": ((3, 5), (3,)),
}
L = sp.log
ORIGINAL = {
    "550261": L(X**2 - 5) / L(2) * (L(7 - X) / L(3)) ** 2
    + 3 * L(X**2 - 5) / L(2)
    - 2 * (L(7 - X) / L(3)) ** 2
    - 6,
    "555265": L(2 * X**2 + 136) / L(-(X**2) - 32 * X + 33)
    - L(-33 * X) / L((1 - X) * (X + 33)),
    "561853": (X**2 + 2 * X - 1)
    * (L(X**2 - 3) / L(2) + L(sp.sqrt(3) - X) / L(sp.Rational(1, 2))),
    "643200": L(X) / L(3) * L(4 * X**2 - 1) / L(3) - L(X * (4 * X**2 - 1) / 3) / L(3),
    "643683": L(X) / L(4) * L((X**2 - 1) / 2) / L(4) - L(X * (X**2 - 1) / 8) / L(4),
    "643677": L(X**3 + 6 * X**2 - 3 * X - 19) / L(3) - L(X + 5) / L(3),
    "693985": L(X - 2) / L(8 * X - 12 - X**2) - L(X - 2) / L(18 - 3 * X),
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for s in case(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(c, context=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
        )
    )


def analysis(c, context=None):
    _, formula, interval, bounds = read(context or c["context"])
    return analyze(formula, interval, bounds, parent(c))


def changed(task, old, new):
    c = case(task)
    context = deepcopy(c["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert old in s["html"]
    s["html"] = s["html"].replace(old, new)
    return c, context


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_six_profiles_share_exact_catalogue_positions_and_one_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-logarithmic-branches"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.category_key,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], "14", 3, g["order"])


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_independent_root_sets_and_original_equations(c):
    a = analysis(c)
    assert (a.selection.roots, a.selection.selected) == EXPECTED[c["task"]]
    for root in a.selection.roots:
        assert allowed(root, a.constraints)
        assert (
            sp.simplify(sp.expand_log(ORIGINAL[c["task"]].subs(X, root), force=True))
            == 0
        )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_does_not_change_assets_or_condition(c):
    context = deepcopy(c["context"])
    before = deepcopy(context)
    p = plan(c, context)
    assert context == before
    assert p.condition_html == next(
        s["html"]
        for s in before["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    for s in context["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>INVALID 999999</p>"
    other = plan(c, context)
    assert (other.answer, other.solution_html) == (p.answer, p.solution_html)
    for t in p.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        s = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        )
        s.update(t["value"])
    assert (
        context["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
    )
    assert plan(c, context).transformations == ()


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_numeric_values_do_not_supply_the_child_equation(c):
    soup = BeautifulSoup(parent(c), "html.parser")
    for span in soup.select("[data-inline-latex]"):
        span["data-inline-latex"] = re.sub(r"\d+", "997", span["data-inline-latex"])
    assert plan(c, prototype=str(soup)) == plan(c)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_empty_parent_unknown_instructions_and_assets_fail_closed(c):
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype="")
    context = deepcopy(c["context"])
    context["normalized_content"]["assets"].append({"asset_key": "unknown"})
    with pytest.raises(UnsupportedCondition):
        plan(c, context)
    context = deepcopy(c["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    s["html"] = s["html"].replace("Ре­ши­те", "Приближённо решите")
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


def test_polynomial_factor_does_not_override_logarithm_domains():
    a = analysis(case("561853"))
    proposed = {r for b in a.branches for r in b.candidates}
    assert -1 + sp.sqrt(2) in proposed and sp.sqrt(3) in proposed
    assert not allowed(-1 + sp.sqrt(2), a.constraints) and not allowed(
        sp.sqrt(3), a.constraints
    )
    assert a.selection.roots == (-1 - sp.sqrt(3), -1 - sp.sqrt(2))


def test_positive_logarithm_square_factor_is_proved_nonzero():
    a = analysis(case("550261"))
    assert len(a.positive) == 1 and len(a.branches) == 1
    p = plan(case("550261")).solution_html
    assert "не обращается в нуль" in p


def test_variable_bases_keep_the_argument_one_branch_even_when_bases_differ():
    a = analysis(case("693985"))
    assert {r for b in a.branches for r in b.candidates} == {3, 5, 6}
    assert a.atoms[0].base.subs(X, 3) != a.atoms[1].base.subs(X, 3)
    assert 3 in a.selection.roots and 6 not in a.selection.roots


def test_argument_one_still_needs_both_original_bases_defined():
    c, context = changed("693985", r"8x-12-x^{2}", r"8x-14-x^{2}")
    assert analysis(c, context).selection.roots == ()
    plan(c, context)


def test_reciprocal_logarithm_denominator_cannot_be_zero():
    c, context = changed(
        "555265",
        r"\log_{(-x^{2}-32x+33)} (2x^{2}+136)=\frac{1}{\log_{(-33x)} ((1-x)(x+33))}",
        r"\log_{(x+1)} (x+2)=\frac{1}{\log_{(2)} (x+1)}",
    )
    a = analysis(c, context)
    assert a.branches[0].candidates == (0,) and a.selection.roots == ()
    plan(c, context)


def test_corrupted_source_domain_exclusions_are_recomputed():
    a = analysis(case("555265"))
    excluded = {
        r for p, rel in a.constraints if rel == "nonzero" and p.has(X) for r in roots(p)
    }
    assert excluded == {
        -sp.Rational(1, 33),
        -16 - 12 * sp.sqrt(2),
        -16 + 12 * sp.sqrt(2),
    }
    html = plan(case("555265")).solution_html
    assert r"-\frac{1}{33}" in html.replace(" ", "") and "12" in html
    assert "x\\ne\\frac{1}{33}" not in html


def test_equal_logarithm_cubic_checks_the_simpler_argument_before_selection():
    a = analysis(case("643677"))
    assert set(a.branches[0].candidates) == {-6, -2, 2}
    assert -6 not in a.selection.roots
    html = plan(case("643677")).solution_html
    assert (
        html.index("отбрасывается")
        < html.index("Отберём корни")
        < html.index("Примечание")
    )
    assert "<img" not in html and "Правило</" not in html


@pytest.mark.parametrize(
    "mutation", ["identity", "url", "duplicate", "unknown_reference"]
)
def test_only_the_two_audited_service_icons_can_be_omitted(mutation):
    c = case("643677")
    context = deepcopy(c["context"])
    assets = context["normalized_content"]["assets"]
    if mutation == "identity":
        assets[0]["asset_id"] = "unknown"
    elif mutation == "url":
        assets[0]["url"] = "/assets/unknown"
    elif mutation == "duplicate":
        assets[1] = deepcopy(assets[0])
    else:
        s = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "solution"
        )
        s["html"] = s["html"].replace(
            'src="/assets/88cc43ec-bba0-4842-b479-c55a598eb26b"',
            'src="/assets/unknown"',
        )
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("555265", r"((1-x)(x+33))", r"((1-x)(x+34))"),
        ("550261", r"\log_2 (x^{2}-5)", r"\log_2 (x^{-1}-5)"),
        ("643200", r"\frac{x(4x^{2}-1)}{3}", r"\frac{x(4x^{2}-1)}{2}"),
        ("561853", r"(x^{2}+2x-1)", r"(x^{3}+x+1)"),
        ("693985", r"(18-3x)} (x-2)", r"(18-3x)} (x-3)"),
    ],
)
def test_unreviewed_identities_or_original_poles_fail_closed(task, old, new):
    c, context = changed(task, old, new)
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{\log_2 0{,}5}",
        r"\sqrt{\log_{1}2}",
        r"\sqrt{\log_2 4}+1",
    ],
)
def test_invalid_nested_logarithm_endpoints_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        endpoint(formula)


def test_nested_logarithm_endpoint_is_certified_between_zero_and_one():
    value = endpoint(r"\sqrt{\log_{0,2}0,3}")
    assert compare(value, sp.Integer(0)) > 0 and compare(value, sp.Integer(1)) < 0
    assert compare(endpoint(r"\sqrt{\log_2 16}"), sp.Integer(2)) == 0


def test_generic_product_identity_is_preserved_before_child_branches():
    for task in ("643200", "643683"):
        html = plan(case(task)).solution_html
        assert (
            html.index("Уравнение имеет вид")
            < html.index("Преобразуем уравнение")
            < html.index("Приравняем логарифмический множитель")
        )
