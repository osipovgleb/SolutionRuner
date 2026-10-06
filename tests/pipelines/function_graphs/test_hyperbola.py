from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.function_graphs.hyperbola import build_context_repair_plan, graph_facts

FIXTURES = Path(__file__).parent / 'fixtures'


def context(source_id):
    from solution_runner.pipelines.core.content_runtime import _with_required_assets
    ctx = json.loads((FIXTURES / f'{source_id}.json').read_text())
    return _with_required_assets(ctx, 'hyperbola-shift-value' if source_id < 508961 else 'hyperbola-shift-argument')


def svg(source_id):
    return (FIXTURES / f'{source_id}.svg').read_bytes()


def plan(ctx, source_id, mime='image/svg+xml'):
    return build_context_repair_plan(ctx, condition_asset_bytes=svg(source_id),
        current_asset_content_type=mime, mode='value' if source_id < 508961 else 'argument')


def materialize(ctx, changes):
    result = deepcopy(ctx)
    for change in changes:
        key = change['transformation_target_id'].split(':')[1]
        section = next((s for s in result['normalized_content']['sections'] if s['key'] == key), None)
        if section is None:
            section = {'key':key, 'section_id':f'{key}:1'}
            result['normalized_content']['sections'].append(section)
        section.update(change['value'])
    return result


@pytest.mark.parametrize('source_id,expected', [(508951, '0,75'), (508952, '-2,96'),
    (508953, '11'), (508961, '-15'), (508962, '-20'), (508963, '-0,25')])
def test_saved_tasks_two_methods_assets_and_repeat(source_id, expected):
    ctx = context(source_id)
    before = deepcopy(ctx)
    result = plan(ctx, source_id)
    assert result.answer == expected
    assert not result.warnings
    assert ctx == before
    assert all(t['transformation_target_id'].startswith('section:') for t in result.transformations)
    updated = materialize(ctx, result.transformations)
    assert updated['normalized_content']['assets'] == ctx['normalized_content']['assets']
    for key in ('condition',):
        old = next(s for s in ctx['normalized_content']['sections'] if s['key'] == key)
        new = next(s for s in updated['normalized_content']['sections'] if s['key'] == key)
        assert old['asset_keys'] == new['asset_keys']
    html = next(s['html'] for s in updated['normalized_content']['sections'] if s['key'] == 'solution')
    assert html.startswith('<section data-content-kind="solution" data-solution-title="Решение"><center><img ')
    assert html.index('<img ') < html.index('Возьмём на графике две точки:')
    assert 'Подстановка двух точек' not in html
    assert 'data-solution-title="Альтернативное решение"' in html
    assert html.count('<img ') == 2
    assert 'По обратной пропорциональности' not in html
    assert r'\Rightarrow k=' in html
    assert '<center><p><span data-formula-render-mode="display"' in html
    assert 'Красный горизонтальный отрезок' in html
    assert 'сдвинут на' in html
    assert 'Умножим каждое уравнение' not in html
    assert r'\iff' in html
    assert 'data-formula-render-mode="display"' in html
    assert 'четвертях относительно асимптот' in html
    assert 'y=k/x+a' not in html
    if source_id == 508951:
        assert r'f(-12)=\frac{3}{-12}+1=-\frac{1}{4}+1=\frac{3}{4}=0{,}75' in html
        assert 'k&gt;0' in html and 'k=+3' in html
        assert '+(1)' not in html and '(3)a' not in html
    assert plan(updated, source_id).transformations == ()
    stored_solution = next(s for s in updated['normalized_content']['sections'] if s['key']=='solution')
    stored_solution['html'] = stored_solution['html'].replace(' src="/assets/', ' data-transformation-target-id="asset:readback-annotation" src="/assets/')
    assert plan(updated, source_id).transformations == ()


@pytest.mark.parametrize('source_id', [508951, 508952, 508953, 508961, 508962, 508963])
def test_non_svg_warns_and_continues_and_is_repeatable(source_id):
    ctx = context(source_id)
    result = plan(ctx, source_id, 'image/png')
    assert result.warnings and 'не SVG' in result.warnings[0]
    assert result.answer == plan(ctx, source_id).answer
    updated = materialize(ctx, result.transformations)
    assert plan(updated, source_id, 'image/png').transformations == ()


