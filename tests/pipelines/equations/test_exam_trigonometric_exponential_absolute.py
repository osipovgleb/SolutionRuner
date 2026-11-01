"""Both closed exponent sign cases retain their own roots and positive powers."""

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
from solution_runner.pipelines.equations.exam_input import read
from solution_runner.pipelines.equations.exam_power_terms import read as power_terms
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_exponential_absolute import (
    E,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import first
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_exponential_absolute.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, i, b, parent(c))


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


def original_zero(q, *, a=2024, b=-1, rhs=2023, base=3):
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        s, c = mp.sin(x), mp.cos(x)
        radicand = 1 - c * c
        assert radicand >= -mp.mpf("1e-60")
        value = (
            a * mp.power(base, mp.sqrt(max(0, radicand))) + b * mp.power(base, s) - rhs
        )
        return abs(value) < mp.mpf("1e-45")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_match_original_equation_in_both_closed_cases(c):
    a = analysis(c)
    assert a.series == ((0, 1),) and a.selected == (2, 3)
    assert select(a.series, (0, 2, True, False))[0] == (0, 1)
    for q in (sp.Integer(0), sp.Integer(1), sp.Integer(2), sp.Integer(3)):
        assert original_zero(q)
    for n in range(192):
        q = R(n, 96)
        assert original_zero(q) == (q in (0, 1))


