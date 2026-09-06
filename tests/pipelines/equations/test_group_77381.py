from solution_runner.pipelines.equations.group_77381 import _build_plan


def test_rewrites_a_shifted_logarithm_as_a_product_with_a_positivity_check():
    plan = _build_plan(r"\log_5 (7-x)=\log_5 (3-x)+1")
    assert plan.answer == "2"
    assert r"1=\log_5 5^{1}" in plan.solution_html
    assert "используем формулу" not in plan.solution_html
    assert r"\begin{cases}7-x\gt 0\\3-x\gt 0\\7-x=5^{1}(3-x)\end{cases}" in plan.solution_html
    assert r"\begin{cases}-x>-7\\-x>-3\\7-x=15-5x\end{cases}" in plan.solution_html
    assert r"\begin{cases}x<3\\x=2\end{cases}" in plan.solution_html


def test_recomputes_a_child_with_other_linear_coefficients():
    plan = _build_plan(r"\log_2 (8+3x)=\log_2 (3+x)+1")
    assert plan.answer == "-2"
    assert r"8+3x=2^{1}(3+x)" in plan.solution_html


def test_accepts_a_bare_x_as_the_right_logarithm_argument():
    plan = _build_plan(r"\log_2 (x+3)=\log_2 x+1")
    assert plan.answer == "3"
    assert r"\begin{cases}x+3\gt 0\\x\gt 0\\x+3=2^{1}(x)\end{cases}" in plan.solution_html