def test_existing_solution_image_is_preserved_exactly():
    ctx = context(508951)
    section = next(s for s in ctx['normalized_content']['sections'] if s['key'] == 'solution')
    image = '<img src="/assets/shared" data-asset-key="diagram" alt="Схема" />'
    section['html'] += image
    section['asset_keys'] = ['diagram']
    result = plan(ctx, 508951)
    change = next(t for t in result.transformations if t['transformation_target_id'] == 'section:solution:1')
    assert image in change['value']['html']
    assert change['value']['asset_keys'][0] == 'diagram'
    assert len(change['value']['asset_keys']) == 3


@pytest.mark.parametrize('source_id,k,a,x,y', [(508951,3,1,3,2), (508952,2,-3,-2,-4), (508953,4,-1,1,3)])
def test_graph_evidence(source_id,k,a,x,y):
    assert graph_facts(svg(source_id)) == tuple(map(Fraction, (k,a,x,y)))


def test_missing_graph_marker_fails_closed():
    data = svg(508951).replace(b'<circle ', b'<ellipse ')
    with pytest.raises(ContentPlanError, match='marked point'):
        build_context_repair_plan(context(508951), condition_asset_bytes=data,
            current_asset_content_type='image/svg+xml', mode='value')


def test_non_svg_without_numerical_evidence_fails_closed():
    ctx = context(508951)
    next(s for s in ctx['normalized_content']['sections'] if s['key']=='solution')['html'] = '<p>Нет данных</p>'
    with pytest.raises(ContentPlanError, match='verified numerical evidence'):
        plan(ctx, 508951, 'image/png')


@pytest.mark.parametrize('source_id,value', [(508951,'f(0)'), (508961, '1')])
def test_unattainable_request_fails_closed(source_id,value):
    ctx = context(source_id)
    section = next(s for s in ctx['normalized_content']['sections'] if s['key']=='condition')
    section['html'] = section['html'].replace('f(-12)',value) if source_id==508951 else section['html'].replace('0,8',value)
    with pytest.raises(ContentPlanError, match='domain/range'):
        plan(ctx,source_id)


@pytest.mark.parametrize('key,parent,mode', [('508951','de6bf611-902c-4952-b81c-e25323375982','value'),
    ('508961','371e1a7e-a8c1-4657-8b16-dc617e02ec7b','argument')])
def test_group_registration(key,parent,mode):
    profile = get_group_profile(key)
    assert profile.category_key == '12'
    assert profile.existing_solution_policy == 'rewrite'
    handler = get_handler(profile.content_rule_key)
    handler.validate()
    assert dict(handler.options) == {'mode':mode}
    assert handler.allow_non_svg_condition_asset
    assert context(int(key))['problem_id'] == parent


def test_runtime_non_svg_warning_is_in_manifest_without_writes():
    from types import SimpleNamespace
    from solution_runner.pipelines.core.content_runtime import _prepared_record, _condition_asset_bytes
    class Gateway:
        def get_problem_context(self, problem_id):
            return context(508951)
        def get_asset_metadata(self, asset_id):
            return {'asset_id':asset_id, 'content_type':'image/png'}
        def download_condition_asset(self, target):
            return SimpleNamespace(content_type='image/png',data=svg(508951))
    gateway = Gateway()
    record = _prepared_record(gateway,
        {'problem_id':context(508951)['problem_id'],'source_problem_id':'508951'},
        None, 'hyperbola-shift-value')
    assert record['status'] == 'prepared'
    assert record['expected_answer'] == '0,75'
    assert 'не SVG' in record['message']
    assert not any(t['transformation_target_id'].startswith('asset:') for t in record['transformations'])
    with pytest.raises(ContentPlanError, match='must be SVG'):
        _condition_asset_bytes(gateway, 'problem', 'source', 'coordinate-line-true-statement')


@pytest.mark.parametrize('source_id,expected', [(508987,'-19'),(508988,'38')])
def test_audited_horizontal_rasters_both_methods_and_repeat(source_id,expected):
    ctx = context(source_id)
    data = (FIXTURES / f'{source_id}.png').read_bytes()
    result = build_context_repair_plan(ctx,condition_asset_bytes=data,
        current_asset_content_type='image/png',mode='argument')
    assert result.answer == expected
    assert 'не SVG' in result.warnings[0]
    html = next(t['value']['html'] for t in result.transformations if t['transformation_target_id'].startswith('section:solution'))
    assert 'Подстановка двух точек' not in html
    assert 'Альтернативное решение' in html
    assert 'четвертях относительно асимптот' in html
    updated = materialize(ctx,result.transformations)
    assert updated['normalized_content']['assets'] == ctx['normalized_content']['assets']
    assert build_context_repair_plan(updated,condition_asset_bytes=data,
        current_asset_content_type='image/png',mode='argument').transformations == ()
    if source_id == 508987:
        assert '14' in result.warnings[1] and '-19' in result.warnings[1]
    with pytest.raises(ContentPlanError, match='audited numerical evidence'):
        build_context_repair_plan(ctx,condition_asset_bytes=data+b'changed',
            current_asset_content_type='image/png',mode='argument')


