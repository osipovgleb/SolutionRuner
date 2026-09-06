from solution_runner.pipelines.equations.group_101879_planner import build_repair_plan

def ctx(formula, answer=''):
 return {'normalized_content':{'format':'teacherhelper-normalized','schema_version':3,'assets':[],'sections':[{'key':'condition','section_id':'condition:1','transformation_target_id':'section:condition:1','asset_keys':[],'html':f'<p>Ре­ши­те урав­не­ние <span data-inline-latex="{formula}"></span>. Если урав­не­ние имеет более од­но­го корня, в от­ве­те за­пи­ши­те боль­ший из кор­ней.</p>'},{'key':'answer','section_id':'answer:1','transformation_target_id':'section:answer:1','html':f'<p>{answer}</p>'}]}}

def test_parent_math_and_second_task_style() -> None:
 plan=build_repair_plan(ctx(r'\frac{x-6}{7x+3}=\frac{x-6}{5x-1}'),parent_condition_asset_id=None)
 assert plan.answer=='6'
 plan=build_repair_plan(ctx(r'\frac{x+8}{5x+7}=\frac{x+8}{7x+5}'),parent_condition_asset_id=None)
 assert plan.answer=='1'

def test_zero_constant_denominator_and_pupil_friendly_numbers() -> None:
 plan=build_repair_plan(
  ctx(r'\frac{x+7}{3x+7}=\frac{x+7}{x}'),
  parent_condition_asset_id=None,
 )
 assert plan.answer=='-3{,}5'
 solution=plan.transformations[0]['value']['html']
 assert 'x\\ne-\\frac{7}{3}' in solution
 assert 'x\\ne0' in solution
 assert 'x=-3{,}5' in solution

def test_shortened_singular_root_wording() -> None:
 context=ctx(r'\frac{x+6}{4x+1{,}1}=\frac{x+6}{3x+1}')
 context['normalized_content']['sections'][0]['html']=context['normalized_content']['sections'][0]['html'].replace('боль­ший из кор­ней','боль­ший ко­рень')
 plan=build_repair_plan(context,parent_condition_asset_id=None)
 assert plan.answer=='-0{,}1'

def test_decimals_start_only_with_the_third_alternative_system() -> None:
 plan=build_repair_plan(
  ctx(r'\frac{x+7}{5x+3}=\frac{x+7}{x}'),
  parent_condition_asset_id=None,
 )
 solution=plan.transformations[0]['value']['html']
 assert 'x\\ne-\\frac{3}{5}\\\\x\\ne0\\\\x^{2}+7x=5x^{2}+38x+21' in solution
 assert 'x\\ne-0{,}6\\\\x\\ne0\\\\-4x^{2}-31x-21=0' in solution
