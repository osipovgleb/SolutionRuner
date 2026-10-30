"""Independent radical identities include signs, endpoints and original domains."""

from copy import deepcopy
from itertools import product

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_category_8_source_samples import CASES, plan


def question(group, expression, constraint=None):
    case = next(c for c in CASES if c["group"] == group)
    context = deepcopy(case["context"])
    html = (
        '<p>Найдите значение выражения <span data-inline-latex="'
        + expression
        + '"></span>'
    )
    if constraint:
        html += ' при <span data-inline-latex="' + constraint + '"></span>'
    html += ".</p>"
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = html
    return case, context


@pytest.mark.parametrize("m,n", tuple(product([-5, -1, 2, 7], [-3, 1, 4])))
def test_polynomial_square_expansion_uses_cross_term_and_cancels_before_substitution(
    m, n
):
    expression = rf"\frac{{({m}x+({n})y)^2-({m * m})x^2-({n * n})y^2}}{{2xy}}"
    case, context = question("647129", expression, r"x=-2, y=\sqrt{3}")
    assert sp.Rational(plan(case, context).answer.replace(",", ".")) == m * n
    case, context = question("647129", expression, r"x=0, y=\sqrt{3}")
    with pytest.raises(ValueError, match="nonzero denominator"):
        plan(case, context)


@pytest.mark.parametrize("degree,c,k", tuple(product([2, 3, 5, 7], [2, 7, 11], [1, 2])))
def test_complete_root_power_cancels_even_when_the_variable_is_negative(degree, c, k):
    expression = (
        rf"\frac{{(\sqrt[{degree}]{{{c}a^{{2}}}})^{{{degree * k}}}}}{{a^{{{2 * k}}}}}"
    )
    case, context = question("26832", expression, r"a\ne0")
    assert plan(case, context).answer == str(c**k)
    for a in [-3, 2]:
        assert sp.real_root(c * a * a, degree) ** (degree * k) / a ** (2 * k) == c**k


@pytest.mark.parametrize(
    "expression,constraint",
    [
        (r"\frac{(\sqrt[3]{7a^{2}})^{6}}{a^{4}}", None),
        (r"\frac{(\sqrt[3]{7a^{2}})^{6}}{a^{4}}", r"a=0"),
        (r"\frac{(\sqrt[3]{7a^{2}})^{5}}{a^{4}}", r"a\ne0"),
        (r"\frac{(\sqrt[2]{7a^{3}})^{4}}{a^{6}}", r"a\ne0"),
    ],
)
def test_root_power_method_needs_the_complete_domain_and_matching_exponents(
    expression, constraint
):
    case, context = question("26832", expression, constraint)
    with pytest.raises(ValueError):
        plan(case, context)


@pytest.mark.parametrize("n,m", [(2, 3), (3, 7), (4, 5), (7, 11)])
def test_nested_positive_roots_reduce_to_the_same_monomial(n, m):
    expression = rf"\frac{{9\sqrt[{n}]{{\sqrt[{m}]{{a}}}}-4\sqrt[{m}]{{\sqrt[{n}]{{a}}}}}}{{2\sqrt[{n * m}]{{a}}}}"
    case, context = question("26838", expression, r"a>0")
    assert plan(case, context).answer == "2,5"
    for constraint in [None, r"a\ne0", r"a=-1", r"a=0"]:
        case, context = question("26838", expression, constraint)
        with pytest.raises(ValueError):
            plan(case, context)


@pytest.mark.parametrize("k", [-22, -1, 0, 2, 13])
def test_square_root_of_square_is_an_absolute_value_at_and_below_the_boundary(k):
    expression = rf"x+\sqrt{{x^2+({-2 * k})x+({k * k})}}"
    case, context = question("26829", expression, rf"x\le{k}")
    assert plan(case, context).answer == str(k)
    for x in [k - 5, k - 1, k]:
        assert x + sp.sqrt(x * x - 2 * k * x + k * k) == k
    case, context = question("26829", expression, rf"x\le{k + 1}")
    with pytest.raises(ValueError, match="square centred"):
        plan(case, context)


def test_squares_outside_the_root_are_not_reinterpreted_as_absolute_values():
    case, context = question(
        "26830", r"\sqrt{(a-3)}^{2}+\sqrt{(a-5)}^{2}", r"3\le a\le5"
    )
    with pytest.raises(ValueError):
        plan(case, context)
    case, context = question(
        "26830", r"\sqrt{(a-3)^{2}}+\sqrt{(a-5)^{2}}", r"3\le a\le5"
    )
    assert plan(case, context).answer == "2"


@pytest.mark.parametrize("degree,d", tuple(product([3, 5, 9], [2, 5])))
def test_odd_root_symmetry_is_valid_on_both_sides_of_the_radical_zero(degree, d):
    for x in [-2 * d, -d, 0, d, 2 * d]:

        def h(t):
            return sp.real_root(t, degree) + sp.real_root(t - 2 * d, degree)

        assert sp.simplify(h(d + x) + h(d - x)) == 0
        if abs(x) != d:
            a = sp.real_root((d - x) * (2 * d - (d - x)), degree)
            b = sp.real_root((d + x) * (2 * d - (d + x)), degree)
            assert sp.simplify(a / b) == 1


@pytest.mark.parametrize("task", ["26839", "26840"])
def test_even_root_or_changed_centre_does_not_receive_an_odd_root_proof(task):
    case = next(c for c in CASES if c["task"] == task)
    for old, new in [
        (r"\sqrt[3]", r"\sqrt[2]"),
        ("4-x", "5-x") if task == "26839" else ("x-10", "x-11"),
    ]:
        context = deepcopy(case["context"])
        condition = next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "condition"
        )
        condition["html"] = condition["html"].replace(old, new)
        with pytest.raises(ValueError):
            plan(case, context)


def test_the_original_radical_parent_keeps_both_source_methods():
    case = next(c for c in CASES if c["task"] == "26824")
    result = plan(case, deepcopy(case["context"]))
    html = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert html.index("Первый способ") < html.index("Второй способ")
    assert any(
        r"t=\sqrt{x}>0" in tag["data-inline-latex"]
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )
