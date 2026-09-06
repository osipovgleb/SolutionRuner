from solution_runner.pipelines.equations.group_315535 import _build_plan, _normalize_formula


def test_uses_the_parent_main_solution_without_a_dot_after_the_system():
    plan = _build_plan(r"2^{\log_8 (5x-3)}=4")
    assert plan.answer == "13,4"
    assert r"\begin{cases}(5x-3)^{\log_8 2}=4\\5x-3\gt 0\end{cases}\quad" in plan.solution_html
    assert r"(5x-3)^{\frac{1}{3}}=4\iff 5x-3=64\iff x=13{,}4" in plan.solution_html
    assert r"2^{\log_8 (5x-3)}=2^{2}\iff \log_8 (5x-3)=2" in plan.solution_html
    assert "<p><b>Приведём другое решение.</b></p>" not in plan.solution_html
    assert 'data-solution-title="Приведём другое решение."' in plan.solution_html
    assert "Примечание" not in plan.solution_html


def test_recomputes_child_and_normalizes_the_numeric_logarithm_base():
    plan = _build_plan(r"2^{\log_{(8)} (4x+5)}=7")
    assert plan.answer == "84,5"
    assert r"(4x+5)^{\frac{1}{3}}=7\iff 4x+5=343\iff x=84{,}5" in plan.solution_html
    assert r"8^{\log_8 (4x+5)}=7^{3}\iff 4x+5=343" in plan.solution_html


def test_accepts_a_multi_digit_logarithm_base_beginning_with_one():
    plan = _build_plan(r"2^{\log_{16} (2x-5)}=2")
    assert plan.answer == "10,5"
    assert r"(2x-5)^{\frac{1}{4}}=2\iff 2x-5=16\iff x=10{,}5" in plan.solution_html


def test_normalizes_a_bare_affine_logarithm_argument():
    formula = _normalize_formula(r"2^{\log_{(4)} 2x+5}=3")
    plan = _build_plan(formula)
    assert formula == r"2^{\log_4 (2x+5)}=3"
    assert plan.answer == "2"
