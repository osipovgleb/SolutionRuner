"""Complete original radical domains, isolated zeros and nonperiodic index sets."""

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_global_indices import (
    X,
    exact_floor,
)
from solution_runner.pipelines.equations.exam_trigonometric_global_radical import (
    compile_global,
)
from solution_runner.pipelines.equations.exam_trigonometric_global_radical_proof import (
    all_roots,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_global_radicals.json"
    ).read_text()
)
CASES = DATA["cases"]
EXPECTED = {
    "670044": (sp.Rational(20, 3), sp.Integer(7)),
    "674196": (
        -sp.sqrt(3) / sp.pi,
        sp.S.Zero,
        sp.sqrt(3) / sp.pi,
        2 / sp.pi,
        sp.Rational(-5, 2),
        sp.Rational(-3, 2),
        sp.Rational(1, 2),
    ),
    "678031": (sp.Rational(-1, 6), sp.Rational(7, 6)),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(example):
    return next(
        s["html"]
        for s in example["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(example, context=None):
    _, f, i, b = read(context or example["context"])
    return analyze(f, i, b, parent(example))


def plan(example, context=None):
    return get_handler(get_group_profile(example["group"]).content_rule_key).plan(
        PlanInput(context or example["context"], parent_solution_html=parent(example))
    )


def full_membership(a, x):
    data = a.global_radical
    if any(sp.simplify(x - point) == 0 for point in data.points):
        return True
    for f in data.families:
        index = sp.simplify((x / sp.pi - f.offset) / f.period)
        if index.is_Integer is True and f.accepts(int(index)):
            return True
    return False


def original_value(key, x):
    if key == "670044":
        rad = 49 * math.pi**2 - x * x
        return (
            None if rad < -1e-8 else (4 * math.cos(x) ** 2 - 1) * math.sqrt(max(rad, 0))
        )
    if key == "674196":
        rad = x * (x - 2) * (x * x - 3)
        return None if rad < -1e-8 else math.sqrt(max(rad, 0)) * math.cos(x)
    if abs(math.cos(x)) < 1e-10:
        return None
    rad = x * math.tan(x)
    return None if rad <= 1e-10 else (2 * math.sin(x) + 1) / math.sqrt(rad)


def changed(example, *, formula=None, interval=None):
    context = deepcopy(example["context"])
    sec = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(sec["html"], "html.parser")
    if formula is not None:
        soup.select("[data-inline-latex]")[0]["data-inline-latex"] = formula
    if interval is not None:
        row = soup.find_all("li")[1]
        row.clear()
        row.append(
            "Найдите все корни уравнения, принадлежащие промежутку " + interval + "."
        )
    sec["html"] = str(soup)
    return context


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_reuses_one_rule_and_exact_catalog_coordinates(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"], "14")


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_complete_domain_and_selected_roots_match_the_original_equation(example):
    a = analysis(example)
    key = example["task"]
    assert a.selected == EXPECTED[key]
    assert a.selection_method == "global_domain"
    for q in a.selected:
        value = original_value(key, float(q * sp.pi))
        assert value is not None and abs(value) < 1e-7
    for k in range(-192, 193):
        q = sp.Rational(k, 24)
        value = original_value(key, float(q) * math.pi)
        assert full_membership(a, q * sp.pi) == (
            value is not None and abs(value) < 1e-7
        ), (key, q)
    for point in a.global_radical.points:
        assert full_membership(a, point)
        assert sp.simplify(a.global_radical.polynomial.subs(X, point)) == 0


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(example):
    original = deepcopy(example["context"])
    p = plan(example)
    assert example["context"] == original
    changed = deepcopy(original)
    for section in changed["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>Не использовать.</p>"
    other = plan(example, changed)
    assert (other.answer, other.solution_html) == (p.answer, p.solution_html)
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith(("asset:", "section:condition"))
        section = next(
            s
            for s in changed["normalized_content"]["sections"]
            if s["transformation_target_id"] == key
        )
        section.update(t["value"])
    assert plan(example, changed).transformations == ()
    assert not original["normalized_content"]["assets"]
    assert (
        get_handler(get_group_profile(example["group"]).content_rule_key).diagram_specs(
            original
        )
        == ()
    )
    assert not BeautifulSoup(p.solution_html, "html.parser").find("img")


def test_bounded_full_answer_has_thirty_roots_and_no_unbounded_family_leak():
    e = case("670044")
    a = analysis(e)
    data = a.global_radical
    assert data.points == (-7 * sp.pi, 7 * sp.pi)
    assert all(f.windows == ((-7, 6),) for f in data.families)
    full = {
        *data.points,
        *(
            (f.offset + f.period * k) * sp.pi
            for f in data.families
            for k in range(-7, 7)
        ),
    }
    assert len(full) == 30
    assert not full_membership(a, sp.Rational(22, 3) * sp.pi)
    wide = analysis(e, changed(e, interval="[-25;25]"))
    assert len(wide.selected) == 30 and set(wide.selected) == {x / sp.pi for x in full}
    answer = all_roots(a)
    assert r"\ldots" in answer and "-7" in answer and r"\in\mathbb Z" not in answer


def test_original_radical_endpoints_respect_open_and_closed_selection_bounds():
    e = case("670044")
    closed = analysis(e, changed(e, interval=r"[20;7\pi]"))
    opened = analysis(e, changed(e, interval=r"[20;7\pi)"))
    assert closed.selected == (sp.Rational(20, 3), sp.Integer(7))
    assert opened.selected == (sp.Rational(20, 3),)
    assert all_roots(closed) == all_roots(opened)


def test_quartic_retains_all_isolated_roots_and_exactly_one_index_exception():
    e = case("674196")
    a = analysis(e)
    d = a.global_radical
    f = d.families[0]
    assert d.case_order
    assert d.points == (-sp.sqrt(3), 0, sp.sqrt(3), 2)
    assert f.windows == ((None, -2), (0, None))
    assert all(f.accepts(k) == (k != -1) for k in range(-30, 31))
    assert r"\mathbb Z\setminus\{-1\}" in all_roots(a)
    assert not full_membership(a, -sp.pi / 2)
    assert full_membership(a, sp.pi / 2)
    for x in d.points:
        assert full_membership(a, x)
    p = plan(e)
    assert p.solution_html.index("Случай 1") < p.solution_html.index("Случай 2")
    formulas = [
        "".join(n["data-inline-latex"].split())
        for n in BeautifulSoup(p.solution_html, "html.parser").select(
            "[data-inline-latex]"
        )
    ]
    assert r"x\in(-\infty;-\sqrt{3})\cup(0;\sqrt{3})\cup(2;\infty)" in formulas


def test_radical_zeros_are_not_lost_when_the_periodic_factor_only_vanishes_at_endpoints():
    e = case("674196")
    ctx = changed(e, formula=r"\sqrt{\frac{\pi^2}{4}-x^2}\cos x=0")
    a = analysis(e, ctx)
    assert a.global_radical.points == (-sp.pi / 2, sp.pi / 2)
    assert a.global_radical.families[0].windows == ()
    assert a.selected == (-sp.Rational(1, 2), sp.Rational(1, 2))
    assert r"\varnothing" not in all_roots(a)


def test_denominator_domain_keeps_two_natural_index_families_and_the_parent_letters():
    e = case("678031")
    a = analysis(e)
    negative, positive = a.global_radical.families
    assert a.global_radical.denominator and not a.global_radical.points
    assert negative.windows == ((None, 0),) and negative.parameter == "k"
    assert positive.windows == ((0, None),) and positive.parameter == "m"
    assert (negative.offset, negative.period) == (-sp.Rational(1, 6), 2)
    assert (positive.offset, positive.period) == (sp.Rational(7, 6), 2)
    assert a.poles
    assert not full_membership(a, 0)
    assert not full_membership(a, sp.Rational(11, 6) * sp.pi)
    assert not full_membership(a, -sp.Rational(5, 6) * sp.pi)
    answer = all_roots(a)
    assert "m" in answer and "k" in answer and r"\mathbb N\cup\{0\}" in answer
    assert "2 \\pi k" in answer and "2 \\pi m" in answer


@pytest.mark.parametrize(
    "value",
    [
        sp.Rational(-1, 2),
        -sp.sqrt(3) / sp.pi - sp.Rational(1, 2),
        2 / sp.pi - sp.Rational(1, 2),
        sp.sqrt(21) / sp.pi - sp.Rational(1, 2),
    ],
)
def test_index_bounds_are_exactly_certified(value):
    n = exact_floor(value)
    assert n <= value < n + 1


@pytest.mark.parametrize(
    "formula,method",
    [
        (r"\sqrt{x^2+1}\cos x=0", "product"),
        (r"\sqrt{x^3-1}\cos x=0", "product"),
        (r"\sqrt{49\pi^2-x^2}/\sin x=0", "product"),
        (r"\cos x\sqrt{49\pi^2-x^2}+1=0", "product"),
        (r"\frac{\sin x}{\sqrt{x\tg x}+1}=0", "quotient"),
        (r"\sqrt{49\pi^2-y^2}\cos x=0", "product"),
        (r"\sqrt{49\pi^2-x^2}\cos x=0", "quotient"),
    ],
)
def test_unreviewed_domains_poles_and_radical_positions_fail_closed(formula, method):
    with pytest.raises(UnsupportedCondition):
        compile_global(formula, method)


def test_open_periodic_and_isolated_endpoints_both_stay_excluded():
    e = case("670044")
    ctx = changed(e, interval=r"(\frac{20\pi}{3};7\pi)")
    a = analysis(e, ctx)
    assert a.selected == ()
    assert r"\varnothing" in plan(e, ctx).answer


def test_parent_n_and_m_stay_attached_to_their_own_series():
    fixture = json.loads(
        (
            Path(__file__).parent / "fixtures/category_14_trigonometric_addition.json"
        ).read_text()
    )
    source = next(c for c in fixture["cases"] if c["task"] == "527157")
    _, f, i, b = read(source["context"])
    prototype = next(
        s["html"]
        for s in source["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    result = analyze(f, i, b, prototype)
    assert dict(zip(result.series, result.family_parameters)) == {
        (sp.Rational(5, 4), sp.Integer(2)): "m",
        (sp.Rational(7, 4), sp.Integer(2)): "n",
    }
    assert result.selected == (sp.Rational(5, 4), sp.Rational(7, 4))


def test_adjacent_index_windows_can_recover_an_unrestricted_family_without_losing_zero():
    e = case("674196")
    ctx = changed(e, formula=r"\sqrt{x^2}\cos x=0")
    result = analysis(e, ctx)
    assert result.global_radical.points == (sp.S.Zero,)
    assert result.global_radical.families[0].windows == ((None, None),)
    assert full_membership(result, -sp.pi / 2)
    assert full_membership(result, sp.S.Zero)
    answer = all_roots(result)
    assert r"\mathbb Z" in answer and "None" not in answer
