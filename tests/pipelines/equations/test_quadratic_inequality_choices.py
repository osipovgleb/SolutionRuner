"""Check choice mathematics, visual evidence guards and four-asset convergence."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import pytest

from solution_runner.pipelines.core.content_runtime import _prepared_record, _apply_record
from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.quadratic_inequality_choices import (
    RULE, build_context_repair_plan, solve_choice, _condition_options, diagram_specs, _constant_sign_solution,
)
from solution_runner.pipelines.equations.inequality_system_svg import render_quadratic_sign_chart_svg
from solution_runner.pipelines.equations.linear_system_intervals import Interval
from test_inequality_systems_complete import Gateway

FIXTURES = json.loads((Path(__file__).parent / 'fixtures/quadratic_185.json').read_text())


class AnnotatingGateway(Gateway):
    """Model server serialization and transient asset-target annotations."""

    def __init__(self, context):
        super().__init__(context)
        self._annotate()

    def _annotate(self):
        for section in self.context['normalized_content']['sections']:
            soup = BeautifulSoup(section['html'], 'html.parser')
            for image in soup.find_all('img', attrs={'data-asset-key':True}):
                image['data-transformation-target-id'] = 'asset:' + image['data-asset-key']
            section['html'] = str(soup)

    def apply_problem_transformations(self, problem_id, transformations):
        solution_change = next((t for t in transformations if t['transformation_target_id'].startswith('section:solution')
                                and t['operation'] != 'remove'), None)
        solution = next((s for s in self.context['normalized_content']['sections'] if s['key']=='solution'), {})
        keys = list((solution_change['value'] if solution_change else solution).get('asset_keys', []))
        for change in transformations:
            if change['operation'] != 'add' or not change['transformation_target_id'].startswith('asset:generated_quadratic_option_'):
                continue
            key = change['value']['asset_key']
            position = change['value']['position']
            assert position == keys.index(key), 'asset position must follow the remaining image order'
            assert 0 <= position < len(keys), 'server cannot insert an asset beyond the section asset range'
        super().apply_problem_transformations(problem_id, transformations)
        self._annotate()


@pytest.mark.parametrize('sid,answer', [('185','4'), ('314596','1'), ('333004','2')])
def test_shared_runtime_four_diagrams_and_second_run_without_writes(sid, answer):
    context = FIXTURES[sid]
    gateway = Gateway(context)
    child = {'problem_id': context['problem_id'], 'source_problem_id': sid}
    record = _prepared_record(gateway, child, None, RULE)
    assert record['status'] == 'prepared', record
    assert record['expected_answer'] == answer
    diagram_count = 4 if sid == '333004' else 2
    assert len(record['generated_diagrams']) == diagram_count
    assert _apply_record(gateway, record, None, RULE)['status'] == 'applied'
    assert gateway.uploads == diagram_count
    assert gateway.writes == 1
    content = gateway.context['normalized_content']
    assert next(s for s in content['sections'] if s['key'] == 'condition') == next(
        s for s in context['normalized_content']['sections'] if s['key'] == 'condition')
    solution = next(s for s in content['sections'] if s['key'] == 'solution')
    soup = BeautifulSoup(solution['html'], 'html.parser')
    for row in soup.find_all('li'):
        if 'т.к.' in row.get_text():
            assert row.find('img') is None
            assert r'\Rightarrow x\in ' in row.find_all('span')[-1]['data-inline-latex']
            continue
        assert row.find('img')
        algebra = row.find('p').span['data-inline-latex']
        assert r'\in' not in algebra
        assert algebra.count(r'\iff') <= 1
        assert row.find_all('p')[-1].span['data-inline-latex'].startswith(r'x\in ')
        assert row.find('center').find_next_sibling('p') == row.find_all('p')[-1]
        assert row.find_all(recursive=False)[-1].name == 'br'
    assert len(solution['asset_keys']) == diagram_count
    assert _apply_record(gateway, record, None, RULE)['status'] == 'already_complete'
    assert gateway.uploads == diagram_count and gateway.writes == 1


@pytest.mark.parametrize('relation,truth,bound,result', [
    (r'\lt', 'ложь.', r'x^{2}\lt -25', r'\varnothing'),
    (r'\le', 'ложь.', r'x^{2}\le -25', r'\varnothing'),
    (r'\gt', 'ист.', r'x^{2}\gt -25', r'\mathbb{R}'),
    (r'\ge', 'ист.', r'x^{2}\ge -25', r'\mathbb{R}'),
])
def test_positive_constant_moves_right_and_uses_truth_explanation_without_diagram(relation,truth,bound,result):
    choice = solve_choice('x^{2}+25' + relation + '0')
    html = BeautifulSoup(_constant_sign_solution(choice), 'html.parser')
    assert html.find('img') is None
    assert truth + ', т.к.' in html.get_text()
    formulas = [s['data-inline-latex'] for s in html.find_all('span')]
    assert formulas == [choice.latex + r'\iff ' + bound, r'x^{2}\ge 0', r'\Rightarrow x\in ' + result]
    assert html.li.find_all(recursive=False)[-1].name == 'br'


def test_previously_uploaded_trivial_diagrams_are_removed_and_not_reuploaded():
    context = FIXTURES['185']
    gateway = AnnotatingGateway(context)
    condition = next(s for s in context['normalized_content']['sections'] if s['key']=='condition')
    options, _ = _condition_options(condition['html'])
    import hashlib
    for index, formula in enumerate(options,1):
        choice = solve_choice(formula)
        svg = render_quadratic_sign_chart_svg(choice.roots,choice.intervals)
        asset = gateway.upload_solution_asset(source_problem_id='185',svg_bytes=svg,sha256=hashlib.sha256(svg).hexdigest())
        gateway.context['normalized_content']['assets'].append({'asset_key':f'generated_quadratic_option_{index}',
                                                               'asset_id':asset['source_asset_id'],'url':asset['url']})
    record = _prepared_record(gateway, {'problem_id':context['problem_id'],'source_problem_id':'185'}, None, RULE)
    removed = [t['transformation_target_id'] for t in record['transformations'] if t['operation']=='remove']
    assert removed == ['asset:generated_quadratic_option_1','asset:generated_quadratic_option_3']
    assert _apply_record(gateway, record, None, RULE)['status'] == 'applied'
    assert _apply_record(gateway, record, None, RULE)['status'] == 'already_complete'
    assert gateway.uploads == 4
    assert len(diagram_specs(gateway.context)) == 2
    assert {a['asset_key'] for a in gateway.context['normalized_content']['assets']} == {
        'image_1','generated_quadratic_option_2','generated_quadratic_option_4'}


@pytest.mark.parametrize('sid,keys', [('185',['generated_quadratic_option_2','generated_quadratic_option_4']),
                                    ('314596',['generated_quadratic_option_1','generated_quadratic_option_3']),
                                    ('341520',['generated_quadratic_option_1','generated_quadratic_option_4'])])
def test_asset_positions_are_compressed_after_removing_trivial_options(sid,keys):
    gateway = AnnotatingGateway(FIXTURES[sid])
    record = _prepared_record(gateway, {'problem_id':gateway.context['problem_id'],'source_problem_id':sid},None,RULE)
    additions = [t['value'] for t in record['transformations'] if t['transformation_target_id'].startswith('asset:') and t['operation']=='add']
    assert [t['asset_key'] for t in additions] == keys
    assert [t['position'] for t in additions] == [0,1]
    result = _apply_record(gateway, record,None,RULE)
    assert result['status']=='applied',result


def test_answer_is_computed_independently_of_saved_answer():
    context = deepcopy(FIXTURES['333004'])
    next(s for s in context['normalized_content']['sections'] if s['key'] == 'answer')['html'] = '<p>4</p>'
    plan = build_context_repair_plan(context)
    assert plan.answer == '2'
    assert any(t['transformation_target_id'] == 'section:answer:1' for t in plan.transformations)


@pytest.mark.parametrize('sid', sorted(FIXTURES))
def test_entire_audited_group_converges_in_shared_runtime(sid):
    context = FIXTURES[sid]
    gateway = AnnotatingGateway(context)
    record = _prepared_record(gateway, {'problem_id':context['problem_id'], 'source_problem_id':sid}, None, RULE)
    assert record['status'] == 'prepared', record
    assert record['expected_answer'] in {'1','2','3','4'}
    assert _apply_record(gateway, record, None, RULE)['status'] == 'applied'
    assert _apply_record(gateway, record, None, RULE)['status'] == 'already_complete'
    assert gateway.writes == 1 and gateway.uploads == len(record['generated_diagrams'])
    condition = next(s for s in gateway.context['normalized_content']['sections'] if s['key'] == 'condition')
    options, pending_repair = _condition_options(condition['html'])
    assert len(options) == 4 and pending_repair is None


def test_actual_formula_drift_is_not_hidden_by_readback_canonicalization():
    context = FIXTURES['333004']
    gateway = AnnotatingGateway(context)
    record = _prepared_record(gateway, {'problem_id':context['problem_id'], 'source_problem_id':'333004'}, None, RULE)
    assert _apply_record(gateway, record, None, RULE)['status'] == 'applied'
    solution = next(s for s in gateway.context['normalized_content']['sections'] if s['key']=='solution')
    solution['html'] = solution['html'].replace('x(x-6)', 'x(x-7)')
    assets = tuple({'asset_key':a['asset_key'],'source_asset_id':a['asset_id'],'url':a['url']}
                   for a in gateway.context['normalized_content']['assets'] if a['asset_key'].startswith('generated_quadratic_option_'))
    pending = build_context_repair_plan(gateway.context, generated_solution_assets=assets)
    assert [t['transformation_target_id'] for t in pending.transformations] == ['section:solution:1']


@pytest.mark.parametrize('formula', [r'x^{2}-4\le0', r'x^{2}-4\leq0', r'x^{2}-4\leqslant0'])
def test_nonstrict_latex_variants_have_closed_boundaries(formula):
    result = solve_choice(formula).intervals
    assert result == (Interval(Fraction(-2), Fraction(2), True, True),)


def test_plain_text_formula_repairs_are_approved_and_preserve_choice_order():
    context = FIXTURES['319773']
    plan = build_context_repair_plan(context)
    assert plan.answer == '2'
    condition = next(t['value']['html'] for t in plan.transformations if t['transformation_target_id']=='section:condition:1')
    options, pending = _condition_options(condition)
    assert options == ('x^{2}-6x<0','x^{2}-6x>0','x^{2}-36<0','x^{2}-36>0')
    assert pending is None


@pytest.mark.parametrize('formula,closed', [('x^{2}-4<=0',True),('x^{2}-4>=0',True),
                                         ('x^{2}-4<0',False),('x^{2}-4>0',False),
                                         ('x^{2}-4x+4>=0',True),('x^{2}-4x+4<=0',True)])
def test_sign_chart_markers_follow_inclusion_in_solution(formula,closed):
    choice = solve_choice(formula)
    root = ET.fromstring(render_quadratic_sign_chart_svg(choice.roots,choice.intervals))
    circles = root.findall('{http://www.w3.org/2000/svg}circle')
    assert circles
    assert all(c.get('fill') == ('#000000' if closed else 'white') for c in circles)


@pytest.mark.parametrize('mutation', ['unknown', 'formula', 'diagram'])
def test_unreviewed_or_changed_input_never_gets_a_plan(mutation):
    context = deepcopy(FIXTURES['333004'])
    if mutation == 'unknown':
        context['problem_id'] = 'unreviewed'
    else:
        section = next(s for s in context['normalized_content']['sections'] if s['key'] == 'condition')
        section['html'] = section['html'].replace('6x', '7x') if mutation == 'formula' else section['html'].replace('d64f59fc', 'bad-id')
    with pytest.raises(ValueError):
        build_context_repair_plan(context)


@pytest.mark.parametrize('b,c', [(0,-4), (0,4), (-6,0), (-36,0), (6,0), (0,0), (-4,4), (-5,6)])
@pytest.mark.parametrize('sign', ['<','>','<=','>='])
def test_intervals_agree_with_polynomial_at_boundaries_and_between_them(b,c,sign):
    latex = 'x^{2}' + (f'{b:+}x' if b else '') + (f'{c:+}' if c else '') + sign + '0'
    choice = solve_choice(latex)
    for numerator in range(-80, 81):
        x = Fraction(numerator, 2)
        polynomial = x*x+b*x+c
        expected = {'<':polynomial < 0, '>':polynomial > 0, '<=':polynomial <= 0, '>=':polynomial >= 0}[sign]
        actual = any((i.lower is None or x > i.lower or x == i.lower and i.lower_closed)
                     and (i.upper is None or x < i.upper or x == i.upper and i.upper_closed) for i in choice.intervals)
        assert actual == expected


@pytest.mark.parametrize('formula', [r'2x^{2}-4\lt0',r'x^{2}-2\gt0',r'x^{2}-4<=0<1',r'x^{3}-4\lt0'])
def test_unsupported_math_is_rejected(formula):
    with pytest.raises(ValueError):
        solve_choice(formula)


def test_svg_union_has_unshaded_gap_and_open_boundaries():
    svg = ET.fromstring(render_quadratic_sign_chart_svg((Fraction(0), Fraction(6)), (Interval(upper=Fraction(0)), Interval(lower=Fraction(6)))))
    ns = {'s':'http://www.w3.org/2000/svg'}
    assert len(svg.findall('s:circle',ns)) == 2
    assert all(c.get('fill') == 'white' for c in svg.findall('s:circle',ns))
    hatch = [n for n in svg.findall('s:line',ns) if n.get('stroke') == '#143B8F']
    assert hatch
    assert all(float(n.get('x1')) <= 66.955 or float(n.get('x2')) >= 119.057 for n in hatch)


@pytest.mark.parametrize('negative', [False, True])
def test_all_three_regions_have_arcs_and_signs_with_only_matching_regions_shaded(negative):
    choice = solve_choice('x^{2}-6x' + ('<0' if negative else '>0'))
    actual = render_quadratic_sign_chart_svg(choice.roots, choice.intervals)
    root = ET.fromstring(actual)
    ns = {'s':'http://www.w3.org/2000/svg'}
    assert len([p for p in root.findall('s:path',ns) if p.get('data-sign-interval') is not None]) == 3
    assert [t.text for t in root.findall('s:text',ns) if t.get('data-polynomial-sign')] == ['+', '−', '+']
    hatch = [n for n in root.findall('s:line',ns) if n.get('stroke') == '#143B8F']
    assert hatch
    if negative:
        assert all(66.955 <= float(n.get('x2')) < float(n.get('x1')) <= 119.057 for n in hatch)
    else:
        assert all(float(n.get('x1')) <= 66.955 or float(n.get('x2')) >= 119.057 for n in hatch)


@pytest.mark.parametrize('formula,signs', [('x^{2}+4<0',['+']), ('x^{2}+4>0',['+']),
                                        ('x^{2}-4x+4<0',['+','+']), ('x^{2}-4x+4>0',['+','+'])])
def test_no_real_roots_and_double_root_keep_correct_signs_even_for_empty_solution(formula,signs):
    choice = solve_choice(formula)
    root = ET.fromstring(render_quadratic_sign_chart_svg(choice.roots, choice.intervals))
    ns = {'s':'http://www.w3.org/2000/svg'}
    assert [t.text for t in root.findall('s:text',ns) if t.get('data-polynomial-sign')] == signs
    hatch = [n for n in root.findall('s:line',ns) if n.get('stroke') == '#143B8F']
    assert bool(hatch) == bool(choice.intervals)


def test_group_185_routes_to_new_rule():
    profile = all_group_profiles()['185']
    assert profile.content_rule_key == RULE
    assert profile.source_group_id == 'fa22c171-2a79-4914-809f-2147181bf88c'
    assert profile.existing_solution_policy == 'rewrite'
