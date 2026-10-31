"""Inverse ratio grammar and original domains remain distinct from scalar division."""

import pytest
import sympy as sp

from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S, T
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


@pytest.mark.parametrize(
    "formula,values",
    [
        (r"\frac{1}{\tg^2 x}-\frac{1}{\tg x}=0", (1,)),
        (r"\frac{1}{\tg^2 x}-\frac{3}{\tg x}+2=0", (sp.Rational(1, 2), 1)),
        (r"\frac{1}{\ctg^2 x}-\frac{3}{\ctg x}+2=0", (sp.Rational(1, 2), 1)),
        (r"\frac{1}{\tg^2 x}-\frac{1}{2\tg x}=0", (2,)),
    ],
)
def test_inverse_ratio_substitution_preserves_both_domains_and_excludes_t_zero(
    formula, values
):
    from solution_runner.pipelines.equations.exam_trigonometric import solve_branches
    from solution_runner.pipelines.equations.exam_trigonometric_methods import (
        compile_reviewed,
    )

    equation = compile_reviewed(formula, T, sp.S.One, sp.S.Zero)
    assert equation.reciprocal is not None and set(equation.poles) == {S, C}
    result = solve_branches(equation.raw, T, True)[1]
    assert set(result[0].values) == set(values)


@pytest.mark.parametrize(
    "formula",
    [r"\frac{1}{\tg^3 x}+\frac{1}{\tg x}=0", r"\frac{1}{\tg^2 x+1}+\frac{1}{\tg x}=0"],
)
def test_unreviewed_inverse_ratio_shapes_fail_closed(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_methods import (
        compile_reviewed,
    )

    with pytest.raises(UnsupportedCondition):
        compile_reviewed(formula, T, sp.S.One, sp.S.Zero)


@pytest.mark.parametrize(
    "formula", [r"2\cos(\frac{\pi}{2}-x)=tgx", r"ctgx+\cos(\frac{\pi}{2}+2x)=0"]
)
def test_bare_school_ratio_notation_is_bounded_to_known_function_names(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_methods import (
        parse_equation,
    )

    _, atoms, _ = parse_equation(formula)
    assert any(a.function in ("tg", "ctg") for a in atoms.values())
    with pytest.raises(UnsupportedCondition):
        parse_equation(formula.replace("tgx", "foottgx"))


def test_constant_denominator_keeps_the_existing_tangent_quadratic_route():
    from solution_runner.pipelines.equations.exam_trigonometric_methods import (
        compile_reviewed,
    )

    equation = compile_reviewed(r"\frac{\tg^2 x}{2}-\tg x=0", T, sp.S.One)
    assert equation.reciprocal is None
    assert sp.expand(equation.raw - (T * T / 2 - T)) == 0
    assert equation.poles == (C,)
