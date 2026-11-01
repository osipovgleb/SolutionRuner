"""Outer-root log products keep original domains and both reviewed parent methods."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_input import endpoint
from solution_runner.pipelines.equations.exam_logarithmic_branches import (
    allowed,
    analyze,
)
from solution_runner.pipelines.equations.exam_logarithmic_reference import read
from solution_runner.pipelines.equations.exam_scalar import compare
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_logarithmic_radical_products.json"
    ).read_text()
)
CASES = DATA["cases"]
C = CASES[0]
FORMULA = r"(\sqrt{x^{2}+2x-7}-1)\cdot \log_3 (9+2x-x^{2})=0"


def parent():
    return section(C["context"]["normalized_content"], "solution")["html"]


def analysis(formula=FORMULA, interval="[0;5]", bounds=(0, 5, True, True)):
    return analyze(
        formula,
        interval,
        tuple(sp.sympify(v) if type(v) is int else v for v in bounds),
        parent(),
    )


def plan(context=None, prototype=None):
    return get_handler(get_group_profile("624920").content_rule_key).plan(
        PlanInput(
            context or C["context"],
            parent_solution_html=parent() if prototype is None else prototype,
        )
    )


def test_exact_registration_reuses_existing_logarithm_branch_handler():
    p = get_group_profile("624920")
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (DATA["groups"][0]["uuid"], DATA["groups"][0]["theme_uuid"], 12, 3)
    assert p.content_rule_key == "exam-logarithmic-branches"


def test_original_roots_and_domain_are_independent_of_the_saved_answer():
    _, f, i, b = read(C["context"])
    a = analyze(f, i, b, parent())
    assert a.selection.roots == (2, 4) and a.selection.selected == (2,)
    assert tuple(v.candidates for v in a.branches) == ((-4, 2), (-2, 4))
    assert a.radical_product.domain == sp.Interval.Ropen(
        2 * sp.sqrt(2) - 1, 1 + sp.sqrt(10)
    )
    for v in (-4, -2, 2, 4):
        assert allowed(v, a.constraints) == (v in (2, 4))
    for v in a.selection.roots:
        expression = (
            (sp.sqrt(v * v + 2 * v - 7) - 1) * sp.log(9 + 2 * v - v * v) / sp.log(3)
        )
        assert sp.simplify(expression) == 0
    # Exhaust all real half-integers in a wider interval against the original factors.
    for v in (sp.Rational(n, 2) for n in range(-12, 13)):
        valid = v * v + 2 * v - 7 >= 0 and 9 + 2 * v - v * v > 0
        zero = valid and (v * v + 2 * v - 7 == 1 or 9 + 2 * v - v * v == 1)
        assert bool(zero) == (v in a.selection.roots)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_original_inputs(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    section(ctx["normalized_content"], "answer")["html"] = "<p>UNUSED 999</p>"
    section(ctx["normalized_content"], "solution")["html"] = "<p>UNUSED 999</p>"
    p = plan(ctx)
    assert p == plan() and c["context"] == before
    for t in p.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(ctx).transformations == ()
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    assert (
        ctx["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
        == []
    )


def test_both_parent_methods_and_the_note_position_are_preserved():
    html = plan().solution_html
    assert (
        html.index("Первый множитель")
        < html.index("Второй множитель")
        < html.index("Отберём корни")
        < html.index("Примечание")
    )
    soup = BeautifulSoup(html, "html.parser")
    assert "Примечание" not in soup.select_one('[data-list-marker="а)"]').get_text()
    assert "Примечание" in soup.select_one('[data-list-marker="б)"]').get_text()
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    assert any(r"\sqrt{" in f and "=1" in f for f in formulas)
    assert any(r"\ge0" in f and ">0" in f for f in formulas)
    assert any("sqrt" in f and r"\right)" in f and r"\left[" in f for f in formulas)
    assert "1<" + sp.latex(sp.sqrt(2)) in formulas
    assert "2>" + sp.latex(sp.sqrt(2)) in formulas
    assert not "<img" in html


@pytest.mark.parametrize(
    "formula,expected",
    [
        (r"(\sqrt{x^2-4}-0)\log_3(x+3)=0", (-2, 2)),
        (r"(\sqrt{x^2-4}-2)\log_3(x+3)=0", (-2 * sp.sqrt(2), -2, 2 * sp.sqrt(2))),
        (r"3\log_{(\frac{1}{2})}(x+3)\cdot(\sqrt{x^2-4}-0)=0", (-2, 2)),
        (r"(\sqrt{x^2}-1)\log_5(x+2)=0", (-1, 1)),
    ],
)
def test_changed_coefficients_bases_and_zero_radicand_are_computed(formula, expected):
    a = analysis(formula, "[-3;3]", (-3, 3, True, True))
    assert a.selection.roots == expected and a.selection.selected == expected
    for v in expected:
        assert allowed(v, a.constraints)


@pytest.mark.parametrize(
    "lc,uc,selected",
    [
        (True, True, (2, 4)),
        (False, True, (4,)),
        (True, False, (2,)),
        (False, False, ()),
    ],
)
def test_exact_open_and_closed_root_endpoints(lc, uc, selected):
    a = analysis(bounds=(2, 4, lc, uc))
    assert a.selection.selected == selected


@pytest.mark.parametrize(
    "formula",
    [
        r"(\sqrt{x^2+2x-7}-1)\log_3(9+2x-x^2)=1",
        r"(\sqrt{x^2+2x-7}+1)\log_3(9+2x-x^2)=0",
        r"(\sqrt{x^2+2x-7}-x)\log_3(9+2x-x^2)=0",
        r"(\sqrt{x^2+2x-7}-21)\log_3(9+2x-x^2)=0",
        r"(\sqrt{x^2+2x-7}-1/13)\log_3(9+2x-x^2)=0",
        r"(\sqrt{x^3+2x-7}-1)\log_3(9+2x-x^2)=0",
        r"(\sqrt{x^2+2x-7}-1)\log_3(x^3+x+1)=0",
        r"(\sqrt{x^2+2x-7}-1)\log_x(9+2x-x^2)=0",
        r"(\sqrt{x^2+2x-7}-1)\log_1(9+2x-x^2)=0",
        r"(\sqrt{x^2+2x-7}-1)\log_0(9+2x-x^2)=0",
        r"(\sqrt{x^2+2x-7}-1)\log_3(9+2x-x^2)^2=0",
        r"(\sqrt{x^2+2x-7}-1)/\log_3(9+2x-x^2)=0",
        r"(\sqrt{x^2+2x-7}-1)\log_3\sqrt{9+2x-x^2}=0",
        r"(\sqrt{x^2+2x-7}-1)\log_3(9+2x-x^2)\log_2(x)=0",
        r"(\sqrt{x^2+2x-7}-\sqrt{x+1})\log_3(9+2x-x^2)=0",
        r"(\sqrt{\sqrt{x+2}}-1)\log_3(x+3)=0",
        r"(\sqrt{x^2/x}-1)\log_3(x+3)=0",
        r"(\sqrt{x^2+2x-7}-1)\log_3(9+2x-x^2)+x=0",
        r"(\sqrt{x^2+2x-7}-1)(\log_3(9+2x-x^2)+1)=0",
        r"(\sqrt{x^2+2x-7}-1)\log_3(9+2x-x^2)/(x/x)=0",
    ],
)
def test_unreviewed_operands_and_original_poles_are_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        analysis(formula)


@pytest.mark.parametrize(
    "mutation", ["empty", "note", "extra", "assets", "instruction"]
)
def test_unknown_methods_missing_note_assets_and_instruction_fail_closed(mutation):
    ctx = deepcopy(C["context"])
    prototype = parent()
    if mutation == "empty":
        prototype = ""
    if mutation == "note":
        prototype = prototype.replace("При\xadме\xadча\xadние", "Объяснение")
    if mutation == "extra":
        prototype += "<p>Другое решение.</p>"
    if mutation == "assets":
        ctx["normalized_content"]["assets"].append({"asset_key": "unknown"})
    if mutation == "instruction":
        sec = section(ctx["normalized_content"], "condition")
        sec["html"] = sec["html"].replace("Ре\xadши\xadте", "Приближённо решите")
    with pytest.raises(UnsupportedCondition):
        plan(ctx, prototype)


@pytest.mark.parametrize(
    "a,b,result",
    [
        (2, 2 ** sp.sqrt(2), -1),
        (2 ** sp.sqrt(2), 4, -1),
        (2 ** sp.sqrt(2), 2, 1),
        (4, 2 ** sp.sqrt(2), 1),
        (-(2 ** sp.sqrt(2)), -2, -1),
        (-4, -(2 ** sp.sqrt(2)), -1),
        (-(2 ** sp.sqrt(2)), 0, -1),
        (0, 2 ** sp.sqrt(2), -1),
        (2 ** (-sp.sqrt(2)), sp.Rational(1, 2), -1),
        (2 ** sp.sqrt(2), 2 ** sp.sqrt(2), 0),
        (sp.log(5) / sp.log(3), 2 ** sp.sqrt(2), -1),
    ],
)
def test_irrational_power_comparisons_are_exact_and_certified(a, b, result):
    assert compare(a, b) == result


@pytest.mark.parametrize(
    "value",
    [
        2 ** (1 + sp.sqrt(2)),
        2**sp.pi,
        2 ** sp.sqrt(401),
        1001 ** sp.sqrt(2),
    ],
)
def test_unreviewed_power_scalars_do_not_gain_approximate_fallback(value):
    with pytest.raises(UnsupportedCondition):
        compare(value, sp.Integer(2))


def test_whole_original_endpoint_is_read_and_no_unknown_suffix_is_dropped():
    value = endpoint(r"2^{\sqrt{2}}")
    assert value == 2 ** sp.sqrt(2) and compare(value, 2) > 0 and compare(value, 4) < 0
    with pytest.raises(UnsupportedCondition):
        endpoint(r"2^{\sqrt{2}}+y")
