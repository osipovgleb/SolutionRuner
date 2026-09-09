from solution_runner.pipelines.equations.group_26646 import _build_plan, build_context_repair_plan


def test_parent_and_child_recompute_their_own_logarithm_values():
    parent = _build_plan(r"\log_2(4-x)=7")
    child = _build_plan(r"\log_6(3-x)=2")
    assert parent.answer == "-124"
    assert child.answer == "-33"
    assert r"\log_6 (3-x)=2\iff 3-x=6^{2}\iff 3-x=36\iff x=-33" in child.solution_html


def test_accepts_a_fractional_logarithm_base_and_negative_logarithm_value():
    plan = _build_plan(r"\log_{\frac{1}{7}} (7-3x)=-2")
    assert plan.answer == "-14"
    assert r"\log_{\frac{1}{7}} (7-3x)=-2\iff 7-3x=(\frac{1}{7})^{-2}\iff 7-3x=49\iff x=-14" in plan.solution_html


def test_accepts_a_plus_sign_and_any_integer_coefficient_inside_the_logarithm():
    plan = _build_plan(r"\log_2(4+2x)=7")
    assert plan.answer == "62"


def test_equates_arguments_of_same_base_logarithms_when_right_argument_has_x():
    plan = _build_plan(r"\log_5(5-x)=\log_5(3+x)")
    assert plan.answer == "1"
    assert r"\begin{cases}5-x=3+x\\3+x>0\end{cases}" in plan.solution_html
    assert r"\begin{cases}x=1\\x+3>0\end{cases}" in plan.solution_html


def test_cancels_matching_quadratic_terms_before_solving_equal_logarithms():
    plan = _build_plan(r"\log_8 (x^{2}+x)=\log_8 (x^{2}-4)")
    assert plan.answer == "-4"
    assert r"\begin{cases}x^{2}+x=x^{2}-4\\x^{2}-4\gt 0\end{cases}" in plan.solution_html
    assert r"\iff x=-4" in plan.solution_html


def test_records_parent_style_positivity_system_for_two_linear_logarithm_arguments():
    plan = _build_plan(r"\log_4 (x+3)=\log_4 (4x-15)")
    assert plan.answer == "6"
    assert r"\begin{cases}x+3=4x-15\\4x-15>0\end{cases}" in plan.solution_html
    assert r"\begin{cases}x=6\\4x>15\end{cases}" in plan.solution_html


def test_accepts_a_bare_right_logarithm_argument_and_preserves_its_style():
    plan = _build_plan(r"\log_5 (5-x)=\log_5 3")
    assert plan.answer == "2"
    assert r"\log_5 (5-x)=\log_5 3\iff 5-x=3\iff x=2" in plan.solution_html


def test_accepts_any_integer_logarithm_base_greater_than_one():
    plan = _build_plan(r"\log_{13} (4-x)=\log_{13} 10")
    assert plan.answer == "-6"
    assert r"\log_{13} (4-x)=\log_{13} 10\iff 4-x=10\iff x=-6" in plan.solution_html


def test_keeps_a_two_digit_logarithm_base_in_one_latex_subscript():
    plan = _build_plan(r"\log_{10} (3-x)=\log_{10} 2")
    assert r"\log_{10} (3-x)=\log_{10} 2\iff 3-x=2\iff x=1" in plan.solution_html
    assert r"\log_10" not in plan.solution_html


def test_rewrites_an_integer_multiple_of_a_logarithm_with_the_same_base():
    plan = _build_plan(r"\log_3 (6-4x)=4\log_3 2")
    assert plan.answer == "-2,5"
    assert r"\log_3 (6-4x)=4\log_3 2\iff \log_3 (6-4x)=\log_3 2^{4}\iff 6-4x=16\iff x=-\frac{5}{2}\iff x=-2{,}5" in plan.solution_html


def test_rejects_equal_logarithms_when_the_shared_argument_is_not_positive():
    try:
        _build_plan(r"\log_5(x-2)=\log_5(-x)")
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("non-positive logarithm arguments must be rejected")


def test_normalizes_parenthesized_logarithm_base_notation():
    plan = _build_plan(r"\log_{(5)}(4+x)=2")
    assert plan.answer == "21"
    assert r"\log_5 (4+x)=2\iff 4+x=5^{2}\iff 4+x=25\iff x=21" in plan.solution_html


def test_accepts_decimal_logarithm_shorthand():
    plan = _build_plan(r"\lg (-4x-30)=2")
    assert plan.answer == "-32,5"
    assert r"\log_{10} (-4x-30)=2\iff -4x-30=10^{2}\iff -4x-30=100\iff x=-\frac{65}{2}\iff x=-32{,}5" in plan.solution_html


def test_rewrites_parenthesized_base_in_the_condition_before_writing_solution():
    plan = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p>Найдите корень уравнения <span data-inline-latex="\\log_{(8)} (4+x)=2"></span>.</p>', "asset_keys": [], "section_id": "condition:1"},
    ]}})
    condition = next(item for item in plan.transformations if item["transformation_target_id"] == "section:condition")
    assert 'data-inline-latex="\\log_8 (4+x)=2"' in condition["value"]["html"]


def test_normalizes_parenthesized_fractional_base_in_the_condition():
    plan = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p><span data-inline-latex="\\log_{(\\frac{1}{8})} (4-4x)=-2"></span></p>', "asset_keys": [], "section_id": "condition:1"},
    ]}})
    condition = next(item for item in plan.transformations if item["transformation_target_id"] == "section:condition")
    assert 'data-inline-latex="\\log_{\\frac{1}{8}} (4-4x)=-2"' in condition["value"]["html"]


def test_context_rewrites_only_the_missing_solution():
    plan = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p>Найдите корень уравнения <span data-inline-latex="\\log_6 (3-x)=2"></span>.</p>', "asset_keys": [], "section_id": "condition:1"},
        {"key": "answer", "title": "Ответ", "html": "<p>-33</p>", "asset_keys": [], "section_id": "answer:1"},
    ]}})
    assert plan.answer == "-33"
    assert [item["transformation_target_id"] for item in plan.transformations] == ["section:solution"]


def test_context_does_not_rewrite_a_matching_quadratic_logarithm_solution():
    plan = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p><span data-inline-latex="\\log_5 (x^{2}+2x)=\\log_5 (x^{2}+10)"></span>.</p>', "asset_keys": [], "section_id": "condition:1"},
        {"key": "solution", "title": "Решение", "html": '<p>Пе­рей­дем к од­но­му ос­но­ва­нию сте­пе­ни:</p><center><p> <span data-inline-latex="\\log_5 (x^{2}+2x)=\\log_5 (x^{2}+10)\\iff \\begin{cases}x^{2}+2x=x^{2}+10\\\\x^{2}+10\\gt 0\\end{cases}.\\quad \\iff x=5"></span>.</p></center>', "asset_keys": [], "section_id": "solution:1"},
        {"key": "answer", "title": "Ответ", "html": "<p>5</p>", "asset_keys": [], "section_id": "answer:1"},
    ]}})
    assert plan.transformations == ()


def test_context_accepts_any_prose_around_one_logarithmic_formula():
    plan = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p>Решите: <span data-inline-latex="\\log_2 (4+x)=7"></span>.</p>', "asset_keys": [], "section_id": "condition:1"},
    ]}})
    assert plan.answer == "124"
