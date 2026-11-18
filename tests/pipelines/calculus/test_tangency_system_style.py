"""One named-function contact system for every analytic tangent group."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from test_analytic_calculus import tangent
from test_category_9_source_samples import CASES, plan

from solution_runner.pipelines.calculus.common import X
from solution_runner.pipelines.calculus.tangency import calculate
from solution_runner.pipelines.calculus.tangency_proof import render, substitute
from solution_runner.pipelines.core.group_profiles import get_group_profile

GROUPS = ("27485", "27486", "119972", "119974", "119973")


def formulas(html):
    return [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def test_all_five_groups_use_the_same_handler_without_method_options():
    assert {get_group_profile(g).content_rule_key for g in GROUPS} == {
        "calculus-polynomial-tangency"
    }


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] in GROUPS], ids=lambda c: c["task"]
)
def test_one_solution_defines_tangent_f_curve_g_and_point_equation_first(case):
    p = plan(case, case["context"])
    f = formulas(p.solution_html)
    assert f[0].startswith("f(x)=")
    assert any(x.startswith("g(x)=") for x in f)
    named = next(x for x in f if x.startswith(r"\begin{cases}f(x)=g(x)"))
    first, second = named.split(r"\\")
    assert r"f(x)=g(x),&\text{так как графики пересекаются}" in first
    assert r"f'(x)=g'(x),&\text{так как }f(x)\text{ — касательная к }g(x)" in second
    assert "В точке касания графики пересекаются, поэтому" not in p.solution_html
    assert (
        "Второй способ" not in p.solution_html
        and "Первый способ" not in p.solution_html
    )
    assert "пересекаются" in p.solution_html and "касательная" in p.solution_html


def test_parallel_line_has_an_unknown_offset_and_ordinate_comes_from_the_curve():
    case, context = tangent("x^2+x-8", "100", "ординату точки касания", parallel=True)
    p = plan(case, context)
    assert p.answer == "-8,25"
    assert formulas(p.solution_html)[0] == "f(x)=-b"
    assert "y=100" in formulas(p.solution_html)
    assert "y=g(" in p.solution_html
    # The free term of the given parallel line must not enter the contact system.
    assert not any(
        "100" in f for f in formulas(p.solution_html) if f.startswith(r"\begin{cases}")
    )


def test_substitution_keeps_explicit_multiplication_for_positive_numbers():
    assert r"3 \cdot 2" in substitute(3 * X + 4, 2)
    assert r"\left(2\right)" not in substitute(3 * X + 4, 2)


def test_coordinate_candidates_must_satisfy_both_equations():
    _case, context = tangent("x^3+7x^2+7x-6", "-4x-11", "абсциссу точки касания")
    c = calculate(context)
    assert len(c.candidates) == 2 and len(c.valid) == 1
    assert r"\ne" in render(c)


def test_server_attribute_serialization_does_not_rewrite_an_identical_solution():
    case = next(c for c in CASES if c["task"] == "27486")
    context = deepcopy(case["context"])
    first = plan(case, context)
    solution = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "solution"
    )
    solution["html"] = str(BeautifulSoup(first.solution_html, "html.parser"))
    assert plan(case, context).transformations == ()


def test_quadratic_contact_uses_discriminant_and_a_union_of_roots():
    _case, context = tangent("x^3+7*x^2+7*x-6", "-4*x-11", "абсциссу точки касания")
    html = render(calculate(context))
    f = formulas(html)
    assert any(x.startswith("D=") for x in f)
    assert not any(x.startswith(r"\displaystyle x=") and r"\pm" in x for x in f)
    union = next(x for x in f if r"\left[\begin{aligned}x&=" in x)
    assert union.count(r"\sqrt") == 2
    assert union.count(r"\frac") >= 2
    assert r"\pm" not in union
    assert not any(r"\in\left\{" in x for x in f)
