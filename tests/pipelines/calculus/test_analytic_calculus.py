"""Independent derivative and contact identities, including degenerate cases."""

from copy import deepcopy
from itertools import product

import pytest
import sympy as sp
from test_category_9_source_samples import CASES, plan

from solution_runner.pipelines.core.numbers import parse_rational


def motion(law, query):
    case = next(c for c in CASES if c["task"] == "119975")
    context = deepcopy(case["context"])
    html = (
        '<p>Материальная точка движется прямолинейно по закону <span data-inline-latex="x(t)='
        + law
        + '"></span> (где x — расстояние от точки отсчета в метрах, t — время в секундах, измеренное с начала движения). '
        + query
        + "</p>"
    )
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = html
    return case, context


def tangent(curve, line, request, *, parallel=False, two=False):
    case = next(c for c in CASES if c["task"] == ("119972" if two else "27485"))
    context = deepcopy(case["context"])
    kind = "параллельна касательной" if parallel else "является касательной"
    html = (
        '<p>Прямая <span data-inline-latex="y='
        + line
        + '"></span> '
        + kind
        + ' к графику функции <span data-inline-latex="y='
        + curve
        + '"></span>. Найдите '
        + request
        + ".</p>"
    )
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = html
    return case, context


@pytest.mark.parametrize(
    "a,b,c,d,t",
    [
        (a, b, c, d, t)
        for (a, b, c, d), t in product(
            [(1, -2, 3, -4), (-2, 3, -5, 7), (0, 1, -3, 0)], [0, 1, 3]
        )
    ],
)
def test_velocity_is_the_signed_derivative_of_each_polynomial_term(a, b, c, d, t):
    law = rf"({a})t^4+({b})t^3+({c})t^2+({d})t+17"
    case, context = motion(
        law, f"Найдите ее скорость (в м/с) в момент времени t = {t} с."
    )
    assert (
        parse_rational(plan(case, context).answer)
        == 4 * a * t**3 + 3 * b * t**2 + 2 * c * t + d
    )


@pytest.mark.parametrize(
    "law,speed,expected",
    [
        (r"\frac{1}{3}t^3-2t^2-5t", 0, 5),
        (r"\frac{1}{3}t^3-t^2+t", 0, 1),
        ("t^2", 0, 0),
        ("-t^2+5t", -3, 4),
    ],
)
def test_time_roots_are_filtered_by_the_original_start_time_and_repeated_roots_deduplicate(
    law, speed, expected
):
    case, context = motion(
        law, f"В какой момент времени (в секундах) ее скорость была равна {speed} м/с?"
    )
    assert plan(case, context).answer == str(expected)


@pytest.mark.parametrize(
    "law,speed", [(r"\frac{1}{3}t^3-2t^2+3t", 0), ("t^2", -2), ("2t", 2)]
)
def test_an_ambiguous_absent_or_underdetermined_time_is_not_selected_arbitrarily(
    law, speed
):
    case, context = motion(
        law, f"В какой момент времени (в секундах) ее скорость была равна {speed} м/с?"
    )
    with pytest.raises(ValueError):
        plan(case, context)


def test_negative_time_and_nonpolynomial_domain_cancellation_are_rejected():
    for law, time in [("t^2", -1), (r"\frac{t}{t}+t^2", 2), ("x^2", 2)]:
        case, context = motion(
            law, f"Найдите ее скорость (в м/с) в момент времени t = {time} с."
        )
        with pytest.raises(ValueError):
            plan(case, context)


def test_parallel_tangent_does_not_require_the_given_line_to_pass_through_the_graph():
    case, context = tangent("x^2+x-8", "100", "абсциссу точки касания", parallel=True)
    assert plan(case, context).answer == "-0,5"
    case, context = tangent("x^2+x-8", "100", "абсциссу точки касания")
    with pytest.raises(ValueError):
        plan(case, context)


def test_a_true_cubic_tangent_filters_derivative_roots_by_the_common_point():
    case, context = tangent("x^3+7x^2+7x-6", "-4x-11", "абсциссу точки касания")
    assert plan(case, context).answer == "-1"
    case, context = tangent(
        "x^3+7x^2+7x-6", "-4x-11", "абсциссу точки касания", parallel=True
    )
    with pytest.raises(ValueError):
        plan(case, context)


def test_contact_ordinate_and_repeated_zero_contact_are_supported():
    case, context = tangent("x^3+4x^2+3x+4", "3x+4", "ординату точки касания")
    assert plan(case, context).answer == "4"
    case, context = tangent("x^3", "0", "абсциссу точки касания")
    assert plan(case, context).answer == "0"


@pytest.mark.parametrize(
    "a,b,c,x0", [(2, 3, 7, 1), (-3, 2, 5, -2), (sp.Rational(1, 8), 2, 3, 4)]
)
def test_leading_parameter_matches_an_independently_constructed_tangent_in_both_methods(
    a, b, c, x0
):
    k, l = 2 * a * x0 + b, c - a * x0 * x0
    case, context = tangent(
        rf"ax^2+({b})x+({c})", sp.latex(k) + "x+(" + sp.latex(l) + ")", "a", two=True
    )
    assert parse_rational(plan(case, context).answer) == a


@pytest.mark.parametrize("x0", [-sp.Rational(1, 2), sp.Rational(1, 2)])
def test_linear_parameter_selects_the_requested_side_before_using_the_discriminant(x0):
    a, c, k = 8, 5, 3
    l = c - a * x0 * x0
    expected = k - 2 * a * x0
    request = (
        "b, учитывая, что абсцисса точки касания "
        + ("больше" if x0 > 0 else "меньше")
        + " 0"
    )
    case, context = tangent(f"{a}x^2+bx+{c}", f"{k}x+{l}", request, two=True)
    assert parse_rational(plan(case, context).answer) == expected


def test_constant_parameter_and_zero_contact_are_not_mistaken_for_absence_of_a_tangent():
    case, context = tangent("2x^2-3x+c", "x+5", "c")
    assert plan(case, context).answer == "7"
    case, context = tangent("2x^2+bx+1", "3x+1", "b", two=True)
    assert plan(case, context).answer == "3"


@pytest.mark.parametrize(
    "curve,line,quantity",
    [
        ("ax^2+3x+1", "3x+1", "a"),
        ("ax^2+3x+2", "3x+1", "a"),
        ("8x^2+bx+5", "3x+3", "b"),
        ("2x^2+bx+1", "3x+1", "b, учитывая, что абсцисса точки касания больше 0"),
    ],
)
def test_degenerate_or_ambiguous_parameters_fail_closed(curve, line, quantity):
    case, context = tangent(curve, line, quantity, two=True)
    with pytest.raises(ValueError):
        plan(case, context)


def test_nested_or_attributed_superscripts_cannot_hide_unreviewed_markup():
    case = next(c for c in CASES if c["task"] == "119972")
    for bad in ['<sup data-extra="2">2</sup>', "<sup><i>2</i></sup>"]:
        context = deepcopy(case["context"])
        section = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "condition"
        )
        section["html"] = section["html"].replace("<sup>2</sup>", bad)
        with pytest.raises(ValueError):
            plan(case, context)
