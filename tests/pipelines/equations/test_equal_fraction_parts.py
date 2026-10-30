import pytest

from solution_runner.pipelines.equations.group_315119_planner import _solve


@pytest.mark.parametrize(
    ("formula", "answer"),
    [
        (r"\frac{x+89}{x-7}=\frac{-5}{x-7}", "-94"),
        (r"\frac{3}{2x+1}=\frac{3}{x+4}", "3"),
        (r"\frac{1}{-x+1}=\frac{1}{x-3}", "2"),
        (r"\frac{1}{2}=\frac{1}{x+1}", "1"),
    ],
)
def test_equal_fraction_parts_compute_the_unique_root(formula, answer):
    assert _solve(formula).answer == answer


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{x+1}{x-2}=\frac{3}{x-2}",
        r"\frac{1}{x+1}=\frac{1}{x+1}",
        r"\frac{0}{x+1}=\frac{0}{2x+1}",
        r"\frac{x}{x+1}=\frac{2}{x+2}",
    ],
)
def test_domain_violations_or_unhandled_fraction_forms_fail_closed(formula):
    with pytest.raises(ValueError):
        _solve(formula)
