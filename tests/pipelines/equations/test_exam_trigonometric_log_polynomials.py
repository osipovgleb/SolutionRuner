"""Original log polynomials, parent substitutions and both interval-selection methods."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    LINES,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_selection import KEY
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads((Path(__file__).parent/'fixtures/category_14_trigonometric_log_polynomials.json').read_text())
CASES = DATA['cases']
R = sp.Rational
EXPECTED = {
 '514446':((R(1,6),R(11,6)),(R(11,6),R(13,6))),
 '514526':((R(1,3),R(5,3)),(R(5,3),)),
 '514533':((R(1,4),R(7,4)),(-R(7,4),)),
 '514540':((R(1,6),R(11,6)),(R(11,6),R(13,6))),
 '525117':((R(1,4),R(7,4)),(-R(7,4),)),
 '525392':((R(1,4),R(3,4)),(-R(5,4),)),
 '525138':((R(1,4),R(3,4)),(R(3,4),)),
 '526013':((R(1,3),R(2,3)),(R(8,3),)),
 '517180':((R(1,2),R(5,6)),(R(1,2),R(5,6))),
 '517218':((R(1,6),R(1,2)),(R(1,6),R(1,2))),
 '517476':((R(3,4),R(5,4)),(-R(5,4),-R(3,4))),
 '639674':((R(3,4),R(5,4)),(-R(5,4),-R(3,4))),
 '558618':((R(1,3),R(2,3)),(-R(5,3),)),
 '656193':((R(5,6),R(7,6)),(R(17,6),R(19,6))),
}
ORIGINAL = {
 '514446':(3,(2,-5,2),'cos',2,0,None),'514540':(3,(2,-5,2),'cos',2,0,None),
 '514526':(4,(2,-7,3),'cos',4,0,None),
 '514533':(2,(2,-9,4),'cos',2,0,None),'525117':(2,(2,-9,4),'cos',2,0,None),
 '525392':(.5,(2,7,3),'sin',2,0,None),'525138':(2,(2,-5,2),'sin',2,0,None),
 '526013':(.75,(2,3,-2),'sin',1,0,None),
 '517180':(2,(1,1,0),'sin',1,0,-math.sqrt(3)),
 '517218':(2,(1,1,0),'sin',1,0,math.sqrt(3)),
 '558618':(3,(2,-7,6),'sin',8,-math.sqrt(3),None),
 '656193':(3,(2,-9,4),'cos',8,5*math.sqrt(3),None),
}


def case(key):return next(c for c in CASES if c['task']==key)


def parent(c):return section(case(c['group'])['context']['normalized_content'],'solution')['html']


def analysis(c,context=None):
    _,f,i,b = read(context or c['context'])
    return analyze(f,i,b,parent(c))


def generated(c,context=None):
    h = get_handler(get_group_profile(c['group']).content_rule_key)
    return tuple({**s,'source_asset_id':'preview-'+s['sha256'][:16],'url':'/assets/preview-'+s['sha256'][:16]} for s in h.diagram_specs(context or c['context']))


def plan(c,context=None,assets=None):
    ctx = context or c['context']
    return get_handler(get_group_profile(c['group']).content_rule_key).plan(PlanInput(ctx,parent_solution_html=parent(c),generated_solution_assets=generated(c,ctx) if assets is None else assets))


def formulas(html):return [n['data-inline-latex'] for n in BeautifulSoup(html,'html.parser').select('[data-inline-latex]')]


def original_zero(key,q):
    x = float(q)*math.pi
    si,co = math.sin(x),math.cos(x)
    if key in ('517476','639674'):
        argument = math.cos(2*x)-9*math.sqrt(2)*co-8
        return argument>1e-9 and abs(math.log(argument,13))<1e-8
    base,coeffs,fn,scale,shift,pole = ORIGINAL[key]
    argument = scale*(si if fn=='sin' else co)+shift
    if argument<=1e-9 or (pole is not None and abs(2*co+pole)<1e-9):return False
    value = math.log(argument,base)
    a,b,c = coeffs
    return abs(a*value*value+b*value+c)<1e-8


@pytest.mark.parametrize('c',CASES,ids=lambda c:c['task'])
def test_complete_and_selected_roots_follow_the_original_logarithms_and_poles(c):
    a = analysis(c)
    full,selected = EXPECTED[c['task']]
    assert select(a.series,(0,2,True,False))[0]==full
    assert a.selected==selected
    for q in (*full,*selected):assert original_zero(c['task'],q)
    for k in range(-144,145):
        q=R(k,24)
        assert original_zero(c['task'],q)==(q%2 in full),(c['task'],q)


@pytest.mark.parametrize('g',DATA['groups'],ids=lambda g:g['key'])
def test_exact_profiles_extend_the_common_runner(g):
    p=get_group_profile(g['key'])
    assert (p.source_group_id,p.snapshot_theme_id,p.theme_order_index,p.group_order_index)==(g['uuid'],g['theme_uuid'],10,g['order'])
    assert p.content_rule_key=='exam-trigonometric-polynomial-circle'


@pytest.mark.parametrize('c',CASES,ids=lambda c:c['task'])
def test_saved_answers_are_unused_and_local_replay_preserves_the_original_inputs(c):
    before=deepcopy(c['context']);p=plan(c);ctx=deepcopy(before)
    for key in ('answer','solution'):section(ctx['normalized_content'],key)['html']='<p>Не использовать сохранённые значения.</p>'
    assert plan(c,ctx)==p
    for t in p.transformations:
        key=t['transformation_target_id']
        assert not key.startswith('section:condition')
        if key.startswith('asset:'):
            assert c['group']=='514446' and c['task']!='514446' and t['operation']=='add'
            ctx['normalized_content']['assets'].append(t['value'])
        else:next(s for s in ctx['normalized_content']['sections'] if s['transformation_target_id']==key).update(t['value'])
    assert plan(c,ctx).transformations==()
    assert section(ctx['normalized_content'],'condition')==section(before['normalized_content'],'condition')
    assert ctx['normalized_content']['assets'][:len(before['normalized_content']['assets'])]==before['normalized_content']['assets']
    assert c['context']==before


@pytest.mark.parametrize('c',CASES,ids=lambda c:c['task'])
def test_every_original_svg_has_exact_bytes_and_mathematically_valid_native_markers(c):
    for asset in c['context']['normalized_content']['assets']:
        aid=asset['asset_id'];entry=(CIRCLES|LINES)[aid]
        raw=gzip.decompress((DIRECTORY/(aid+'.svgz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==entry['sha256']
        root=ET.fromstring(raw);paths={n.get('d') for n in root.iter() if n.tag.endswith('path')}
        if aid in LINES:
            assert entry['selected']==['11/6','13/6'] and entry['metric_scale'] is False
            assert all(any(n.tag.endswith('line') and n.attrib==tick for n in root.iter()) for tick in entry['native_ticks'])
            assert all(m['path_d'] in paths for m in entry['interval_markers'])
            continue
        assert entry['native_circle_path'] in paths
        for point in (*entry['green_markers'],*entry['excluded_markers']):
            assert point['path_d'] in paths
            q=R(point['angle']);cx,cy,radius=entry['circle'];radius=point.get('radius',radius)
            assert math.hypot(point['x']-cx-radius*math.cos(float(q)*math.pi),point['y']-cy+radius*math.sin(float(q)*math.pi))<5
            assert original_zero(c['task'],q)==(point in entry['green_markers'])


@pytest.mark.parametrize('key',['514446','514526','514533','514540'])
def test_both_parent_selection_methods_and_their_figures_remain_in_part_b(key):
    c=case(key);a=analysis(c);assert a.log_polynomial.alternative_selection
    soup=BeautifulSoup(plan(c).solution_html,'html.parser');part=soup.select_one('li[data-list-marker="б)"]');images=part.find_all('img')
    assert len(images)==2 and not soup.select('li[data-list-marker="а)"] img')
    assert images[0]['data-asset-key']==('image_1' if key=='514446' else KEY)
    assert images[1]['data-asset-key']==('image_2' if key=='514446' else 'image_1')
    html=str(part);assert html.index(str(images[0]))<html.index('Приведём другое решение пункта б)')<html.index(str(images[1]))


def test_identical_child_reuses_the_existing_parent_number_line_without_a_duplicate_svg():
    c=case('514540');assert generated(c)==()
    added=[t for t in plan(c).transformations if t['transformation_target_id']=='asset:'+KEY]
    assert len(added)==1 and added[0]['value']['asset_id']=='4a63e553-97f7-4c51-9da1-2dea4db3c135'
    assert '/assets/4a63e553-97f7-4c51-9da1-2dea4db3c135' in added[0]['value']['html']


@pytest.mark.parametrize('key',['514526','514533'])
def test_new_child_number_lines_have_exact_ordered_ticks_bounds_and_root_groups(key):
    c=case(key);a=analysis(c);specs=generated(c);assert len(specs)==1
    root=ET.fromstring(specs[0]['svg_text']);entry=CIRCLES[c['context']['normalized_content']['assets'][0]['asset_id']]['log_selection_line']
    assert specs[0]['sha256']==hashlib.sha256((DIRECTORY/entry['file']).read_bytes()).hexdigest()
    ticks=sorted([n for n in root.iter() if n.get('data-angle')],key=lambda n:float(n.get('cx',n.get('x1','0'))))
    values=[R(n.get('data-angle')) for n in ticks];assert values==sorted(set(values))
    assert {R(n.get('data-angle')) for n in ticks if n.get('data-role')=='boundary'}==set(a.bounds[:2])
    actual=tuple(q for q in values if a.bounds[0]<=q<=a.bounds[1] and q%2 in a.residues)
    assert actual==a.selected
    assert {str(k) for k in entry['groups']}=={n.get('data-latex')[2:] for n in root.iter() if (n.get('data-latex') or '').startswith('k=')}
    bad=list(specs);bad[0]={**bad[0],'sha256':'0'*64}
    with pytest.raises(UnsupportedCondition):plan(c,assets=tuple(bad))


def test_less_than_one_bases_keep_the_parent_argument_level_order():
    assert analysis(case('525392')).log_polynomial.levels==(-R(1,2),-sp.Integer(3))
    assert analysis(case('526013')).log_polynomial.levels==(R(1,2),-sp.Integer(2))
    assert analysis(case('514446')).log_polynomial.levels==(sp.Integer(2),R(1,2))
    html=plan(case('525392')).solution_html
    assert any(r'\left(\frac{1}{2}\right)^' in f for f in formulas(html))


def test_factoring_before_y_and_the_original_affine_denominator_are_preserved():
    c=case('517180');a=analysis(c);html=plan(c).solution_html;f=formulas(html)
    assert a.log_polynomial.substitution=='y' and a.log_polynomial.factor_before
    factor_index=next(i for i,x in enumerate(f) if x.count(r'\log_{2}')==2 and x.endswith('=0'))
    assert factor_index<next(i for i,x in enumerate(f) if x.startswith('y='))
    assert R(1,6) not in a.residues and R(5,6) in a.residues
    assert analysis(case('517218')).residues==(R(1,6),R(1,2))
    assert 'не подходит' in html


def test_bare_log_zero_precedes_cosine_double_angle_and_the_later_cosine_substitution():
    a=analysis(case('517476'));f=formulas(plan(case('517476')).solution_html)
    assert a.log_polynomial.substitution is None and a.log_polynomial.trig_substitution=='t'
    arg=next(i for i,x in enumerate(f) if r'\cos2x' in x and x.endswith('=1'))
    identity=next(i for i,x in enumerate(f) if x.startswith(r'\cos(2x)='))
    substitution=next(i for i,x in enumerate(f) if x.startswith('t=') and r'\cos' in x)
    assert arg<identity<substitution
    assert r'\sqrt{242}=11 \sqrt{2}' in f
    assert a.parameter=='n'


def test_direct_logarithmic_quadratic_does_not_introduce_the_internal_dummy_variable():
    a=analysis(case('656193'));f=formulas(plan(case('656193')).solution_html)
    assert a.log_polynomial.substitution is None
    assert not any(x.startswith(('t=','l=')) for x in f)
    assert analysis(case('558618')).log_polynomial.discriminant
    assert any(x.endswith('=1') and x.startswith('D=') for x in formulas(plan(case('558618')).solution_html))


@pytest.mark.parametrize('c',CASES,ids=lambda c:c['task'])
def test_unknown_asset_and_unrecognized_extra_instruction_fail_closed(c):
    context=deepcopy(c['context']);context['normalized_content']['assets'][0]['asset_id']='unknown'
    with pytest.raises(UnsupportedCondition):plan(c,context)
    context=deepcopy(c['context']);section(context['normalized_content'],'condition')['html']+='<p>Дополнительно вычислите произведение всех корней.</p>'
    with pytest.raises(UnsupportedCondition):plan(c,context)