def test_both_case_certificates_keep_the_shared_zero_and_impossible_negative_power():
    d = analysis(CASES[0]).exponential_absolute
    assert d.base == 3 and d.variable == S and d.radicand == 1 - C * C
    assert d.coefficients == (2024, -1, -2023) and d.accepted == (0,)
    positive, negative = d.cases
    assert positive.sign == 1 and positive.polynomial == 2023 * E - 2023
    assert positive.powers == (1,) and positive.levels == positive.accepted == (0,)
    assert negative.sign == -1 and negative.polynomial == E * E + 2023 * E - 2024
    assert negative.powers == (1, -2024) and negative.levels == (0, None)
    assert negative.accepted == (0,)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_registration_reuses_the_trigonometric_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 12, 7)
    assert (
        p.content_rule_key == "exam-trigonometric-polynomial-circle"
        and g["task_count"] == 1
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_original_conditions_and_no_assets(
    c,
):
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
    for t in p.transformations:
        assert t["transformation_target_id"].startswith("section:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(c, ctx).transformations == () and c["context"] == before
    assert (
        ctx["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
        == []
    )
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )
    assert (
        "<img" not in p.solution_html and analysis(c).selection_method == "inequalities"
    )


def test_proof_keeps_square_identity_then_both_cases_then_union_and_inequality_selection():
    html = plan(CASES[0]).solution_html
    f = forms(html)
    identity = next(i for i, s in enumerate(f) if s.startswith(r"\sqrt{"))
    positive = f.index(r"(\sin x)\ge0")
    negative = f.index(r"(\sin x)\le0")
    rejected = f.index(r"3^{(\sin x)}=-2024")
    assert identity < positive < negative < rejected
    assert f.count(r"x=\pi k,\quad k\in\mathbb Z") == 3
    assert "на границе учитываем один раз" in html
    assert any(r"\le" in s and "k" in s for s in f[rejected:])
    assert not any(s.startswith(("t=", "y=")) for s in f)
    assert "<p>Если <center>" not in html


def test_changed_coefficients_produce_distinct_nonzero_roots_in_each_sign_case():
    a = analysis(CASES[0], r"7\cdot4^{\sqrt{1-\cos^2x}}-4\cdot4^{\sin x}=12")
    assert a.exponential_absolute.cases[0].accepted == (1,)
    assert a.exponential_absolute.cases[1].accepted == (-R(1, 2),)
    full = (R(1, 2), R(7, 6), R(11, 6))
    assert select(a.series, (0, 2, True, False))[0] == full
    for n in range(192):
        q = R(n, 96)
        assert original_zero(q, a=7, b=-4, rhs=12, base=4) == (q in full)
    first(a)


def test_positive_power_candidate_in_wrong_negative_case_is_rejected():
    a = analysis(CASES[0], r"2\cdot4^{\sqrt{1-\cos^2x}}+4^{\sin x}=3")
    negative = a.exponential_absolute.cases[1]
    assert dict(zip(negative.powers, negative.levels, strict=True)) == {
        1: 0,
        2: R(1, 2),
    }
    assert negative.accepted == (0,) and a.series == ((0, 1),)
    assert "не удовлетворяет условию рассматриваемого случая" in first(a)[1]


def test_exact_log_level_outside_unit_interval_is_rejected_before_trig_back_substitution():
    a = analysis(CASES[0], r"7\cdot2^{\sqrt{1-\cos^2x}}-4\cdot2^{\sin x}=12")
    positive, negative = a.exponential_absolute.cases
    assert positive.levels == (2,) and positive.accepted == ()
    assert negative.accepted == (-1,)
    assert select(a.series, (0, 2, True, False))[0] == (R(3, 2),)
    assert "не входит в отрезок от −1 до 1" in first(a)[1]


def test_cosine_square_identity_uses_the_same_certificate_and_keeps_closed_interval_endpoints():
    c = CASES[0]
    _, _, interval, bounds = read(c["context"])
    prototype = (
        parent(c)
        .replace(r"\sin", "TEMP")
        .replace(r"\cos", r"\sin")
        .replace("TEMP", r"\cos")
    )
    a = analyze(
        r"2024\cdot3^{\sqrt{1-\sin^2x}}-3^{\cos x}=2023", interval, bounds, prototype
    )
    assert a.exponential_absolute.variable == C
    assert a.series == ((R(1, 2), 1),) and a.selected == (R(3, 2), R(5, 2), R(7, 2))
    assert select(a.series, (0, 2, True, False))[0] == (R(1, 2), R(3, 2))
    first(a)


@pytest.mark.parametrize(
    "formula",
    [
        r"2024\cdot3^{\sqrt{1-\cos^2x}}-2^{\sin x}=2023",
        r"2024\cdot3^{\sqrt{1+\cos^2x}}-3^{\sin x}=2023",
        r"2024\cdot3^{\sqrt{1-\cos^2x}}-3^{\cos x}=2023",
        r"2024\cdot3^{\sqrt{1-\cos^2(2x)}}-3^{\sin(2x)}=2023",
        r"2024\cdot3^{\sqrt{1-\cos^2x}+1}-3^{\sin x}=2023",
        r"2024\cdot3^{\sqrt{1-\cos^2x}}-3^{\sin x}+3^{\cos x}=2023",
        r"2024\cdot3^{\sqrt{1-\cos^2x}}-3^{\frac{\sin x}{\cos x}}=2023",
        r"3^{\sqrt{1-\cos^2x}}-3^{\sin x}=0",
        r"3^{\sqrt{1-\cos^2x}}+3^{\sin x}=-1",
    ],
)
def test_unreviewed_roots_poles_angles_bases_and_degenerate_cases_are_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        analysis(CASES[0], formula)


@pytest.mark.parametrize(
    "old,new",
    [
        (r"\sin x\ge 0", r"\sin x>0"),
        (r"\sin x\le 0", r"\sin x<0"),
        ("два слу\xadчая", "один случай"),
    ],
)
def test_parent_must_retain_both_closed_cases(old, new):
    c = CASES[0]
    changed = parent(c).replace(old, new)
    assert changed != parent(c)
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=changed)


def test_unknown_extra_parent_method_cannot_be_omitted():
    with pytest.raises(UnsupportedCondition):
        plan(CASES[0], prototype=parent(CASES[0]) + "<p>Другое решение</p>")


def test_shared_exponential_reader_default_still_requires_polynomial_x_exponents():
    terms, constant = power_terms(r"9^{2x}-3\cdot3^{x}=2")
    assert len(terms) == 2 and constant == -2
    with pytest.raises(UnsupportedCondition):
        power_terms(r"9^{\sin x}-3\cdot3^{\sin x}=2")
