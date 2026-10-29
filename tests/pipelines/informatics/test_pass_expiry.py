from copy import deepcopy
from html import escape
import json
from pathlib import Path

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.informatics.pass_expiry import build_context_repair_plan
from solution_runner.pipelines.informatics.pass_expiry_condition import parse_expiry_record
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


CASES = {r['source_problem_id']: r['condition'] for r in json.loads(
    (Path(__file__).parent / 'fixtures/pass_expiry.json').read_text()
)}


def context(source='27271', text=None):
    return {'normalized_content': {'format': 'teacherhelper-normalized', 'schema_version': 3,
                                  'assets': [], 'sections': [
                                      {'key': 'condition', 'html': '<p>' + escape(text or CASES[source]) + '</p>', 'asset_keys': []},
                                  ]}}


@pytest.mark.parametrize('source,code_bytes,date_bytes,answer', [
    ('27271', 14, 2, '16'), ('27298', 12, 2, '14'), ('28549', 10, 2, '12'),
])
def test_audited_tasks_compute_code_and_date_with_their_own_byte_alignment(source, code_bytes, date_bytes, answer):
    value = context(source)
    before = deepcopy(value)
    plan = build_context_repair_plan(value)
    assert value == before and plan.condition_html == value['normalized_content']['sections'][0]['html']
    assert plan.answer == answer
    assert rf'{code_bytes}+{date_bytes}={answer}\;\text{{байт}}' in plan.solution_html
    assert 'поэтому умножим число бит для одного символа' in plan.solution_html
    assert 'По условию кодируется именно этот номер' in plan.solution_html
    assert 'сначала сложим их объёмы в битах' in plan.solution_html
    assert 'для личного кода выделяется отдельное целое число байт' in plan.solution_html


def test_year_and_day_are_packed_before_rounding_the_date():
    solution = build_context_repair_plan(context('27298')).solution_html
    steps = [r'5\cdot 19=95', r'\frac{95}{8}=11{,}875', r'\left\lceil 11{,}875\right\rceil=12',
             r'2^{5}\leq 60 &lt; 2^{6}', 'k=6', r'2^{8}\leq 366 &lt; 2^{9}', 'm=9',
             '6+9=15', r'\frac{15}{8}=1{,}875', r'\left\lceil 1{,}875\right\rceil=2', '12+2=14']
    positions = [solution.index(s) for s in steps]
    assert positions == sorted(positions)
    assert r'\frac{6}{8}' not in solution and r'\frac{9}{8}' not in solution
    assert 'в личном коде 19 символов' in solution and '22 символов' not in solution


def test_month_alphabet_and_separate_code_rounding_are_not_lost():
    solution = build_context_repair_plan(context('28549')).solution_html
    assert '26+10=36' in solution and 'Номер месяца — число от 1 до 12' in solution
    assert r'\frac{78}{8}=9{,}75' in solution
    assert '6+4=10' in solution and r'\frac{10}{8}=1{,}25' in solution
    assert solution.count(r'\left\lceil') == 2


def test_exact_byte_date_does_not_get_an_extra_byte():
    solution = build_context_repair_plan(context()).solution_html
    assert '7+9=16' in solution and r'\frac{16}{8}=2' in solution
    assert solution.count(r'\left\lceil') == 1


@pytest.mark.parametrize('maximum,answer', [(15, '11'), (16, '12')])
def test_year_zero_and_the_power_of_two_boundary_are_counted(maximum, answer):
    text = CASES['28549'].replace('от 0 до 60', f'от 0 до {maximum}').replace('до 2060', f'до {2000+maximum}')
    assert build_context_repair_plan(context(text=text)).answer == answer


@pytest.mark.parametrize('source,old,new', [
    ('27271', 'Сколько байтов занимает', 'Сколько битов занимает'),
    ('27271', 'минимально возможным количеством битов', 'произвольным количеством битов'),
    ('27271', 'означающее год от 2000 до 2099', 'означающее год от 2000 до 2098'),
    ('27271', 'число от 1 до 366', 'число от 1 до 365'),
    ('27271', 'Номер года и номер дня записаны', 'Номер года и номер месяца записаны'),
    ('27271', 'а два числа вместе', 'а каждое число отдельно'),
    ('27271', 'целое число байтов, при этом', 'целое число битов, при этом'),
    ('28549', 'число от 1 до 12', 'число от 1 до 13'),
    ('28549', '26 заглавных латинских букв', '26 заглавных и строчных латинских букв'),
])
def test_unaudited_units_packing_year_mapping_and_date_ranges_fail_closed(source, old, new):
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(context(text=CASES[source].replace(old, new)))


def test_record_keeps_the_year_label_range_and_date_component():
    record = parse_expiry_record(CASES['27271'])
    assert (record.year_max, record.first_year, record.last_year, record.date_unit, record.unit_max) == (99, 2000, 2099, 'day', 366)


def test_saved_solution_converges_without_rewriting_an_existing_answer():
    value = context()
    value['normalized_content']['sections'].append({'key': 'answer', 'html': '<p><span data-effect="spaced">16</span></p>', 'asset_keys': []})
    plan = build_context_repair_plan(value)
    assert len(plan.transformations) == 1
    value['normalized_content']['sections'].append({'key': 'solution', 'html': plan.solution_html, 'asset_keys': []})
    assert not build_context_repair_plan(value).transformations


@pytest.mark.parametrize('key', ['inf-27271', '28549'])
def test_groups_use_shared_launcher_and_verified_readback(key):
    profile = get_group_profile(key)
    assert profile.content_rule_key == 'informatics-pass-expiry-bytes'
    assert profile.existing_solution_policy == 'rewrite'
    handler = get_handler(profile.content_rule_key)
    assert handler.parent_from_group_listing and handler.verify_content_readback
    assert not handler.requires_parent_condition_asset


def test_namespaced_informatics_key_preserves_the_existing_mathematics_group():
    assert get_group_profile('inf-27271').source_group_id == '47c1df0b-6a0f-480f-aee5-c7f0a5e23668'
    assert get_group_profile('27271').source_group_id == '07b024c7-a4a9-42da-8f06-3b76c754d39a'
