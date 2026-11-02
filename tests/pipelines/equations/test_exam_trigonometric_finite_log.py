"""Physical log-base domains filter actual finite translates, never just residues."""

import json
from copy import deepcopy
from pathlib import Path

import mpmath as mp
import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_exponential import X
from solution_runner.pipelines.equations.exam_input import read
from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_finite_log import data_of
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    conditions,
    failed,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_variable import Parser
from solution_runner.pipelines.equations.exam_trigonometric_proof import first, render
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_finite_log.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
DEFAULT_WEIGHTS = (1, sp.sqrt(3))


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None, bounds=None, interval=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, interval or i, bounds or b, parent(c))


def plan(c, context=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
        )
    )


def forms(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def equation(
    base, numerator=r"\sin x+\sqrt{3}\cos x", fixed="2", denominator=r"\sin 3x"
):
    return (
        r"\log_{("
        + base
        + r")}\frac{"
        + numerator
        + "}{"
        + denominator
        + r"}=\frac{1}{\log_{"
        + fixed
        + "}("
        + base
        + ")}"
    )


def original_zero(q, coefficients=(-1, 2, 3), weights=DEFAULT_WEIGHTS, fixed=2):
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        base = coefficients[0] * x * x + coefficients[1] * x + coefficients[2]
        denominator = mp.sin(3 * x)
        eps = mp.mpf("1e-48")
        if base <= eps or abs(base - 1) < eps or abs(denominator) < eps:
            return False
        p, r = (mp.mpf(str(sp.N(v, 70))) for v in weights)
        argument = (p * mp.sin(x) + r * mp.cos(x)) / denominator
        if argument <= eps:
            return False
        d = mp.mpf(str(sp.N(fixed, 70)))
        value = mp.log(argument) / mp.log(base) - 1 / (mp.log(base) / mp.log(d))
        return abs(value) < mp.mpf("1e-43")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_finite_root_and_empty_interval_answer_match_original_logs(c):
    a = analysis(c)
    assert a.finite_roots == (R(1, 6),) and a.selected == ()
    assert data_of(a).intervals == ((-1, 3),)
    assert data_of(a).rows() == ((R(1, 6), R(1, 2), 0, 1, (R(1, 6), R(2, 3))),)
    for n in range(-192, 385):
        q = R(n, 96)
        assert original_zero(q) == (q == R(1, 6))
    assert failed(a, R(1, 6)) is None
    assert failed(a, R(2, 3)) == (3 * S - 4 * S**3, "nonzero", 0)
    assert plan(c).answer == r"а) \{\frac{\pi}{6}\}; б) \varnothing"


def test_original_base_argument_and_both_original_denominators_are_preserved():
    a = analysis(CASES[0])
    base = 3 + 2 * X - X * X
    domain = conditions(a)
    assert (base, "positive") in domain and (base - 1, "nonzero") in domain
    assert a.poles == (3 * S - 4 * S**3, base - 1)
    assert any(
        relation == "positive" and expression.has(S, C)
        for expression, relation in domain
    )
    assert data_of(a).phase == R(1, 3)
    assert not a.global_radical and not a.bounded_log and not a.log_polynomial


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_registration_reuses_the_existing_trigonometric_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 10, 12)
    assert (
        p.content_rule_key == "exam-trigonometric-polynomial-circle"
        and g["task_count"] == 1
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_keeps_conditions_and_no_diagrams(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 999</p>"
    p = plan(c, ctx)
    assert (
        p == plan(c)
        and p.condition_html
        == section(before["normalized_content"], "condition")["html"]
    )
    for change in p.transformations:
        assert change["transformation_target_id"].startswith("section:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == change["transformation_target_id"]
        ).update(change["value"])
    assert plan(c, ctx).transformations == () and c["context"] == before
    assert (
        ctx["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
        == []
    )
    assert "<img" not in p.solution_html
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )


def test_parent_reciprocal_amplitude_product_and_finite_selection_stay_in_order():
    html = plan(CASES[0]).solution_html
    f = forms(html)
    domain = f.index("-1<x<3")
    reciprocal = f.index(r"\frac{1}{\log_a b}=\log_b a")
    product = next(i for i, s in enumerate(f) if s.startswith(r"2\sin\left("))
    indices = f.index(r"k\in\{0;1\}")
    rejected = f.index(r"\sin(3x)=0")
    assert domain < reciprocal < product < indices < rejected
    assert not any(s.startswith(("t=", "y=", r"\tg")) for s in f)
    soup = BeautifulSoup(html, "html.parser")
    second = soup.find_all("li")[1]
    assert r"k\in" not in str(second) and r"\frac{\pi}{6}&lt;\frac{\pi}{2}" in str(
        second
    )
    assert "Ни один корень" in second.get_text()


def test_wide_selection_interval_cannot_leak_any_periodic_translate():
    a = analysis(
        CASES[0],
        bounds=(-10 * sp.pi, 10 * sp.pi, True, True),
        interval=r"[-10\pi;10\pi]",
    )
    assert a.finite_roots == a.selected == (R(1, 6),)
    answer, _, html = render(a, "")
    assert answer.count(r"\frac{\pi}{6}") == 2
    assert r"\mid k" not in answer and r"\mathbb" not in answer
    second = BeautifulSoup(html, "html.parser").find_all("li")[1]
    assert r"k\in" not in str(second)


def test_shifted_domain_keeps_later_translates_even_if_every_canonical_residue_fails():
    a = analysis(
        CASES[0],
        equation("-x^2+16x-60"),
        bounds=(0, 10 * sp.pi, True, True),
        interval=r"[0;10\pi]",
    )
    assert data_of(a).intervals == ((6, 10),)
    assert a.finite_roots == a.selected == (R(13, 6), R(19, 6))
    assert all(failed(a, q) is not None for q in (R(1, 6), R(2, 3), R(7, 6), R(5, 3)))
    for n in range(385):
        q = R(n, 96)
        assert original_zero(q, (-1, 16, -60)) == (q in a.finite_roots)
    html = first(a)[1]
    assert "6<x<10" in forms(html) and r"k\in\{4;5;6\}" in forms(html)


def test_negative_index_windows_are_not_replaced_by_the_parent_index_values():
    a = analysis(
        CASES[0],
        equation("-x^2-12x-32"),
        bounds=(-10 * sp.pi, 0, True, True),
        interval=r"[-10\pi;0]",
    )
    assert a.finite_roots == a.selected == (-R(11, 6),)
    assert original_zero(-R(11, 6), (-1, -12, -32))
    assert data_of(a).intervals == ((-8, -4),)
    first(a)


def test_open_base_domain_endpoint_is_not_restored_after_cancellation():
    a = analysis(CASES[0], equation("4x-x^2", r"2\sin x"))
    assert data_of(a).phase == 0 and data_of(a).intervals == ((0, 4),)
    assert a.finite_roots == (R(1, 4), R(3, 4), R(5, 4)) and a.selected == (
        R(3, 4),
        R(5, 4),
    )
    assert 0 not in a.finite_roots and not original_zero(sp.S.Zero, (-1, 4, 0), (2, 0))
    for q in a.finite_roots:
        assert original_zero(q, (-1, 4, 0), (2, 0))
    first(a)


def test_amplitude_phase_changes_both_candidate_families_from_condition_values():
    a = analysis(CASES[0], equation("3+2x-x^2", r"\sqrt{3}\sin x+\cos x"))
    assert data_of(a).phase == R(1, 6)
    assert a.finite_roots == (
        -R(7, 24),
        R(1, 12),
        R(5, 24),
        R(17, 24),
    ) and a.selected == (R(17, 24),)
    for n in range(-96, 193):
        q = R(n, 96)
        assert original_zero(q, weights=(sp.sqrt(3), 1)) == (q in a.finite_roots)
    first(a)


def test_fixed_reciprocal_base_below_one_keeps_the_same_original_domain():
    a = analysis(
        CASES[0],
        equation(
            "3+2x-x^2", r"\frac{1}{4}\sin x+\frac{\sqrt{3}}{4}\cos x", r"\frac{1}{2}"
        ),
    )
    assert a.finite_roots == (R(1, 6),) and a.selected == ()
    assert original_zero(R(1, 6), weights=(R(1, 4), sp.sqrt(3) / 4), fixed=R(1, 2))
    first(a)


@pytest.mark.parametrize(
    "formula",
    [
        equation("3+2x+x^2"),
        equation("3+2x-x^4"),
        equation("3+2x-x^2+\\sin x"),
        equation(r"1000-\frac{x^2}{100}"),
        equation("3+2x-x^2", r"\sin x+\cos x"),
        equation("3+2x-x^2", r"\sqrt{2}\sin x+\sqrt{2}\cos x"),
        equation("3+2x-x^2", denominator=r"\sin 2x"),
        equation("3+2x-x^2", denominator=r"\sin(3x+\frac{\pi}{6})"),
        equation("3+2x-x^2", fixed="1"),
        equation("3+2x-x^2", fixed="-2"),
        equation("3+2x-x^2")
        .replace(r"\sin x", r"\sin\beta")
        .replace(r"\cos x", r"\cos\beta")
        .replace(r"\sin 3x", r"\sin 3\beta"),
        equation("3+2x-x^2").replace(r"\sin 3x", r"\sin 3x\cos x"),
    ],
)
def test_unsupported_bases_domains_phases_angles_and_extra_poles_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analysis(CASES[0], formula)


def test_default_variable_log_parser_still_rejects_a_physical_scalar_x():
    with pytest.raises(UnsupportedCondition):
        Parser(r"\log_{(3+2\alpha-\alpha^2)}(\sin\alpha)", {}, [], []).parse()


@pytest.mark.parametrize(
    "extra",
    [
        "<p>Другое решение</p>",
        '<img src="/assets/unknown"/>',
        '<p><span data-inline-latex="t=\\sin x"></span></p>',
    ],
)
def test_unknown_extra_parent_methods_diagrams_and_substitutions_cannot_be_dropped(
    extra,
):
    with pytest.raises(UnsupportedCondition):
        plan(CASES[0], prototype=parent(CASES[0]) + extra)
