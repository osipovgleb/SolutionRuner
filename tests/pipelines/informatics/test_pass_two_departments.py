from copy import deepcopy
from html import escape
import json
from pathlib import Path

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.informatics.pass_department import build_context_repair_plan as one_department_plan
from solution_runner.pipelines.informatics.pass_two_departments import build_context_repair_plan
from solution_runner.pipelines.informatics.pass_two_departments_condition import parse_two_departments_record
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


CASES = {r['source_problem_id']: r['condition'] for r in json.loads(
    (Path(__file__).parent / 'fixtures/pass_two_departments.json').read_text()
)}


def context(source='18494', text=None):
    return {'normalized_content': {'format': 'teacherhelper-normalized', 'schema_version': 3,
                                  'assets': [], 'sections': [
                                      {'key': 'condition', 'html': '<p>' + escape(text or CASES[source]) + '</p>', 'asset_keys': []},
                                  ]}}


@pytest.mark.parametrize('source,packing,answer', [
    ('18494', 'separate', '19'), ('18625', 'separate', '20'),
    ('18561', 'joint', '21'), ('18589', 'joint', '22'),
])
def test_audited_conditions_preserve_alignment_and_do_not_modify_the_input(source, packing, answer):
    value = context(source)
    before = deepcopy(value)
    plan = build_context_repair_plan(value)
    assert value == before and plan.condition_html == value['normalized_content']['sections'][0]['html']
    assert parse_two_departments_record(CASES[source]).packing == packing
    assert plan.answer == answer
    assert 'поэтому умножим число бит для одного символа' in plan.solution_html
    assert 'два' in plan.solution_html and 'поэтому умножим' in plan.solution_html


def test_separate_fields_round_before_multiplying_the_two_department_numbers():
    solution = build_context_repair_plan(context()).solution_html
    steps = ['12+10=22', r'5\cdot 13=65', r'\frac{65}{8}=8{,}125',
             r'\left\lceil 8{,}125\right\rceil=9', r'2^{9}\leq 999 &lt; 2^{10}',
             r'\frac{10}{8}=1{,}25', r'\left\lceil 1{,}25\right\rceil=2',
             r'2\cdot 2=4', '9+4+x=32', 'x=32-9-4=19']
    positions = [solution.index(s) for s in steps]
    assert positions == sorted(positions)


def test_joint_fields_add_bits_before_the_only_byte_rounding():
    solution = build_context_repair_plan(context('18561')).solution_html
    steps = [r'5\cdot 13=65', r'2^{9}\leq 1000 &lt; 2^{10}', r'10\cdot 2=20',
             '65+20=85', r'\frac{85}{8}=10{,}625', r'\left\lceil 10{,}625\right\rceil=11',
             '11+x=32', 'x=32-11=21']
    positions = [solution.index(s) for s in steps]
    assert positions == sorted(positions)
    assert solution.count(r'\frac{') == solution.count(r'\left\lceil') == 1
    assert 'целое число байт' in solution and 'сначала сложим их объёмы в битах' in solution
    assert r'\frac{65}{8}' not in solution and r'\frac{10}{8}' not in solution


def test_two_digit_fields_and_changed_alphabet_are_computed_from_the_condition():
    separate = build_context_repair_plan(context('18625'))
    assert r'\frac{7}{8}=0{,}875' in separate.solution_html
    assert r'1\cdot 2=2' in separate.solution_html
    packed = build_context_repair_plan(context('18589'))
    assert '16+10=26' in packed.solution_html
    assert r'7\cdot 2=14' in packed.solution_html
    assert r'\frac{79}{8}=9{,}875' in packed.solution_html


@pytest.mark.parametrize('maximum,answer', [(127, '22'), (128, '21')])
def test_binary_integer_at_a_power_of_two_uses_an_extra_bit(maximum, answer):
    text = CASES['18561'].replace('не превышающих 1000', f'не превышающих {maximum}')
    assert build_context_repair_plan(context(text=text)).answer == answer


@pytest.mark.parametrize('source,old,new', [
    ('18494', 'Сколько байт выделено', 'Сколько бит выделено'),
    ('18494', 'одинаковым минимально возможным количеством бит', 'неравномерным количеством бит'),
    ('18494', 'из двух трёхзначных чисел', 'из трёх трёхзначных чисел'),
    ('18494', 'каждое из которых кодируется как двоичное число', 'каждое из которых кодируется посимвольно'),
    ('18494', 'занимает минимально возможное целое число байт', 'занимает минимально возможное целое число бит'),
    ('18561', 'занимает минимально возможное целое число бит', 'занимает минимально возможное целое число байт'),
    ('18561', 'Личный код и код подразделения записываются подряд и вместе занимают', 'Каждое поле отдельно занимает'),
    ('18561', '32 байт данных', '1 байт данных'),
])
def test_changed_units_field_count_encoding_and_packing_fail_closed(source, old, new):
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(context(text=CASES[source].replace(old, new)))


def test_old_single_department_rule_rejects_both_new_packing_variants():
    for source in CASES:
        with pytest.raises(UnsupportedCondition):
            one_department_plan(context(source))


def test_zero_extra_is_valid_and_saved_solution_is_idempotent():
    value = context(text=CASES['18561'].replace('32 байт данных', '11 байт данных'))
    plan = build_context_repair_plan(value)
    assert plan.answer == '0'
    value['normalized_content']['sections'].extend([
        {'key': 'solution', 'html': plan.solution_html, 'asset_keys': []},
        {'key': 'answer', 'html': '<p>0</p>', 'asset_keys': []},
    ])
    assert not build_context_repair_plan(value).transformations


@pytest.mark.parametrize('key', ['18494', '18561'])
def test_both_groups_use_shared_runtime_with_verified_readback(key):
    profile = get_group_profile(key)
    assert profile.content_rule_key == 'informatics-pass-two-departments-extra-bytes'
    assert profile.existing_solution_policy == 'rewrite'
    handler = get_handler(profile.content_rule_key)
    assert handler.parent_from_group_listing and handler.verify_content_readback
    assert not handler.requires_parent_condition_asset
