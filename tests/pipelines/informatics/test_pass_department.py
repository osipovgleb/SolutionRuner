from copy import deepcopy
from html import escape
import json
from pathlib import Path

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.informatics.pass_department import build_context_repair_plan
from solution_runner.pipelines.informatics.pass_department_condition import parse_pass_record
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


CASES = {r['source_problem_id']: r['condition'] for r in json.loads(
    (Path(__file__).parent / 'fixtures/pass_department.json').read_text()
)}


def context(source='15798', text=None):
    return {'normalized_content': {'format': 'teacherhelper-normalized', 'schema_version': 3,
                                  'assets': [], 'sections': [
                                      {'key': 'condition', 'html': '<p>' + escape(text or CASES[source]) + '</p>', 'asset_keys': []},
                                  ]}}


@pytest.mark.parametrize('source,code,department,answer', [
    ('15798', 9, 1, 14), ('15825', 9, 1, 22), ('15923', 10, 1, 9), ('15950', 9, 1, 10),
    ('16388', 12, 2, 26), ('16889', 10, 2, 28), ('16442', 10, 2, 18), ('16816', 9, 2, 19),
    ('17331', 12, 2, 16), ('17377', 13, 2, 15), ('18819', 15, 2, 31),
    ('28688', 11, 2, 23), ('29120', 12, 2, 22),
])
def test_audited_conditions_keep_independent_field_alignment(source, code, department, answer):
    value = context(source)
    before = deepcopy(value)
    record = parse_pass_record(CASES[source])
    plan = build_context_repair_plan(value)
    assert value == before
    assert plan.condition_html == value['normalized_content']['sections'][0]['html']
    assert plan.answer == str(answer)
    assert rf'{code}+{department}+x={record.total}' in plan.solution_html
    assert rf'x={record.total}-{code}-{department}={answer}' in plan.solution_html
    assert 'поэтому умножим число бит для одного символа' in plan.solution_html
    assert 'хранится отдельно от личного кода' in plan.solution_html
    assert 'парол' not in plan.solution_html


def test_rounding_and_intermediate_decimal_are_explained_in_order():
    plan = build_context_repair_plan(context())
    steps = ['26+10=36', r'6\cdot 11=66', r'\frac{66}{8}=8{,}25',
             r'\left\lceil 8{,}25\right\rceil=9', r'2^{7}\leq 200 &lt; 2^{8}',
             r'\frac{8}{8}=1', '9+1+x=24', 'x=24-9-1=14']
    positions = [plan.solution_html.index(s) for s in steps]
    assert positions == sorted(positions)


@pytest.mark.parametrize('maximum,dept_bytes,answer', [(255, 1, 14), (256, 2, 13)])
def test_binary_integer_maximum_includes_the_zero_bit_pattern(maximum, dept_bytes, answer):
    text = CASES['15798'].replace('от 1 до 200', f'от 1 до {maximum}')
    plan = build_context_repair_plan(context(text=text))
    assert plan.answer == str(answer)
    assert f'9+{dept_bytes}+x=24' in plan.solution_html


def test_three_and_four_digit_numbers_use_the_actual_numeric_upper_bound():
    record = parse_pass_record(CASES['17377'])
    assert (record.department_min, record.department_max) == (1000, 9999)
    plan = build_context_repair_plan(context('17377'))
    assert r'2^{13}\leq 9999 &lt; 2^{14}' in plan.solution_html
    assert r'\frac{14}{8}=1{,}75' in plan.solution_html


def test_alphabet_details_do_not_drop_case_excluded_digits_or_special_symbols():
    for source, size, formula in [('15923', 29, '20+9=29'), ('16388', 69, r'2\cdot 30+9=69'),
                                  ('16889', 31, '25+6=31'), ('18819', 71, r'2\cdot26+10+9=71')]:
        record = parse_pass_record(CASES[source])
        assert record.size == size and record.alphabet_formula == formula
    plan = build_context_repair_plan(context('18819'))
    assert '@#$%^&amp;*()' in plan.solution_html
    assert 'на карте выделено 48 байт' in plan.solution_html


def test_separate_rounding_is_not_replaced_with_a_single_rounding():
    text = CASES['15798'].replace('из 11 символов', 'из 1 символов').replace('от 1 до 200', 'от 1 до 256')
    # 6 bits -> 1 byte, 9 bits -> 2 bytes. Combining the 15 bits would incorrectly give 2 bytes.
    assert build_context_repair_plan(context(text=text)).answer == '21'


@pytest.mark.parametrize('old,new', [
    ('Сколько байт выделено', 'Сколько бит выделено'),
    ('минимально возможным количеством бит', 'произвольным количеством бит'),
    ('занимает минимально возможное целое число байт', 'вместе с личным кодом занимает целое число байт'),
    ('личный код сотрудника, номер подразделения', 'личный код сотрудника, два номера подразделений'),
    ('26 заглавных латинских букв', '26 заглавных и строчных латинских букв'),
    ('24 байта данных', '1 байта данных'),
])
def test_unsupported_units_packing_alphabet_and_allocation_fail_closed(old, new):
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(context(text=CASES['15798'].replace(old, new)))


def test_inconsistent_excluded_letter_count_is_rejected():
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(context(text=CASES['15923'].replace('6 букв', '5 букв')))


def test_saved_solution_converges_without_touching_condition_or_correct_answer():
    value = context()
    plan = build_context_repair_plan(value)
    value['normalized_content']['sections'].extend([
        {'key': 'solution', 'html': plan.solution_html, 'asset_keys': []},
        {'key': 'answer', 'html': '<p>14</p>', 'asset_keys': []},
    ])
    assert not build_context_repair_plan(value).transformations


@pytest.mark.parametrize('key', ['15798', '15923', '16388', '17331', '18819', '28688'])
def test_all_six_groups_use_the_shared_launcher_and_verified_readback(key):
    profile = get_group_profile(key)
    handler = get_handler(profile.content_rule_key)
    assert profile.content_rule_key == 'informatics-pass-department-extra-bytes'
    assert profile.existing_solution_policy == 'rewrite'
    assert handler.parent_from_group_listing and handler.verify_content_readback
    assert not handler.requires_parent_condition_asset
