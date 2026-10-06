from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import pytest
from solution_runner.pipelines.core.content_runtime import _with_required_assets
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.function_graphs.fractional_hyperbola import ASSET_DIR,registry,graph_evidence,annotate,build_context_repair_plan
def materialize(ctx,changes):
    result=deepcopy(ctx)
    for change in changes:
        key=change['transformation_target_id'].split(':')[1]
        section=next((s for s in result['normalized_content']['sections'] if s['key']==key),None)
        if section is None:
            section={'key':key,'section_id':key+':1'}
            result['normalized_content']['sections'].append(section)
        section.update(change['value'])
    return result

FIXTURES=Path(__file__).parent/'fixtures'


def context(n):return _with_required_assets(json.loads((FIXTURES/f'{n}.json').read_text()),'hyperbola-shift-fractional-coefficient')
def plan(ctx,n):return build_context_repair_plan(ctx,condition_asset_bytes=(FIXTURES/f'{n}.svg').read_bytes(),current_asset_content_type='image/svg+xml')

@pytest.mark.parametrize('n,k',[(508993,1),(508994,-1),(508995,2),(508996,-2)])
def test_graph_and_two_methods_condition_repair_repeat(n,k):
    data=(FIXTURES/f'{n}.svg').read_bytes();facts=graph_evidence(data)
    assert facts['k']==k
    x,y=facts['point'];x2,y2=facts['second'];a,b=facts['a'],facts['b']
    assert (k*x+a)/(x+b)==y and (k*x2+a)/(x2+b)==y2
    ctx=context(n);before=deepcopy(ctx);result=plan(ctx,n)
    assert ctx==before and result.answer==str(k)
    updated=materialize(ctx,result.transformations)
    condition=next(s for s in updated['normalized_content']['sections'] if s['key']=='condition')
    assert r'f(x)=\frac{kx+a}{x+b}' in condition['html']
    assert BeautifulSoup(condition['html'],'html.parser').find('img')==BeautifulSoup(next(s['html'] for s in before['normalized_content']['sections'] if s['key']=='condition'),'html.parser').find('img')
    html=next(s['html'] for s in updated['normalized_content']['sections'] if s['key']=='solution')
    assert html.count('<img ')==2 and html.startswith('<section data-content-kind="solution" data-solution-title="Решение"><center><img ')
    assert r'kx+kb+a-kb' in html and r'k(x+b)+(a-kb)' in html
    assert r'\frac{k(x+b)}{x+b}+\frac{a-kb}{x+b}=k+\frac{a-kb}{x+b}' in html
    assert 'канонической для гиперболы' in html and 'сдвиг по вертикали' in html
    assert 'В исходной формуле' not in html
    assert 'Подставим три точки' in html
    assert 'C(' in html
    first=html.split('data-solution-title="Альтернативное решение"')[0]
    assert 'Вертикальная асимптота' not in first
    assert 'C=k' in html and 'B=b' in html and r'\iff' in html
    assert plan(updated,n).transformations==()

@pytest.mark.parametrize('asset_id,e',list(registry()['conditions'].items()))
def test_original_svg_is_preserved_except_annotation(asset_id,e):
    data=(ASSET_DIR/e['source_file']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==e['sha256']
    for method in ('points','offset'):
        output=(ASSET_DIR/e[method]['file']).read_bytes()
        assert output==annotate(data,method)
        start=output.index(b'<g data-role="fractional-hyperbola-overlay">');end=output.index(b'</g>',start)+4
        assert output[:start]+output[end:]==data
        assert hashlib.sha256(output).hexdigest()==e[method]['sha256']
        root=ET.fromstring(output)
        assert root.attrib==ET.fromstring(data).attrib
        assert len(list(root)[-1].findall('{http://www.w3.org/2000/svg}circle'))==(3 if method=='points' else 1)


def test_disagreeing_point_fails_closed():
    data=(FIXTURES/'508994.svg').read_bytes().replace(b'cy="139.7665"',b'cy="159.7335"')
    with pytest.raises(ContentPlanError,match='disagree'):graph_evidence(data)


def test_wrong_question_fails_closed():
    ctx=context(508993);condition=next(s for s in ctx['normalized_content']['sections'] if s['key']=='condition');condition['html']=condition['html'].replace('Най\u00adди\u00adте <i>k</i>','Найдите <i>x</i>')
    with pytest.raises(ContentPlanError,match='question'):plan(ctx,508993)


@pytest.mark.parametrize('sought,expected',[('a','9'),('b','4'),('k','1')])
def test_requested_original_coefficient_is_recovered_from_canonical_form(sought,expected):
    ctx=context(508993)
    condition=next(s for s in ctx['normalized_content']['sections'] if s['key']=='condition')
    condition['html']=condition['html'].replace('Най\u00adди\u00adте <i>k</i>',f'Найдите <i>{sought}</i>')
    result=plan(ctx,508993)
    assert result.answer==expected
    updated=materialize(ctx,result.transformations)
    html=next(s['html'] for s in updated['normalized_content']['sections'] if s['key']=='solution')
    assert r'f(x)=k+\frac{a-kb}{x+b}=C+\frac{A}{x+B}=\frac{A}{x+B}+C' in html
    assert 'Подставим эти обозначения' in html
    assert r'f(x)=\frac{5}{x+4}+1' in html
    if sought=='a':assert r'a=A+CB=5+1\cdot 4=9' in html
    assert plan(updated,508993).transformations==()


def test_three_unknowns_are_solved_with_explicit_elimination_steps():
    result=plan(context(508993),508993)
    html=next(t['value']['html'] for t in result.transformations if t['transformation_target_id'].startswith('section:solution'))
    first=BeautifulSoup(html,'html.parser').find('section')
    formulas=[node['data-inline-latex'] for node in first.select('[data-inline-latex]')]
    assert any('6(-3+b)=-3k+a' in f for f in formulas)
    assert any('-18+6b=-3k+a' in f for f in formulas)
    assert r'2k-10b=-38\iff k-5b=-19' in formulas
    assert r'-4k-4b=-20\iff k+b=5' in formulas
    assert r'-6b=-24\iff b=4' in formulas
    assert r'k+4=5\iff k=1' in formulas
    assert r'-3+a-24=-18\iff a=-18+3+24=9' in formulas
    assert 'Вычтем второе уравнение из первого' in first.get_text()
    assert 'Вычтем третье уравнение из первого' in first.get_text()
