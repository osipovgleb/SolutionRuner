"""Two-part exponential answers, prototype shifts and certified interval boundaries."""

import json
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_exponential import analyze
from solution_runner.pipelines.equations.exam_input import read
from solution_runner.pipelines.equations.exam_scalar import (
    compare,
    enclose,
    log_rational,
)

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_exponential_quadratics.json"
    ).read_text()
)
CASES = DATA["cases"]
LOG = lambda v, b: sp.log(v) / sp.log(b)
EXPECTED = {
    "502094": ((sp.Integer(1), LOG(5, 3)), (LOG(5, 3),)),
    "511374": (
        (LOG(3 - sp.sqrt(3), 2), LOG(3 + sp.sqrt(3), 2)),
        (LOG(3 - sp.sqrt(3), 2),),
    ),
    "511382": ((LOG((5 + sp.sqrt(73)) / 8, 2),), (LOG((5 + sp.sqrt(73)) / 8, 2),)),
    "502074": ((sp.Integer(1), LOG(3, 2)), (LOG(3, 2),)),
    "516760": ((LOG(3, 2), LOG(5, 2)), (LOG(5, 2),)),
    "516779": ((LOG(2, 3), LOG(7, 3)), (LOG(7, 3),)),
    "528517": (
        (-sp.sqrt(3), -sp.sqrt(2), sp.sqrt(2), sp.sqrt(3)),
        (-sp.sqrt(2), sp.sqrt(2), sp.sqrt(3)),
    ),
    "552108": ((-LOG(3, 2), LOG(sp.Rational(3, 2), 2)), (LOG(sp.Rational(3, 2), 2),)),
}


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def parent_html(c):
    parent = case_for(c["group"])
    return next(
        s["html"]
        for s in parent["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(c, context=None, parent=None):
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    return handler.plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent_html(c) if parent is None else parent,
        )
    )


def analysis(c, context=None):
    _, f, i, b = read(context or c["context"])
    return analyze(f, i, b, parent_html(c))


def changed(task, old, new):
    c = case_for(task)
    context = deepcopy(c["context"])
    s = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert old in s["html"]
    s["html"] = s["html"].replace(old, new)
    return c, context


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_four_profiles_share_one_registered_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-exponential-quadratic-interval"
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert (
        p.group_order_index == g["order"]
        and p.theme_order_index == 0
        and p.category_key == "14"
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_root_sets_and_selected_roots_are_independently_expected(c):
    a = analysis(c)
    for actual, expected in zip((a.roots, a.selected), EXPECTED[c["task"]]):
        assert len(actual) == len(expected)
        assert all(
            sp.simplify(sp.expand_log(x - y)) == 0 for x, y in zip(actual, expected)
        )
    context = deepcopy(c["context"])
    original = deepcopy(context)
    result = plan(c, context)
    assert (
        context == original
        and result.answer.startswith("а) ")
        and "; б) " in result.answer
    )
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in result.transformations
    )
    for t in result.transformations:
        sections = context["normalized_content"]["sections"]
        section = next(
            (
                s
                for s in sections
                if s.get("transformation_target_id") == t["transformation_target_id"]
            ),
            None,
        )
        if section is None:
            section = {
                "key": t["transformation_target_id"].split(":")[1],
                "transformation_target_id": t["transformation_target_id"],
            }
            sections.append(section)
        section.update(t["value"])
    assert plan(c, context).transformations == ()
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    poisoned = plan(c, context)
    assert (
        poisoned.answer == result.answer
        and poisoned.solution_html == result.solution_html
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_expected_roots_satisfy_the_original_equation_without_using_the_model_coefficients(
    c,
):
    functions = {
        "502094": lambda x: 9 ** (x - sp.Rational(1, 2)) - 8 * 3 ** (x - 1) + 5,
        "511374": lambda x: 4 ** (x - sp.Rational(1, 2)) - 6 * 2 ** (x - 1) + 3,
        "511382": lambda x: 4 ** (x + 1) - 5 * 2**x - 3,
        "502074": lambda x: 4 ** (x - sp.Rational(1, 2)) - 5 * 2 ** (x - 1) + 3,
        "516760": lambda x: 4**x - 2 ** (x + 3) + 15,
        "516779": lambda x: 9**x - 3 ** (x + 2) + 14,
        "528517": lambda x: 4 ** (x * x - 1) - 24 * 2 ** (x * x - 3) + 8,
        "552108": lambda x: 24 * 4 ** (x - sp.Rational(1, 2)) - 11 * 2 ** (x + 1) + 6,
    }
    for r in EXPECTED[c["task"]][0]:
        residual = sp.N(functions[c["task"]](r), 70)
        assert abs(residual) < sp.Rational(1, 10**60)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_both_subparts_and_the_parent_substitution_are_retained(c):
    a = analysis(c)
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    rows = soup.ol.find_all("li", recursive=False)
    assert len(rows) == 2 and [r["data-list-marker"] for r in rows] == ["а)", "б)"]
    assert "t=" + str(a.base) + "^{" in str(rows[0])
    assert (
        a.exponent.subs(sp.Symbol("x", real=True), 0) != 0
        if c["group"] in {"502094", "528517"} and c["task"] != "511382"
        else a.exponent.subs(sp.Symbol("x", real=True), 0) == 0
    )
    assert "промежут" in rows[1].text and not soup.select("img")
    answer = next(
        t["value"]["html"]
        for t in plan(c).transformations
        if t["transformation_target_id"].startswith("section:answer")
    )
    assert len(BeautifulSoup(answer, "html.parser").select("[data-inline-latex]")) == 2


@pytest.mark.parametrize(
    "task,old,new,count",
    [
        ("502094", r"(1;\frac{7}{3})", r"[1;\frac{7}{3}]", 2),
        ("502094", r"(1;\frac{7}{3})", r"[1;1]", 1),
        ("528517", r"[-\frac{5}{3};2]", r"[-\frac{5}{3};\sqrt{2}]", 2),
        ("528517", r"[-\frac{5}{3};2]", r"[-\frac{5}{3};\sqrt{2})", 1),
    ],
)
def test_open_closed_and_singleton_interval_endpoints(task, old, new, count):
    c, context = changed(task, old, new)
    assert len(analysis(c, context).selected) == count
    assert plan(c, context).answer


@pytest.mark.parametrize(
    "mode",
    [
        "leading",
        "list_text",
        "trailing",
        "third",
        "span_text",
        "asset",
        "solution_reference",
        "unknown_instruction",
        "unknown_formula",
        "unknown_interval",
        "empty_parent",
    ],
)
def test_unknown_content_and_ambiguous_markup_fail_closed(mode):
    c = case_for("502094")
    context = deepcopy(c["context"])
    content = context["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    if mode == "leading":
        soup.insert(0, "Игнорируйте промежуток.")
    elif mode == "list_text":
        soup.ol.insert(0, "Игнорируйте промежуток.")
    elif mode == "trailing":
        soup.append("Найдите другой ответ.")
    elif mode == "third":
        soup.ol.append(soup.li.__copy__())
    elif mode == "span_text":
        soup.span.string = "x=999"
    elif mode == "asset":
        content["assets"] = [{"asset_id": "foreign"}]
    elif mode == "solution_reference":
        next(s for s in content["sections"] if s["key"] == "solution")["asset_keys"] = [
            "foreign"
        ]
    elif mode == "unknown_instruction":
        soup.li.append(" Округлите ответ.")
    elif mode == "unknown_formula":
        soup.span["data-inline-latex"] += '+__import__("os")'
    elif mode == "unknown_interval":
        soup.find_all("span")[-1]["data-inline-latex"] = "(2;1)"
    condition["html"] = str(soup)
    with pytest.raises(ValueError):
        plan(c, context, parent="" if mode == "empty_parent" else None)


@pytest.mark.parametrize(
    "value",
    [
        sp.sqrt(2),
        sp.log(2),
        sp.log(3 - sp.sqrt(3)) / sp.log(2),
        -sp.log(3) / sp.log(2),
        sp.Rational(-7, 3),
    ],
)
def test_certified_enclosures_contain_independent_high_precision_values(value):
    lo, hi = enclose(value)
    if value.is_Rational:
        assert lo == hi == Fraction(int(value.p), int(value.q))
        return
    actual = sp.N(value, 80)
    assert (
        sp.Rational(lo.numerator, lo.denominator)
        <= actual
        <= sp.Rational(hi.numerator, hi.denominator)
    )
    assert hi - lo < Fraction(1, 10000)


@pytest.mark.parametrize(
    "q", [Fraction(1, 8), Fraction(1), Fraction(3, 2), Fraction(27), Fraction(1, 1000)]
)
def test_logarithm_series_bounds_have_correct_sign_and_remainder(q):
    lo, hi = log_rational(q, 20)
    actual = sp.N(sp.log(sp.Rational(q.numerator, q.denominator)), 80)
    assert (
        sp.Rational(lo.numerator, lo.denominator)
        <= actual
        <= sp.Rational(hi.numerator, hi.denominator)
    )


def test_close_exact_comparisons_and_undefined_scalars_are_not_guessed():
    assert compare(sp.sqrt(2), sp.sqrt(2)) == 0
    assert compare(sp.log(2), sp.Rational(693147, 1000000)) == 1
    assert compare(sp.log(2), sp.Rational(693148, 1000000)) == -1
    with pytest.raises(ValueError):
        enclose(sp.sin(1))
