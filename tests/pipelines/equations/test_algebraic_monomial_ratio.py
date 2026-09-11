from solution_runner.pipelines.equations.algebraic_monomial_ratio import build_context_repair_plan
from solution_runner.pipelines.core.group_profiles import all_group_profiles
def context(f): return {"normalized_content":{"format":"teacherhelper-normalized","schema_version":3,"assets":[],"sections":[{"key":"condition","html":f'<p><span data-inline-latex="{f}"></span></p>',"asset_keys":[]},{"key":"answer","html":"<p></p>","asset_keys":[]}]}}
def test_fraction_and_colon_forms():
 assert build_context_repair_plan(context(r"\frac{9axy-(-7xya)}{4yax}")).answer=="4"
 assert build_context_repair_plan(context(r"(2axy-(-2xya))\colon4yax")).answer=="1"
 assert build_context_repair_plan(context(r"(axy-(-3xya))\colon2yax")).answer=="2"
 assert build_context_repair_plan(context(r"(9axy-(-6xya))\colon(3yax)")).answer=="5"

def test_group_512352_form_is_registered_and_computed():
 plan = build_context_repair_plan(context(r"(9axy-(-6xya))\colon3yax"))
 assert plan.answer == "5"
 assert all_group_profiles()["512352"].content_rule_key == "algebraic-monomial-ratio"
