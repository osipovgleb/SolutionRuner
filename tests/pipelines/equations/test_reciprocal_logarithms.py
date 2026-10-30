import pytest

from solution_runner.pipelines.equations.reciprocal_logarithms import (
    build_reciprocal_plan,
)


@pytest.mark.parametrize(
    ("formula", "answer"),
    [
        (r"\log_2 \frac{x}{6}=\log_{(0{,}5)} (x+1)", "2"),
        (r"\log_5 \frac{x}{2}=\log_{(0{,}2)} (x+1)", "1"),
        (r"\log_2 \frac{x}{1}=\log_{\frac{1}{2}} (2-x)", "1"),
    ],
)
def test_reciprocal_bases_keep_only_roots_with_positive_arguments(formula, answer):
    plan = build_reciprocal_plan(formula)
    assert plan.answer == answer
    assert ">0" in plan.solution_html


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_2 \frac{x}{6}=\log_5 (x+1)",
        r"\log_1 \frac{x}{6}=\log_1 (x+1)",
        r"\log_2 \frac{x}{6}=\log_{(0{,}5)} (-x-1)",
        r"\log_2 \frac{x}{7}=\log_{(0{,}5)} (x+1)",
        r"\log_2 \frac{x}{6}=\log_{(0{,}5)} (5-x)",
    ],
)
def test_invalid_bases_or_ambiguous_or_irrational_roots_fail_closed(formula):
    with pytest.raises(ValueError):
        build_reciprocal_plan(formula)
