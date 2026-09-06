from solution_runner.pipelines.equations.group_26650 import build_context_repair_plan, build_repair_plan

def test_parent_and_child_use_same_base_template():
    parent=build_repair_plan(r"2^{4-2x}=64")
    child=build_repair_plan(r"2^{2-x}=16")
    assert parent.answer=="-1" and child.answer=="-2"
    assert r"2^{2-x}=2^{4}\iff 2-x=4\iff x=-2" in child.solution_html

def test_keeps_the_parent_order_of_an_x_first_exponent():
    plan=build_repair_plan(r"5^{x-7}=\frac{1}{125}")
    assert r"5^{x-7}=5^{-3}\iff x-7=-3\iff x=4" in plan.solution_html

def test_any_exact_power_of_the_same_base_is_accepted():
    assert build_repair_plan(r"3^{7-2x}=243").answer=="1"

def test_all_affine_orders_and_fractional_base_are_supported_without_unit_coefficient():
    assert build_repair_plan(r"2^{3+x}=32").answer=="2"
    assert build_repair_plan(r"2^{2x-3}=2").answer=="2"
    assert build_repair_plan(r"2^{2x+3}=128").answer=="2"
    plan=build_repair_plan(r"\frac{1}{2}^{2-x}=\frac{1}{16}")
    assert plan.answer=="-2" and "1x" not in plan.solution_html
    assert build_repair_plan(r"\frac{1}{2}^{x}=8").answer=="-3"
    assert build_repair_plan(r"2^{x}=\frac{1}{8}").answer=="-3"

def test_decimal_base_is_normalized_to_a_fraction_before_matching_powers():
    plan=build_repair_plan(r"0{,}5^{x}=8")
    assert plan.answer=="-3"
    assert r"(\frac{1}{2})^{x}=(\frac{1}{2})^{-3}" in plan.solution_html

def test_parenthesized_fractional_base_matches_group_26652_parent():
    plan=build_repair_plan(r"(\frac{1}{3})^{x-8}=\frac{1}{9}")
    assert plan.answer=="10"
    assert r"(\frac{1}{3})^{x-8}=(\frac{1}{3})^{2}\iff x-8=2\iff x=10" in plan.solution_html

def test_reduces_a_composite_unit_fraction_to_an_integer_base():
    plan=build_repair_plan(r"(\frac{1}{9})^{x-13}=3")
    assert plan.answer=="12,5"
    assert r"3^{-2x+26}=3^{1}\iff -2x+26=1\iff x=\frac{25}{2}\iff x=12{,}5" in plan.solution_html

def test_preserves_a_composite_base_when_the_right_side_already_uses_it():
    plan=build_repair_plan(r"9^{-5+x}=729")
    assert plan.answer=="8"
    assert r"9^{-5+x}=9^{3}\iff -5+x=3\iff x=8" in plan.solution_html

def test_uses_an_integer_base_for_a_fractional_base_against_an_integer():
    plan=build_repair_plan(r"(\frac{1}{8})^{-3+x}=512")
    assert plan.answer=="0"
    assert r"8^{3-x}=8^{3}\iff 3-x=3\iff x=0" in plan.solution_html

def test_keeps_a_fractional_common_base_when_both_sides_are_fractions():
    plan=build_repair_plan(r"(\frac{1}{9})^{x}=\frac{1}{3}")
    assert plan.answer=="0,5"
    assert r"(\frac{1}{3})^{2x}=(\frac{1}{3})^{1}\iff 2x=1\iff x=\frac{1}{2}\iff x=0{,}5" in plan.solution_html

def test_reduces_an_integer_power_base_to_the_common_base():
    plan=build_repair_plan(r"16^{x-9}=0{,}5")
    assert plan.answer=="8,75"
    assert r"2^{4x-36}=2^{-1}\iff 4x-36=-1\iff x=\frac{35}{4}\iff x=8{,}75" in plan.solution_html

def test_reduces_two_distinct_bases_to_one_common_base():
    plan=build_repair_plan(r"6^{2-4x}=36^{3x}")
    assert plan.answer=="0,2"
    assert r"6^{2-4x}=6^{6x}\iff 2-4x=6x" in plan.solution_html

def test_reduces_reciprocal_and_integer_bases_to_one_common_base():
    plan=build_repair_plan(r"(\frac{1}{2})^{x-6}=4^{x}")
    assert plan.answer=="2"
    assert r"2^{6-x}=2^{2x}\iff 6-x=2x\iff 6=3x\iff x=2" in plan.solution_html

def test_keeps_the_left_and_right_sides_in_their_original_order_when_collecting_terms():
    plan=build_repair_plan(r"(\frac{1}{2})^{x-8}=2^{x}")
    assert r"2^{8-x}=2^{x}\iff 8-x=x\iff 8=2x\iff x=4" in plan.solution_html

def test_normalizes_a_formula_split_out_of_the_introductory_paragraph():
    plan=build_context_repair_plan({"normalized_content":{"format":"teacherhelper-normalized","schema_version":3,"assets":[],"sections":[
        {"key":"condition","title":"Условие","html":"<p>Найдите корень уравнения: </p><span data-inline-latex=\"3^{7+x}=3\"></span>.","asset_keys":[],"section_id":"condition:1"},
        {"key":"answer","title":"Ответ","html":"<p>-6</p>","asset_keys":[],"section_id":"answer:1"},
    ]}})
    condition=next(change for change in plan.transformations if change["transformation_target_id"]=="section:condition")
    assert condition["value"]["html"] == '<p>Найдите корень уравнения: <span data-inline-latex="3^{7+x}=3"></span>.</p>'

def test_keeps_a_semantically_identical_solution_but_repairs_the_answer():
    plan=build_context_repair_plan({"normalized_content":{"format":"teacherhelper-normalized","schema_version":3,"assets":[],"sections":[
        {"key":"condition","title":"Условие","html":"<p>Найдите корень уравнения <span data-inline-latex=\"3^{7+x}=3\"></span>.</p>","asset_keys":[],"section_id":"condition:1"},
        {"key":"answer","title":"Ответ","html":"<p>0</p>","asset_keys":[],"section_id":"answer:1"},
        {"key":"solution","title":"Решение","html":"<p>Пе­рейдем к одному основанию степени:</p><center><p><span data-inline-latex=\"3^{7+x}=3\\iff 3^{7+x}=3^{1}\\iff 7+x=1\\iff x=-6\"></span>.</p></center>","asset_keys":[],"section_id":"solution:1"},
    ]}})
    targets={change["transformation_target_id"] for change in plan.transformations}
    assert "section:solution" not in targets
    assert "section:answer" in targets

def test_accepts_the_equivalent_find_a_solution_wording():
    plan=build_context_repair_plan({"normalized_content":{"format":"teacherhelper-normalized","schema_version":3,"assets":[],"sections":[
        {"key":"condition","title":"Условие","html":"<p>Найдите решение уравнения: <span data-inline-latex=\"2^{x}=8\"></span>.</p>","asset_keys":[],"section_id":"condition:1"},
    ]}})
    assert plan.answer == "3"
