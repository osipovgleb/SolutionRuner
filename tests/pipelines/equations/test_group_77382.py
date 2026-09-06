from solution_runner.pipelines.equations.group_77382 import _build_plan


def test_solves_the_parent_through_the_positive_logarithm_base():
    plan = _build_plan(r"\log_{(x-5)}49=2")
    assert plan.answer == "12"
    assert r"\begin{cases}49=(x-5)^{2}\\x-5\gt 0\\x-5\ne 1\end{cases}" in plan.solution_html
    assert r"x-5=\pm 7" in plan.solution_html
    assert "Альтернативное" not in plan.solution_html


def test_solves_a_child_with_a_plus_sign_in_the_logarithm_base():
    plan = _build_plan(r"\log_{(x+5)}4=2")
    assert plan.answer == "-3"
    assert r"x+5=2\iff x=-3" in plan.solution_html
