from copy import deepcopy

import pytest

from solution_runner.pipelines.equations.numeric_special_forms import build_power_product_plan
from solution_runner.pipelines.triangles.right.planner import RightTrianglePlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile


def context(formula, options=None, answer=''):
    intro = 'Найдите значение выражения' if options is None else 'Какое из данных ниже чисел является значением выражения'
    html = f'<p>{intro} <span data-inline-latex="{formula}"></span>{"." if options is None else "?"}</p>'
    if options is not None:
        html += '<table><tr>' + ''.join(
            f'<td>{index}) <span data-inline-latex="{option}"></span></td>'
            for index, option in enumerate(options, 1)
        ) + '</tr></table>'
    return {'normalized_content': {'format': 'teacherhelper-normalized', 'schema_version': 3,
            'assets': [], 'sections': [
                {'key': 'condition', 'section_id': 'condition:1', 'html': html},
                {'key': 'answer', 'section_id': 'answer:1', 'html': f'<p>{answer}</p>'},
            ]}}


def solution_html(plan):
    return next(change['value']['html'] for change in plan.transformations
                if change['value']['title'] == 'Решение')


def test_power_product_uses_parent_identities_and_compact_chain():
    plan = build_power_product_plan(context(r'4^{-10}\cdot (4^{3})^{4}'))
    assert plan.answer == '16'
    html = solution_html(plan)
    assert r'(a^{b})^{c}=a^{bc}' in html
    assert r'a^{b}\cdot a^{c}=a^{b+c}' in html
    assert r'4^{-10+12}' in html
    assert html.count('<center>') == 1


def test_choice_answer_is_option_number_not_expression_value():
    plan = build_power_product_plan(context(r'5^{-7}\cdot(5^{5})^{2}',
        ['1', r'\frac{1}{125}', '-125', '125'], answer='4'))
    assert plan.answer == '4'
    assert len(plan.transformations) == 1
    assert '=125' in solution_html(plan)


def test_negative_power_gives_exact_fraction_and_selects_its_option():
    plan = build_power_product_plan(context(r'3^{-11}\cdot(3^{5})^{2}',
        [r'\frac{1}{3}', '81', '-3', r'\frac{1}{81}']))
    assert plan.answer == '1'
    assert r'=\frac{1}{3}' in solution_html(plan)


@pytest.mark.parametrize('formula,options', [
    (r'4^{-10}\cdot(5^{3})^{4}', None),
    (r'4^{-10}+(4^{3})^{4}', None),
    (r'0^{-10}\cdot(0^{3})^{4}', None),
    (r'5^{-7}\cdot(5^{5})^{2}', ['125', '125', '1', '2']),
    (r'5^{-7}\cdot(5^{5})^{2}', ['1', '2', '3', '4']),
    (r'5^{-7}\cdot(5^{5})^{2}', ['1', '2', '125']),
    (r'5^{-7}\cdot(5^{5})^{2}', ['1', r'\frac{1}{0}', '3', '125']),
])
def test_unsupported_or_ambiguous_inputs_fail_closed(formula, options):
    with pytest.raises(RightTrianglePlanError):
        build_power_product_plan(context(formula, options))


def test_planner_is_idempotent_after_local_changes():
    source = context(r'4^{-10}\cdot(4^{3})^{4}')
    planned = build_power_product_plan(source)
    updated = deepcopy(source)
    for change in planned.transformations:
        key = change['transformation_target_id'].split(':')[1]
        sections = updated['normalized_content']['sections']
        sections[:] = [section for section in sections if section['key'] != key]
        sections.append(dict(change['value'], key=key, section_id=f'{key}:1'))
    assert build_power_product_plan(updated).transformations == ()


def test_355406_registration_preserves_parent_solution():
    profile = get_group_profile('355406')
    assert profile.source_group_id == '657276c7-62fc-4465-8317-1cc7fac564b6'
    assert profile.content_rule_key == 'numeric-power-of-power-product'
    assert profile.existing_solution_policy == 'rewrite'


def test_parent_solution_is_preserved_during_presentation_rewrite():
    source = context(r'4^{-10}\cdot(4^{3})^{4}', answer='16')
    parent_html = '<p>Оригинальное решение родителя.</p>'
    source['normalized_content']['sections'].append(
        {'key': 'solution', 'section_id': 'solution:1', 'html': parent_html})
    assert build_power_product_plan(source, parent_solution_html=parent_html).transformations == ()
