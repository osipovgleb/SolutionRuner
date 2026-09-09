from solution_runner.pipelines.equations.algebraic_monomial_ratio import build_context_repair_plan
def context(f): return {"normalized_content":{"format":"teacherhelper-normalized","schema_version":3,"assets":[],"sections":[{"key":"condition","html":f'<p><span data-inline-latex="{f}"></span></p>',"asset_keys":[]},{"key":"answer","html":"<p></p>","asset_keys":[]}]}}
def test_fraction_and_colon_forms():
 assert build_context_repair_plan(context(r"\frac{9axy-(-7xya)}{4yax}")).answer=="4"
 assert build_context_repair_plan(context(r"(2axy-(-2xya))\colon4yax")).answer=="1"
 assert build_context_repair_plan(context(r"(axy-(-3xya))\colon2yax")).answer=="2"
