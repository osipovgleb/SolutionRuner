"""Shared physical derivative rule and the requested velocity calculation chain."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from test_analytic_calculus import motion
from test_category_9_source_samples import CASES, plan

from solution_runner.pipelines.core.group_profiles import get_group_profile

GROUPS = ("119975", "119976", "119977", "119978", "119979", "501059")


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def test_whole_physical_theme_selects_one_handler():
    assert {get_group_profile(g).content_rule_key for g in GROUPS} == {
        "calculus-polynomial-motion"
    }


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] in GROUPS], ids=lambda c: c["task"]
)
def test_first_line_differentiates_the_actual_law_and_next_step_uses_V(case):
    result = plan(case, case["context"])
    f = formulas(result.solution_html)
    assert f[0].startswith("V(t)=x'(t)=\\left(")
    assert r"\right)'=" in f[0]
    assert f[1].startswith("V(")
    assert "(t^n)" not in result.solution_html


def test_value_substitution_has_explicit_products_and_no_parentheses_on_positive_integer():
    case, context = motion(
        "6t^2-48t+17", "Найдите ее скорость (в м/с) в момент времени t = 9 с."
    )
    result = plan(case, context)
    f = formulas(result.solution_html)
    assert result.answer == "60"
    assert any(x.startswith(r"V(9)=12 \cdot 9 - 48=60") for x in f)
    assert "(9)" not in f[1].removeprefix("V(9)")


def test_time_problem_first_states_the_velocity_equation():
    case, context = motion(
        "t^2-13t+23",
        "В какой момент времени (в секундах) ее скорость была равна 3 м/с?",
    )
    result = plan(case, context)
    assert formulas(result.solution_html)[1] == "V(t)=3"
    assert result.answer == "8"


def test_materialized_html_is_idempotent_after_apostrophe_normalization():
    case = next(c for c in CASES if c["task"] == "119975")
    context = deepcopy(case["context"])
    result = plan(case, context)
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "solution"
    )["html"] = str(BeautifulSoup(result.solution_html, "html.parser"))
    assert plan(case, context).transformations == ()


def test_quadratic_velocity_equation_reuses_discriminant_presentation():
    from solution_runner.pipelines.calculus.common import T
    from solution_runner.pipelines.function_graphs.parabola_proof import quadratic_steps

    case, context = motion(
        "t^3/3-3t^2-5t+3",
        "В какой момент времени (в секундах) ее скорость была равна 2 м/с?",
    )
    # Keep the supported fraction notation of the source grammar.
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("t^3/3", r"\frac{1}{3}t^3")
    result = plan(case, context)
    f = formulas(result.solution_html)
    assert result.answer == "7"
    assert any(x.startswith("D=") and x.endswith("=64") for x in f)
    assert not any("(t - 7)" in x for x in f)
    expected = formulas(quadratic_steps(T * T - 6 * T - 7, T, [-1, 7]))
    normalized = [x.removeprefix(r"\displaystyle ") for x in f]
    assert all(x in normalized for x in expected[:2])
    union = next(x for x in f if r"\left[\begin{aligned}t&=" in x)
    assert union.count(r"\sqrt{64}") == 2
    assert r"=-1\\t&=" in union
    assert union.endswith(r"=7\end{aligned}\right.")
    assert r"\pm" not in union
    assert not any(r"\in\left\{" in x for x in f)
