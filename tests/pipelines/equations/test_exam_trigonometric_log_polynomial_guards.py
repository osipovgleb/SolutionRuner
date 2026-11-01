"""Unsupported log powers and cancelled denominators cannot leak roots or methods."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_log_polynomial import (
    branches,
    compile_polynomial,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_selection import KEY
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA=json.loads((Path(__file__).parent/'fixtures/category_14_trigonometric_log_polynomials.json').read_text())


def source(key):return next(c for c in DATA['cases'] if c['task']==key)


def prototype(key):return section(source(key)['context']['normalized_content'],'solution')['html']


@pytest.mark.parametrize('formula',[
 r'\log_1^2(\sin x)+\log_1(\sin x)=0',
 r'\log_{\tg x}^2(\sin x)+\log_{\tg x}(\sin x)=0',
 r'\log_2^3(\sin x)+\log_2(\sin x)=0',
 r'\log_2^2(\sin x)-2=0',
 r'\log_2^2(\sin x)+\log_3(\sin x)=0',
 r'\log_2^2(\sin x)+\log_2(\cos x)=0',
 r'(\sin x)\log_2^2(\cos x)+\log_2(\cos x)=0',
 r'\log_2^2(\sin^3x)+\log_2(\sin^3x)=0',
 r'\log_2^2(\sin^2x+\cos^2x)+\log_2(\sin^2x+\cos^2x)=0',
 r'\frac{\log_2^2(\sin x)}{\log_2(\sin x)}=0',
])
def test_unreviewed_bases_levels_arguments_and_log_denominators_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula,r'[0;2\pi]',(sp.S.Zero,2*sp.pi,True,True),prototype('525117'))


def test_a_cancelled_original_nonlog_denominator_is_still_checked():
    formula=r'\frac{(2\cos x-\sqrt{3})(\log_2^2(\sin x)+\log_2(\sin x))}{2\cos x-\sqrt{3}}=0'
    c=compile_polynomial(formula,prototype('517180'))
    assert c is not None and len(c.poles)==1
    residues=tuple(sorted({q for b in branches(c) for q in b.residues}))
    assert residues==(sp.Rational(1,2),sp.Rational(5,6))
    assert sp.Rational(1,6) not in residues


@pytest.mark.parametrize('key',['514446','514540'])
def test_a_compatible_existing_line_cannot_be_replaced_with_a_generated_duplicate(key):
    c=source(key);handler=get_handler(get_group_profile(c['group']).content_rule_key)
    with pytest.raises(UnsupportedCondition):
        handler.plan(PlanInput(c['context'],parent_solution_html=prototype('514446'),generated_solution_assets=({'asset_key':KEY,'sha256':'0'*64,'source_asset_id':'unknown','url':'/assets/unknown'},)))


def test_both_selection_methods_are_required_by_the_registered_source_inventory():
    c=source('514446');handler=get_handler(get_group_profile(c['group']).content_rule_key)
    parent=prototype('514446').replace('При\u00adве\u00adдем дру\u00adгое ре\u00adше\u00adние пунк\u00adта','Удалён способ')
    # Remove the actual heading independent of soft-hyphen placement.
    from bs4 import BeautifulSoup

    soup=BeautifulSoup(parent,'html.parser')
    for n in soup.find_all(string=True):
        if 'другое решение' in str(n).replace('\xad','').lower():n.replace_with('Способ удалён.')
    with pytest.raises(UnsupportedCondition):
        handler.plan(PlanInput(c['context'],parent_solution_html=str(soup)))


def test_a_wrong_prepared_parent_reference_or_extra_asset_is_rejected():
    c=source('514540');handler=get_handler(get_group_profile(c['group']).content_rule_key)
    context=deepcopy(c['context'])
    context['normalized_content']['assets'].append({'asset_key': KEY,'asset_id': 'wrong','url': '/assets/wrong','kind': 'ordinary_image'})
    with pytest.raises(UnsupportedCondition):handler.plan(PlanInput(context,parent_solution_html=prototype('514446')))


def test_an_empty_or_unknown_parent_cannot_choose_a_new_substitution_method():
    with pytest.raises(UnsupportedCondition):
        compile_polynomial(r'2\log_2^2(2\cos x)-9\log_2(2\cos x)+4=0','<p>Найдите приближённое решение другим способом.</p>')
