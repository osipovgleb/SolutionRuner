from solution_runner.pipelines.equations.group_77379 import build_context_repair_plan, _build_plan


def test_parent_has_the_parent_method_and_the_fraction_method():
    plan = _build_plan(r"2^{3+x}=0{,}4\cdot5^{3+x}")
    assert plan.answer == "-2"
    assert r"\frac{2^{3+x}}{5^{3+x}}=0{,}4\iff (\frac{2}{5})^{3+x}=(\frac{2}{5})^{1}\iff 3+x=1\iff x=-2" in plan.solution_html
    assert r"2^{3+x}=0{,}4\cdot5^{3+x}\iff 2^{3+x}=\frac{2}{5}\cdot 5^{3+x}\iff \frac{2^{3+x}}{2^{1}}=\frac{5^{3+x}}{5^{1}}\iff 2^{2+x}=5^{2+x}" in plan.solution_html
    assert "Разные числа в одинаковой степени могут быть равны, только когда оба значения равны единице. Значит, показатель степени равен нулю:" in plan.solution_html


def test_child_uses_its_own_values_and_keeps_a_terminating_decimal_answer():
    plan = _build_plan(r"6^{2-5x}=0{,}6\cdot10^{2-5x}")
    assert plan.answer == "0,2"
    assert r"(\frac{3}{5})^{2-5x}=(\frac{3}{5})^{1}\iff 2-5x=1\iff x=\frac{1}{5}\iff x=0{,}2" in plan.solution_html
    assert r"\frac{6^{2-5x}}{6^{1}}=\frac{10^{2-5x}}{10^{1}}\iff 6^{1-5x}=10^{1-5x}" in plan.solution_html


def test_accepts_a_decimal_multiplier_with_leading_zeroes_and_find_root_wording():
    plan = _build_plan(r"2^{3-5x}=0{,}04\cdot10^{3-5x}")
    assert plan.answer == "0,2"
    context = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p>Найдите корень уравнения <span data-inline-latex="2^{3-5x}=0{,}04\\cdot10^{3-5x}"></span>.</p>', "asset_keys": [], "section_id": "condition:1"},
    ]}})
    assert context.answer == "0,2"


def test_context_accepts_a_plain_solve_equation_condition():
    plan = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p>Решите уравнение <span data-inline-latex="2^{3+x}=0{,}4\\cdot5^{3+x}"></span>.</p>', "asset_keys": [], "section_id": "condition:1"},
    ]}})
    assert plan.answer == "-2"
    assert "Основное решение" not in plan.solution_html
    assert "<p><strong>Альтернативное решение</strong></p>" in plan.solution_html


def test_rewrites_a_previous_one_formula_solution_to_the_two_method_solution():
    plan = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p>Решите уравнение <span data-inline-latex="2^{3+x}=0{,}4\\cdot5^{3+x}"></span>.</p>', "asset_keys": [], "section_id": "condition:1"},
        {"key": "solution", "title": "Решение", "html": '<center><p><span data-inline-latex="2^{3+x}=0{,}4\\cdot5^{3+x}"></span>.</p></center>', "asset_keys": [], "section_id": "solution:1"},
    ]}})
    assert any(change["transformation_target_id"] == "section:solution" for change in plan.transformations)
