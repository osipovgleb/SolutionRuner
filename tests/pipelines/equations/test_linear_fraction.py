from fractions import Fraction

from solution_runner.pipelines.equations.linear_fraction import solve_reciprocal_linear_equation


def test_solves_reciprocal_linear_equation_exactly() -> None:
    assert solve_reciprocal_linear_equation(Fraction(6), Fraction(4), Fraction(-54), Fraction(1, 49)) == 87
