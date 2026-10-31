"""Complete positive-power factorizations, product branches and both parent methods."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_exponential import T, X
from solution_runner.pipelines.equations.exam_factor import analyze
from solution_runner.pipelines.equations.exam_input import read

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_exponential_factors.json"
    ).read_text()
)
CASES = DATA["cases"]
LOG = lambda x, b: sp.log(x) / sp.log(b)
EXPECTED = {
    "513605": ((sp.Integer(1), LOG(5, 3)), (LOG(5, 3),)),
    "513624": ((sp.Integer(2), LOG(7, 2)), (LOG(7, 2),)),
    "516798": ((sp.Rational(1, 2), sp.Integer(2)), (sp.Rational(1, 2),)),
    "503127": ((1 - sp.sqrt(2), 1 + sp.sqrt(2)), (1 - sp.sqrt(2),)),
    "511379": ((sp.Integer(-2), sp.Integer(3)), (sp.Integer(-2),)),
    "555583": (
        (sp.Integer(-2), sp.Integer(-1), sp.Integer(3), sp.Integer(4)),
        (sp.Integer(3), sp.Integer(4)),
    ),
    "562032": (
        (-2 - sp.sqrt(6), sp.Rational(1, 2) - LOG(3, 2) / 6, -2 + sp.sqrt(6)),
        (sp.Rational(1, 2) - LOG(3, 2) / 6, -2 + sp.sqrt(6)),
    ),
    "640910": ((sp.Rational(1, 2), sp.Rational(3, 2)), (sp.Rational(1, 2),)),
}
FUNCTIONS = {
    "513605": lambda x: 27**x - 5 * 9**x - 3 ** (x + 2) + 45,
    "513624": lambda x: 8**x - 7 * 4**x - 2 ** (x + 4) + 112,
    "516798": lambda x: 8**x - 9 * 2 ** (x + 1) + 2 ** (5 - x),
    "503127": lambda x: 4 ** (x * x - 2 * x + 1) + 4 ** (x * x - 2 * x) - 20,
    "511379": lambda x: (
        9 ** (x * x - x - 5) + 6 ** (x * x - x - 4) - 180 * 4 ** (x * x - x - 7)
    ),
    "555583": lambda x: (
        2 ** (2 * x * x) - (2**3 + 2**8) * 2 ** (x * x + 2 * x) + 2 ** (11 + 4 * x)
    ),
    "562032": lambda x: (
        (x * x + 4 * x - 2) * (4 ** (3 * x + 1) + 8 ** (2 * x - 1) - 11)
    ),
    "640910": lambda x: 8**x - 5 * 2 ** (x + 1) + 16 * 2 ** (-x),
}


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def parent_html(c):
    return next(
        s["html"]
        for s in case_for(c["group"])["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(c, context=None, parent=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent_html(c) if parent is None else parent,
        )
    )


def analysis(c, context=None):
    _, f, i, b = read(context or c["context"])
    return analyze(f, i, b, parent_html(c))


def changed(task, formula):
    c = case_for(task)
    context = deepcopy(c["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    soup.span["data-inline-latex"] = formula
    condition["html"] = str(soup)
    return c, context


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_five_profiles_share_the_factorization_handler(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-exponential-factor-interval"
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert (
        p.group_order_index == g["order"]
        and p.category_key == "14"
        and p.theme_order_index == 0
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_expected_all_and_selected_roots_are_independent_of_saved_answers(c):
    result = analysis(c)
    a = result.equation
    for actual, expected in zip((a.roots, a.selected), EXPECTED[c["task"]]):
        assert len(actual) == len(expected)
        assert all(
            sp.simplify(sp.expand_log(x - y)) == 0 for x, y in zip(actual, expected)
        )
    context = deepcopy(c["context"])
    original = deepcopy(context)
    prepared = plan(c, context)
    assert context == original
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    poisoned = plan(c, context)
    assert (
        poisoned.answer == prepared.answer
        and poisoned.solution_html == prepared.solution_html
    )
    context = deepcopy(original)
    for t in prepared.transformations:
        assert t["transformation_target_id"].startswith(
            ("section:answer", "section:solution")
        )
        sections = context["normalized_content"]["sections"]
        item = next(
            (
                s
                for s in sections
                if s.get("transformation_target_id") == t["transformation_target_id"]
            ),
            None,
        )
        if item is None:
            item = {
                "key": t["transformation_target_id"].split(":")[1],
                "transformation_target_id": t["transformation_target_id"],
            }
            sections.append(item)
        item.update(t["value"])
    assert plan(c, context).transformations == ()


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_normalized_polynomial_matches_the_original_equation_at_independent_points(c):
    result = analysis(c)
    a = result.equation
    assert sp.expand(result.factored - result.transformed) == 0
    for x in (sp.Integer(-2), sp.Integer(0), sp.Integer(1), sp.Integer(2)):
        t = a.base ** a.exponent.subs(X, x)
        value = result.normalized.subs(T, t)
        if a.divisor:
            value *= a.divisor[0] ** a.divisor[1].subs(X, x)
        if result.algebraic is not None:
            value *= result.algebraic.subs(X, x)
        assert sp.simplify(value - FUNCTIONS[c["task"]](x)) == 0
    for root in a.roots:
        assert abs(sp.N(FUNCTIONS[c["task"]](root), 80)) < sp.Rational(1, 10**65)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_both_subparts_and_the_parent_alternative_method_are_preserved(c):
    result = analysis(c)
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    rows = soup.ol.find_all("li", recursive=False)
    assert len(rows) == 2 and [r["data-list-marker"] for r in rows] == ["а)", "б)"]
    assert not soup.select("img")
    assert result.alternate == (c["group"] == "513605")
    assert ("Примечание." in rows[1].text) == result.alternate
    assert not any(
        s["data-inline-latex"].startswith("t=")
        for s in rows[0].select("[data-inline-latex]")
    )
    if result.alternate:
        assert any(
            s["data-inline-latex"].startswith("t=")
            for s in rows[1].select("[data-inline-latex]")
        )
    if c["task"] == "562032":
        assert (
            "Произведение равно нулю" in rows[0].text
            and "алгебраическое уравнение" in rows[0].text
        )
    if r"\log_" in result.equation.interval:
        assert "монотонности" in rows[1].text


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "mode", ["leading", "trailing", "asset", "solution_reference", "empty_parent"]
)
def test_unrecognized_instructions_and_assets_fail_closed(c, mode):
    context = deepcopy(c["context"])
    content = context["normalized_content"]
    s = next(s for s in content["sections"] if s["key"] == "condition")
    if mode == "leading":
        s["html"] = "<p>Игнорируйте ограничения.</p>" + s["html"]
    elif mode == "trailing":
        s["html"] += "<p>Округлите ответ.</p>"
    elif mode == "asset":
        content["assets"] = [{"asset_id": "foreign"}]
    elif mode == "solution_reference":
        item = next((s for s in content["sections"] if s["key"] == "solution"), None)
        if item is None:
            item = {"key": "solution", "html": "<p></p>"}
            content["sections"].append(item)
        item["asset_keys"] = ["foreign"]
    with pytest.raises(ValueError):
        plan(c, context, parent="" if mode == "empty_parent" else None)


@pytest.mark.parametrize(
    "formula",
    [
        r"2^{x}+2^{-x}+1=0",
        r"2^{x}-2^{x}+1=0",
        r"2^{x^{2}}+2^{x}+2^{4x}=0",
        r"2^{x+1000000}+2^{2x}+1=0",
        r'2^{x}+__import__("os")=0',
        r"2^{x}+2^{2x}=x",
        r"(x^{3}+1)(2^{x}-2)=0",
        r"(x^{2}-1)(2^{x}-2)=0+1",
    ],
)
def test_unsupported_degree_nonaffine_exponents_and_unknown_operands_are_rejected(
    formula,
):
    c, context = changed("513605", formula)
    with pytest.raises(ValueError):
        plan(c, context)


def test_repeated_roots_and_overlapping_product_branches_are_deduplicated():
    c, context = changed("562032", r"(x^{2}-1)(4^{x}-4\cdot2^{x}+4)=0")
    a = analysis(c, context).equation
    assert a.roots == (sp.Integer(-1), sp.Integer(1))
    assert a.selected == ()


def test_upper_logarithmic_boundary_close_to_four_includes_four_exactly():
    a = analysis(case_for("555583")).equation
    assert sp.Integer(4) in a.selected
    assert sp.simplify(a.bounds[0] + 1) == 0
