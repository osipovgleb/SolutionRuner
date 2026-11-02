"""Preserve certified parent families and their roles after safe squaring."""

import re
from dataclasses import replace
from html import escape

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_parameters import affine_families
from .exam_trigonometric_selection import equivalent_series


def double_polynomial(expression):
    if not expression.is_polynomial(S, C):
        raise UnsupportedCondition("the auxiliary double angle needs a polynomial")
    polynomial = sp.Poly(expression, S, C)
    if (
        polynomial.total_degree() > 2
        or polynomial.coeff_monomial(S)
        or polynomial.coeff_monomial(C)
    ):
        raise UnsupportedCondition("the auxiliary double angle needs a pure quadratic")
    a, b, c, d = (polynomial.coeff_monomial(v) for v in (S * S, C * C, S * C, 1))
    return sp.expand(c * S / 2 + (b - a) * C / 2 + (a + b) / 2 + d)


def auxiliary_series(branch):
    from .exam_trigonometric_inverse import level_series

    result = []
    for q, p in level_series(branch.variable, branch.values[0]):
        q, p = (q - branch.angle_shift) / 2, p / 2
        if p != 1:
            raise UnsupportedCondition("the double-angle method needs two parity cases")
        result.append((q - p if q > p / 2 else q, p))
    if not result:
        raise UnsupportedCondition("the parent auxiliary angle must have exact roots")
    return tuple(result)


def auxiliary_branch(data, parent_html):
    from .exam_trigonometric import select
    from .exam_trigonometric_linear_phase import branch, notation
    from .exam_trigonometric_shifted import candidates, formula

    forms = [
        formula(n["data-inline-latex"])
        for n in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    ]
    reviewed = {
        (name, shift)
        for f in forms
        for name, _, shift in candidates(f, argument_scale=sp.Integer(2))
    }
    if not reviewed:
        return None
    if data.multiplier.free_symbols or data.multiplier == 0:
        raise UnsupportedCondition("the auxiliary square needs a constant root weight")
    double_polynomial(data.radicand)
    double_polynomial(sp.cancel(data.right / data.multiplier) ** 2)
    projected = double_polynomial(data.squared)
    value = branch(sp.primitive(projected)[1])
    if len(reviewed) != 1 or value is None:
        raise UnsupportedCondition(
            "one exact auxiliary double-angle identity is required"
        )
    value = notation((value,), parent_html, scale=sp.Integer(2))[0]
    name = "sin" if value.variable == S else "cos"
    if (name, value.angle_shift) not in reviewed:
        raise UnsupportedCondition("the auxiliary phase must match the parent method")
    value = replace(value, angle_scale=sp.Integer(2))
    roots = select(auxiliary_series(value), (0, 2, True, False))[0]
    return replace(value, residues=roots)


def parameter_roles(html):
    source = affine_families(html)
    if len({name for _, _, name in source}) <= 1:
        return ()
    soup = BeautifulSoup(html, "html.parser")
    first = soup.find("li", attrs={"data-list-marker": "а)"})
    if first is None:
        raise UnsupportedCondition("distinct square-branch parameters require part a")
    formulas = [n["data-inline-latex"] for n in first.select("[data-inline-latex]")]
    if not formulas:
        raise UnsupportedCondition("the parent must declare its final square branches")
    final = re.split(r"\\(?:iff|Leftrightarrow)", formulas[-1])[-1]
    accepted = affine_families(
        '<span data-inline-latex="' + escape(final) + '"></span>'
    )
    if (
        len(accepted) != 2
        or accepted[0][0].is_Integer is not True
        or accepted[1][0].is_Integer is not False
        or any(p != 2 for _, p, _ in accepted)
        or accepted[0][2] == accepted[1][2]
    ):
        raise UnsupportedCondition(
            "the parent must bind zero and nonzero sine branches"
        )
    rejected = {name for _, _, name in source} - {n for _, _, n in accepted}
    if len(rejected) != 1:
        raise UnsupportedCondition("one rejected nominal branch parameter is required")
    return accepted[0][2], accepted[1][2], rejected.pop()


def prepare(a, parent_html):
    if a.radical_equation is None or a.radical_equation.kind != "safe_square":
        return a
    from .exam_trigonometric import select

    roles = parameter_roles(parent_html)
    if roles:
        zeros = tuple((q, p) for q, p in a.series if q.is_Integer is True)
        others = tuple((q, p) for q, p in a.series if q.is_Integer is not True)
        if (
            len(zeros) != 1
            or len(others) != 1
            or len(a.branches) != 1
            or a.branches[0].variable != S
            or 0 not in a.branches[0].values
            or any(p != 2 for _, p in a.series)
        ):
            raise UnsupportedCondition("the child's two sine branch roles changed")
        source = tuple(
            (q % 2 if q.is_Integer else (q % 2) - (2 if q % 2 > 1 else 0), p)
            for q, p in (*zeros, *others)
        )
        parameters = roles[:2]
    else:
        formulas = BeautifulSoup(parent_html, "html.parser").select(
            "[data-inline-latex]"
        )
        ordered_source = tuple(
            f for node in formulas for f in affine_families(str(node))
        )
        source = tuple(
            reversed(
                tuple(
                    dict.fromkeys(
                        (q, p)
                        for q, p, _ in reversed(ordered_source)
                        if equivalent_series((*a.series, (q, p)), a.series)
                    )
                )
            )
        )
        if (
            not source
            and a.sine_inverse
            and any(q.is_Rational is not True for q, _ in a.series)
        ):
            source = a.series
        if (
            a.radical_equation.mixed_factors
            or a.radical_equation.auxiliary_branch is not None
        ) and (not source or not equivalent_series(source, a.series)):
            source = a.series
        parameters = ()
    if not source or not equivalent_series(source, a.series):
        raise UnsupportedCondition(
            "the parent families must cover the complete filtered solution"
        )
    selected, trace = select(source, a.bounds)
    return replace(
        a,
        series=source,
        selected=selected,
        selections=trace,
        family_parameters=parameters,
        series_aligned=source != a.series,
        radical_equation=replace(a.radical_equation, parameters=roles),
    )
