"""Exact identities and domain failures independent of saved catalogue answers."""

import re
from copy import deepcopy
from fractions import Fraction
from itertools import product

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_category_8_source_samples import CASES, plan

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser


def value(text):
    return LogarithmParser(text).parse().value


@pytest.mark.parametrize("a,b,k", tuple(product([2, 3, 5, 12], [3, 7, 10], [-2, 1, 3])))
def test_same_base_logarithms_combine_before_evaluation(a, b, k):
    argument = Fraction(a) ** k * b
    numerator = rf"\frac{{{argument.numerator}}}{{{argument.denominator}}}"
    assert value(rf"\log_{{{a}}}({numerator})-\log_{{{a}}}{b}") == k


@pytest.mark.parametrize("a,b,m,n", tuple(product([2, 3, 10], [5, 7], [1, 2], [1, 3])))
def test_cross_base_products_cancel_without_numeric_approximation(a, b, m, n):
    assert value(rf"\log_{{{a}}}{b**m}\cdot\log_{{{b}}}{a**n}") == m * n


@pytest.mark.parametrize("a,b", tuple(product([2, 3, 10], [5, 7, 12])))
def test_power_and_inverse_logarithm_relations_include_related_bases(a, b):
    assert value(rf"({a**2})^{{\log_{{{a}}}{b}}}") == b * b
    assert value(rf"({a})^{{\log_{{{a**2}}}{b * b}}}") == b
    assert value(rf"({a}^{{\log_{{{b}}}{a}}})^{{\log_{{{a}}}{b}}}") == a


@pytest.mark.parametrize("base,index", tuple(product([2, 3, 12], [2, 3, 7])))
def test_root_arguments_and_bases_have_reciprocal_exponents(base, index):
    assert value(rf"\log_{{{base}}}\sqrt[{index}]{{{base}}}") == sp.Rational(1, index)
    assert value(rf"\log_{{\sqrt[{index}]{{{base}}}}}{base}") == index


@pytest.mark.parametrize(
    "text",
    [
        r"\log_1 3",
        r"\log_{0}3",
        r"\log_{-2}4",
        r"\log_2 0",
        r"\log_2(-1)",
        r"\frac{1}{\log_2 1}",
        r"\frac{1}{\log_2 3-\log_2 3}",
        r"\log_{2}",
        r"\log_{70,8}",
        r"\log_2 0400",
        r"\log_{2}__import__(os)",
        r"\log_2 4+",
        r"\sqrt[0]{2}",
        r"\sqrt[101]{2}",
        r"2^{1001}",
    ],
)
def test_undefined_or_ambiguous_questions_fail_closed(text):
    with pytest.raises(ValueError):
        value(text)


@pytest.mark.parametrize("task", ["26855", "26858"])
def test_both_source_methods_survive_and_do_not_rewrite_on_repeat(task):
    case = next(c for c in CASES if c["task"] == task)
    result = plan(case, deepcopy(case["context"]))
    html = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert html.index("Первый способ") < html.index("Второй способ")


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in ["77415", "77416", "77417"]],
    ids=lambda c: c["task"],
)
def test_given_logarithm_is_used_symbolically_without_losing_negative_values(case):
    context = deepcopy(case["context"])
    result = plan(case, context)
    assert result.answer == plan(case, deepcopy(context)).answer
    html = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert "log_" in html and "\\ne1" in html


def test_numeric_proof_steps_do_not_expose_internal_logarithm_symbols():
    for case in CASES:
        if (
            case["group"] not in ["26854", "26855", "26858", "26860", "77418"]
            or "unsupported_reason" in case
        ):
            continue
        result = plan(case, deepcopy(case["context"]))
        html = next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"].startswith("section:solution")
        )
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
            assert not re.search(r"L(?:_\{)?\d", tag["data-inline-latex"])


def test_every_numeric_equation_in_the_prepared_proof_is_an_identity():
    checked = 0
    for case in CASES:
        if "unsupported_reason" in case:
            continue
        rule = get_group_profile(case["group"]).content_rule_key
        if not rule.startswith("numeric-logarithm-"):
            continue
        result = plan(case, deepcopy(case["context"]))
        html = next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"].startswith("section:solution")
        )
        previous = None
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
            text = tag["data-inline-latex"]
            if re.search(
                r"[abcduvr]",
                text.replace("\\frac", "")
                .replace("\\log", "")
                .replace("\\sqrt", "")
                .replace("\\cdot", "")
                .replace("\\ln", "")
                .replace("\\quad", ""),
            ):
                continue
            parts = [p or previous for p in text.split("=")]
            assert all(parts), (case["task"], text)
            values = [value(p) for p in parts]
            assert all(sp.cancel(sp.powsimp(v - values[0])) == 0 for v in values[1:]), (
                case["task"],
                text,
                values,
            )
            previous = parts[-1]
            checked += 1
    assert checked > 400


@pytest.mark.parametrize(
    "q,reciprocal",
    [(sp.Rational(-2, 3), False), (sp.Rational(3, 7), True), (sp.Integer(0), False)],
)
def test_monomial_expansion_keeps_rational_and_zero_given_logarithms(q, reciprocal):
    case = next(c for c in CASES if c["task"] == "77415")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    relation = r"\log_b a" if reciprocal else r"\log_a b"
    condition["html"] = (
        '<p>Найдите значение выражения <span data-inline-latex="\\log_a(a^{-2}b^{-3})"></span>, если <span data-inline-latex="'
        + relation
        + "="
        + sp.latex(q)
        + '"></span>.</p>'
    )
    expected = -2 - 3 * (1 / q if reciprocal else q)
    assert sp.Rational(plan(case, context).answer.replace(",", ".")) == expected


def test_a_zero_given_logarithm_cannot_be_inverted():
    case = next(c for c in CASES if c["task"] == "77415")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        '<p>Найдите значение выражения <span data-inline-latex="\\log_a(ab^3)"></span>, если <span data-inline-latex="\\log_b a=0"></span>.</p>'
    )
    with pytest.raises(ValueError, match="cannot be inverted"):
        plan(case, context)