def test_retired_synthetic_graph_is_replaced_without_removing_editorial_images():
    from solution_runner.pipelines.function_graphs.diagrams import registry
    ctx=context(508951)
    old_id=registry()['retired_asset_ids'][0]
    ctx['normalized_content']['assets'].append({'asset_key':'old_graph','asset_id':old_id})
    section=next(s for s in ctx['normalized_content']['sections'] if s['key']=='solution')
    section['html']+='<img data-asset-key="old_graph" src="/assets/'+old_id+'"/>'
    section['asset_keys']=['old_graph']
    change=next(t for t in plan(ctx,508951).transformations if t['transformation_target_id']=='section:solution:1')
    assert old_id not in change['value']['html']
    assert 'old_graph' not in change['value']['asset_keys']


@pytest.mark.parametrize('source_id,mode,expected', [
    (508971,'value','0,15'),(508972,'value','-0,25'),(508973,'value','15'),
    (508974,'value','-0,1'),(508975,'value','0,12'),(508976,'value','0,25'),
    (508977,'value','0,4'),(508978,'value','-3,2'),(508979,'value','-0,2'),
    (508980,'value','-0,5'),(508981,'value','-0,24'),(508982,'value','-0,75'),
    (508983,'argument',None),(508984,'argument',None),(508985,'argument',None),
    (508986,'argument',None),(508989,'argument',None),(508990,'argument',None),
    (508991,'argument',None),(508992,'argument',None),(635859,'argument','38'),
    (635962,'argument','-19')])
def test_horizontal_groups_correct_condition_keep_graph_and_repeat(source_id,mode,expected):
    from solution_runner.pipelines.core.content_runtime import _with_required_assets
    from bs4 import BeautifulSoup
    ctx=json.loads((FIXTURES/f'{source_id}.json').read_text())
    if expected is None:
        expected=BeautifulSoup(next(s['html'] for s in ctx['normalized_content']['sections'] if s['key']=='answer'),'html.parser').get_text('',strip=True)
    ctx=_with_required_assets(ctx,'hyperbola-shift-horizontal-'+mode)
    result=build_context_repair_plan(ctx,condition_asset_bytes=svg(source_id),current_asset_content_type='image/svg+xml',mode=mode,horizontal_model=True)
    assert result.answer==expected
    updated=materialize(ctx,result.transformations)
    condition=next(s for s in updated['normalized_content']['sections'] if s['key']=='condition')
    assert r'f(x)=\frac{k}{x+a}' in condition['html']
    assert r'f(x)=\frac{k}{x}+a' not in condition['html']
    assert BeautifulSoup(condition['html'],'html.parser').find('img')==BeautifulSoup(next(s['html'] for s in ctx['normalized_content']['sections'] if s['key']=='condition'),'html.parser').find('img')
    solution=next(s for s in updated['normalized_content']['sections'] if s['key']=='solution')
    assert solution['html'].count('<img ')==2
    assert r'\iff' in solution['html']
    assert 'от вертикальной асимптоты' in solution['html']
    if source_id==635859:assert result.warnings and 'внешнюю' in result.warnings[0]
    assert not build_context_repair_plan(updated,condition_asset_bytes=svg(source_id),current_asset_content_type='image/svg+xml',mode=mode,horizontal_model=True).transformations


@pytest.mark.parametrize('source_id,expected',[(508987,'-19'),(508988,'38'),(635859,'38')])
def test_replaced_svg_conditions_have_annotated_solutions_without_warnings(source_id,expected):
    from bs4 import BeautifulSoup
    ctx=json.loads((FIXTURES/f'{source_id}-svg.json').read_text())
    data=(FIXTURES/f'{source_id}-svg.svg').read_bytes()
    assert b'<image ' not in data
    result=build_context_repair_plan(ctx,condition_asset_bytes=data,current_asset_content_type='image/svg+xml',mode='argument',horizontal_model=source_id==635859)
    assert result.answer==expected and not result.warnings and not result.transformations
    html=next(s['html'] for s in ctx['normalized_content']['sections'] if s['key']=='solution')
    assert len(BeautifulSoup(html,'html.parser').find_all('img'))==2
    assert 'Красный горизонтальный отрезок' in html
