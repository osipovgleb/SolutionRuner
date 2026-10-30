"""Exercise all audited neighboring groups, exact roots and server-style readback."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from bs4 import BeautifulSoup
from solution_runner.pipelines.core.content_runtime import _prepared_record,_apply_record
from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.equations.quadratic_interval_choices import (
    RULE,ASSET_KEY,solve_quadratic,parse_interval_option,build_context_repair_plan,diagram_specs,_polynomial,
)
from solution_runner.pipelines.equations.linear_system_intervals import Interval
from test_quadratic_inequality_choices import AnnotatingGateway

FIXTURES=json.loads((Path(__file__).parent/'fixtures/quadratic_interval_choices.json').read_text())
BLOCKED={'338678','480243'}


@pytest.mark.parametrize('sid',sorted(FIXTURES))
def test_every_neighbor_task_has_verified_single_write_and_no_second_upload(sid):
    context=FIXTURES[sid];gateway=AnnotatingGateway(context)
    initial_condition=deepcopy(next(s for s in gateway.context['normalized_content']['sections'] if s['key']=='condition'))
    child={'problem_id':context['problem_id'],'source_problem_id':sid}
    record=_prepared_record(gateway,child,None,RULE)
    if sid in BLOCKED:
        assert record['status']=='blocked',record
        assert _apply_record(gateway,record,None,RULE)['status']=='blocked'
        assert gateway.writes==gateway.uploads==0
        return
    assert record['status']=='prepared',record
    result=_apply_record(gateway,record,None,RULE)
    assert result['status']=='applied',result
    assert _apply_record(gateway,record,None,RULE)['status']=='already_complete'
    assert gateway.writes==gateway.uploads==1
    solution=next(s for s in gateway.context['normalized_content']['sections'] if s['key']=='solution')
    assert solution['asset_keys']==[ASSET_KEY]
    tree=BeautifulSoup(solution['html'],'html.parser')
    assert len(tree.find_all('img'))==1
    assert tree.find_all('span')[-1]['data-inline-latex'].startswith(r'x\in ')
    condition=next(s for s in gateway.context['normalized_content']['sections'] if s['key']=='condition')
    assert condition==initial_condition


@pytest.mark.parametrize('latex,roots,result',[
    (r'81x^{2}\lt 16',(Fraction(-4,9),Fraction(4,9)),(Interval(Fraction(-4,9),Fraction(4,9)),)),
    (r'6x-x^{2}\ge 0',(Fraction(0),Fraction(6)),(Interval(Fraction(0),Fraction(6),True,True),)),
    (r'-x^{2}-2x\le 0',(Fraction(-2),Fraction(0)),(Interval(upper=Fraction(-2),upper_closed=True),Interval(lower=Fraction(0),lower_closed=True))),
    (r'(2x-5)(x+3)\ge 0',(Fraction(-3),Fraction(5,2)),(Interval(upper=Fraction(-3),upper_closed=True),Interval(lower=Fraction(5,2),lower_closed=True))),
])
def test_exact_roots_and_sign_reversal(latex,roots,result):
    solved=solve_quadratic(latex)
    assert solved.choice.roots==roots
    assert solved.choice.intervals==result
    if latex==r'6x-x^{2}\ge 0':assert r'x^{2}-6x\le 0' in solved.stages


def test_decimal_coefficients_remain_exact_instead_of_rounding_through_float():
    assert _polynomial('0.10000000000000001*x^2') == (
        Fraction(0),Fraction(0),Fraction('0.10000000000000001'))


@pytest.mark.parametrize('formula',["__import__('os').system('x')<0",'x**99<0','x/(x-1)>0','x^3<0','x^2+1>0','x^2-2<0'])
def test_unsupported_syntax_and_nonrational_roots_block(formula):
    with pytest.raises((ValueError,SyntaxError)):
        solve_quadratic(formula)


@pytest.mark.parametrize('raw,expected',[
    (r'(-\infty;-1]\cup [0;+\infty)',(Interval(upper=Fraction(-1),upper_closed=True),Interval(lower=Fraction(0),lower_closed=True))),
    ('(− ∞; +∞)',(Interval(),)),('нет ре­ше­ний',()),
    (r'(-\frac{4}{9};\frac{4}{9})',(Interval(Fraction(-4,9),Fraction(4,9)),)),
])
def test_interval_choices_preserve_boundary_strictness(raw,expected):
    assert parse_interval_option(raw)==expected


def test_fraction_labels_are_svg_text_not_raw_tex():
    root=ET.fromstring(diagram_specs(FIXTURES['338497'])[0]['svg_text'])
    assert r'\frac' not in ''.join(root.itertext())
    labels=[n for n in root.iter() if n.get('data-root-fraction')]
    assert len(labels)==4
    assert [n.text for n in labels]==['4','9','4','9']


def test_saved_answer_does_not_choose_the_matching_option():
    context=deepcopy(FIXTURES['338497'])
    next(s for s in context['normalized_content']['sections'] if s['key']=='answer')['html']='<p>1</p>'
    assert build_context_repair_plan(context).answer=='4'


def test_changed_condition_is_blocked_before_assets_are_generated():
    context=deepcopy(FIXTURES['338497'])
    condition=next(s for s in context['normalized_content']['sections'] if s['key']=='condition')
    condition['html']=condition['html'].replace('81x','25x')
    with pytest.raises(ValueError,match='changed'):
        diagram_specs(context)


def test_all_fourteen_profiles_share_the_new_handler():
    keys=['311309','311310','311311','311385','311751','311781','338497','338499','338550','349532','350216','352247','369736','471238']
    for key in keys:
        assert all_group_profiles()[key].content_rule_key==RULE
