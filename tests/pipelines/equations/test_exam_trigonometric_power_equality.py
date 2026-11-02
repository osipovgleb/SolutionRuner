"""Check complete original powers, independent exponent directions and replay."""

import hashlib
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
from solution_runner.pipelines.equations import (
    verified_expression_repair as source_repair,
)
from solution_runner.pipelines.equations.exam_input import read_parts
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import read
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_power_equality import (
    compile_equality,
    reviewed,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import first
from solution_runner.pipelines.equations.verified_expression_repair import (
    repair_verified_condition,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_power_equality.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None):
    fixed, _ = repair_verified_condition(c["context"], validate=read_parts)
    _, f, i, b = read(fixed)
    return analyze(formula or f, i, b, parent(c))


def plan(c, context=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=prototype or parent(c))
    )


def forms(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_zero(task, q):
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        if task == "505565":
            value = mp.power(3, mp.cos(x)) / mp.power(9, mp.cos(x) ** 2) - mp.power(
                4, 2 * mp.cos(x) ** 2 - mp.cos(x)
            )
        else:
            value = mp.power(7, -mp.cos(mp.pi + x)) * mp.power(
                14, mp.sin(mp.pi - x)
            ) - mp.power(2, mp.cos(mp.pi / 2 - x))
        return abs(value) < mp.mpf("1e-48")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_powers_full_roots_and_selected_roots_are_independently_verified(c):
    a = analysis(c)
    expected = (
        (R(1, 3), R(1, 2), R(3, 2), R(5, 3))
        if c["task"] == "505565"
        else (R(3, 4), R(7, 4))
    )
    selected = (-R(3, 2), -R(1, 2), -R(1, 3)) if c["task"] == "505565" else (R(7, 4),)
    assert select(a.series, (0, 2, True, False))[0] == expected
    assert a.selected == selected and a.selection_method == "inequalities"
    for n in range(-192, 193):
        q = R(n, 48)
        assert original_zero(c["task"], q) == (q % 2 in expected)
    assert all(original_zero(c["task"], q) for q in selected)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_replay_empty_and_original_assets_untouched(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 999</p>"
    p = plan(c, ctx)
    assert p == plan(c)
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
    assert "<img" not in p.solution_html
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )


def test_source_restoration_is_visible_exact_and_answer_independent():
    c = CASES[1]
    before = section(c["context"]["normalized_content"], "condition")["html"]
    p = plan(c)
    assert p.condition_html != before
    assert r"7^{-\cos" in p.condition_html
    assert any(
        t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    records = json.loads(
        Path(source_repair.__file__)
        .with_name("verified_expression_transcriptions.json")
        .read_text()
    )["entries"]
    entry = next(
        e
        for e in records
        if e["condition_sha256"] == hashlib.sha256(before.encode()).hexdigest()
    )
    assert entry["before_html"] == before and entry["after_html"] == p.condition_html
    assert len(entry["source_images"]) == 2 and entry["source_url"].endswith(
        "id=646481"
    )
    changed = deepcopy(c["context"])
    section(changed["normalized_content"], "condition")["html"] = before.replace(
        "14", "15"
    )
    assert repair_verified_condition(changed, validate=read_parts) == (changed, None)
    with pytest.raises(UnsupportedCondition):
        plan(c, changed)


@pytest.mark.parametrize(
    "extra", [" ", "<p>Удвойте ответ.</p>", "<script>changeAnswer()</script>"]
)
def test_source_restoration_rejects_any_augmented_condition(extra):
    ctx = deepcopy(CASES[1]["context"])
    section(ctx["normalized_content"], "condition")["html"] += extra
    prepared, change = repair_verified_condition(ctx, validate=read_parts)
    assert prepared is ctx and change is None


def test_ratio_to_one_method_keeps_original_cosine_factor_without_a_substitution():
    a = analysis(CASES[0])
    assert a.power_equality.base == R(1, 12) and a.raw == 2 * C * C - C
    html = "".join(first(a))
    f = forms(html)
    power = next(i for i, v in enumerate(f) if r"\frac{1}{12}" in v and "^{" in v)
    factor = next(
        i for i, v in enumerate(f) if r"(\cos x)" in v and r"2 (\cos x) - 1" in v
    )
    assert power < factor and "D=" not in html
    assert not any(v.startswith(("t=", "y=")) for v in f)
    assert 0 in a.branches[0].values


def test_positive_factor_cancellation_precedes_tangent_and_inequality_selection():
    p = plan(CASES[1])
    f = forms(p.solution_html)
    positive = next(
        i for i, v in enumerate(f) if r"\left(2\right)" in v and v.endswith(">0")
    )
    target = next(
        i for i, v in enumerate(f) if r"\left(7\right)" in v and v.endswith("=1")
    )
    tangent = next(i for i, v in enumerate(f) if r"\tg" in v and "=0" in v)
    selection = next(i for i, v in enumerate(f) if "k" in v and v.count(r"\le") == 2)
    assert positive < target < tangent < selection
    assert any(r"(\cos x)\ne0" in v for v in f[target:tangent])


@pytest.mark.parametrize(
    "formula,raw",
    [
        (r"2^{\sin x}=3^{\sin x}", S),
        (r"15^{\cos x}=3^{\cos x}\cdot5^{\sin x}", C - S),
        (r"(49^{\cos x})^{\sin x}=7^{\sqrt{2}\cos x}", 2 * C * S - sp.sqrt(2) * C),
        (r"(\frac{1}{81})^{\cos x}=9^{2\sin2x}", -2 * C - 4 * C * S),
        (r"3^{\cos x}\cdot(0{,}2)^{-\sin x}=15^{\sin x}", C - S),
    ],
)
def test_exact_common_exponent_handles_products_nested_and_reciprocal_bases(
    formula, raw
):
    e = compile_equality(formula, parent(CASES[0]))
    ratio = sp.cancel(e.raw / raw)
    assert ratio.is_Rational and ratio != 0
    assert e.poles == ()


@pytest.mark.parametrize(
    "formula",
    [
        r"2^{\sin x}=3^{\cos x}",
        r"2^{\sin x}\cdot3^{\cos x}=1",
        r"2^{\sin x}=2^{\sin x}",
        r"(-2)^{\sin x}=1",
        r"0^{\sin x}=1",
        r"1^{\sin x}=1",
        r"10001^{\sin x}=1",
        r"2^{\sin x}+2^{\cos x}=1",
        r"\frac{2^{\sin x}}{\sin x}=1",
        r"\frac{2^{\sin x}}{1-\cos x}=1",
        r"2^{\tg x}=4^{\sin x}",
        r"2^{\sin x}=2^{\cos^4x}",
        r"x^{\sin x}=1",
        r"2^{\sin x}=2^{\cos\beta}",
    ],
)
def test_unreviewed_equations_fail_closed_instead_of_dropping_factors_or_poles(formula):
    with pytest.raises(UnsupportedCondition):
        compile_equality(formula, parent(CASES[0]))


@pytest.mark.parametrize(
    "formula", [r"\sin^{2}x+\cos^{2}x=1", r"(\sin x+\cos x)^{2}=1"]
)
def test_numeric_power_recognition_does_not_capture_existing_trig_polynomials(formula):
    assert not reviewed(formula)


@pytest.mark.parametrize("extra", [r"t=2^{\cos x}", r"y=\cos x", r"\log_2(\cos x)=1"])
def test_parent_with_another_substitution_or_log_method_is_rejected(extra):
    with pytest.raises(UnsupportedCondition):
        compile_equality(
            r"2^{\sin x}=3^{\sin x}",
            parent(CASES[0]) + f'<span data-inline-latex="{extra}"></span>',
        )


def test_group_profiles_share_the_existing_runner_and_original_catalog_bindings():
    for g in DATA["groups"]:
        p = get_group_profile(g["key"])
        assert p.source_group_id == g["uuid"] and p.group_order_index == g["order"]
        assert p.snapshot_theme_id == g["theme_uuid"]
        assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
