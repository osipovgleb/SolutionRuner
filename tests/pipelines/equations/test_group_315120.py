from solution_runner.pipelines.equations.group_315120 import _build_plan, build_context_repair_plan


def test_uses_the_alternative_common_base_solution_for_the_parent():
    plan = _build_plan(r"\log_{(8)}2^{8x-4}=4")
    assert plan.answer == "2"
    assert r"\log_8 2^{8x-4}=4\iff 2^{8x-4}=8^{4}\iff 2^{8x-4}=2^{12}\iff 8x-4=12\iff x=2" in plan.solution_html


def test_recomputes_the_child_with_different_exponent_coefficients():
    plan = _build_plan(r"\log_{(4)}2^{3x+2}=4")
    assert plan.answer == "2"
    assert r"2^{3x+2}=2^{8}" in plan.solution_html


def test_accepts_a_multi_digit_logarithm_base():
    plan = _build_plan(r"\log_{(16)}2^{2x-4}=4")
    assert plan.answer == "10"
    assert r"2^{2x-4}=2^{16}" in plan.solution_html


def test_rewrites_parenthesized_numeric_base_in_the_condition():
    plan = build_context_repair_plan({"normalized_content": {"format": "teacherhelper-normalized", "schema_version": 3, "assets": [], "sections": [
        {"key": "condition", "title": "Условие", "html": '<p><span data-inline-latex="\\log_{(8)} 2^{8x-4}=4"></span></p>', "asset_keys": [], "section_id": "condition:1"},
    ]}})
    condition = next(item for item in plan.transformations if item["transformation_target_id"] == "section:condition")
    assert 'data-inline-latex="\\log_8 2^{8x-4}=4"' in condition["value"]["html"]
