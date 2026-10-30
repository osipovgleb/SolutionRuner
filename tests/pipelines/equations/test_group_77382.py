import pytest

from solution_runner.pipelines.equations.group_77382 import (
    UnsupportedCondition,
    _build_plan,
)


def test_solves_the_parent_through_the_positive_logarithm_base():
    plan = _build_plan(r"\log_{(x-5)}49=2")
    assert plan.answer == "12"
    assert (
        r"\begin{cases}49=(x-5)^{2}\\x-5\gt 0\\x-5\ne 1\end{cases}"
        in plan.solution_html
    )
    assert r"x-5=\pm 7" in plan.solution_html
    assert "Альтернативное" not in plan.solution_html


def test_solves_a_child_with_a_plus_sign_in_the_logarithm_base():
    plan = _build_plan(r"\log_{(x+5)}4=2")
    assert plan.answer == "-3"
    assert r"x+5=2\iff x=-3" in plan.solution_html


def test_unbraced_variable_base_and_odd_power_have_one_real_base():
    plan = _build_plan(r"\log_x32=5")

    assert plan.answer == "2"
    assert r"\pm" not in plan.solution_html
    assert r"x\gt 0" in plan.solution_html
    assert r"x\ne 1" in plan.solution_html
    assert r"x=2\iff x=2" not in plan.solution_html


@pytest.mark.parametrize("formula", [r"\log_x1=5", r"\log_x33=5", r"\log_{x^{2}}32=5"])
def test_rejects_invalid_base_or_an_unsupported_equation(formula):
    with pytest.raises(UnsupportedCondition):
        _build_plan(formula)
