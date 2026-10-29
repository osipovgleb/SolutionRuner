from copy import deepcopy

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.informatics.password_total_bytes import build_context_repair_plan
from solution_runner.pipelines.informatics.password_total_bytes_condition import parse_total_record
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


def context(*, length=15, users=50, extra=12):
    text = (
        'При регистрации в компьютерной системе каждому пользователю выдаётся пароль, '
        f'состоящий из {length} символов и содержащий только символы из 12-символьного набора: '
        'А, В, C, D, Е, F, G, H, К, L, M, N. '
        'В базе данных для хранения сведений о каждом пользователе отведено одинаковое '
        'и минимально возможное целое число байт. При этом используют посимвольное '
        'кодирование паролей, все символы кодируют одинаковым и минимально возможным количеством бит. '
        'Кроме собственно пароля, для каждого пользователя в системе хранятся дополнительные сведения, '
        f'для чего отведено {extra} байт на одного пользователя. '
        f'Определите объём памяти (в байтах), необходимый для хранения сведений о {users} пользователях. '
        'В ответе запишите только целое число — количество байт.'
    )
    return {'normalized_content': {'format': 'teacherhelper-normalized', 'schema_version': 3,
                                  'assets': [], 'sections': [{'key': 'condition', 'html': '<p>'+text+'</p>', 'asset_keys': []}]}}


def test_whole_password_is_rounded_before_adding_extra_and_multiplying():
    value = context()
    before = deepcopy(value)
    plan = build_context_repair_plan(value)
    assert value == before
    assert plan.answer == '1000'
    assert plan.condition_html == value['normalized_content']['sections'][0]['html']
    expected = [r'\frac{60}{8}=7{,}5', r'\left\lceil 7{,}5\right\rceil=8', r'8+12=20', r'20\cdot 50=1000']
    positions = [plan.solution_html.index(step) for step in expected]
    assert positions == sorted(positions)
    assert len(plan.transformations) == 2


@pytest.mark.parametrize('length,users,extra,answer', [(16, 3, 0, '24'), (15, 100, 12, '2000')])
def test_exact_byte_boundary_zero_extra_and_another_user_count(length, users, extra, answer):
    plan = build_context_repair_plan(context(length=length, users=users, extra=extra))
    assert plan.answer == answer
    if length == 16:
        assert r'\left\lceil' not in plan.solution_html


def test_existing_solution_and_correct_answer_converge():
    value = context()
    value['normalized_content']['sections'].extend([
        {'key': 'solution', 'transformation_target_id': 'section:solution:1', 'html': '<p>Старое решение</p>', 'asset_keys': []},
        {'key': 'answer', 'html': '<p>1000</p>', 'asset_keys': []},
    ])
    plan = build_context_repair_plan(value)
    assert len(plan.transformations) == 1
    assert plan.transformations[0]['transformation_target_id'] == 'section:solution:1'
    value['normalized_content']['sections'][1]['html'] = plan.solution_html
    assert not build_context_repair_plan(value).transformations


@pytest.mark.parametrize('old,new', [('в байтах', 'в битах'), ('минимально возможным', 'произвольным'), ('12-символьного', '11-символьного')])
def test_changed_units_encoding_or_alphabet_fail_closed(old, new):
    value = context()
    condition = value['normalized_content']['sections'][0]
    condition['html'] = condition['html'].replace(old, new)
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)


def test_group_8101_uses_shared_launcher_with_verified_readback():
    profile = get_group_profile('8101')
    assert profile.source_group_id == 'a2b015bc-8d33-49c6-a7c2-82e94d0227c7'
    assert profile.existing_solution_policy == 'rewrite'
    handler = get_handler(profile.content_rule_key)
    handler.validate()
    assert handler.parent_from_group_listing and handler.verify_content_readback
    assert not handler.requires_parent_condition_asset


def test_total_question_can_use_a_named_subset_and_a_different_record_count():
    value = context(users=400)
    condition = value['normalized_content']['sections'][0]
    condition['html'] = condition['html'].replace(
        ' и содержащий только символы из 12-символьного набора: А, В, C, D, Е, F, G, H, К, L, M, N',
        '. Для построения идентификатора используют 15 букв из определённого набора',
    )
    plan = build_context_repair_plan(value)
    assert plan.answer == '8000'
    assert r'20\cdot 400=8000' in plan.solution_html


def test_no_extra_field_is_not_replaced_with_an_invented_zero_byte_field():
    value = context()
    condition = value['normalized_content']['sections'][0]
    condition['html'] = condition['html'].replace(
        'Кроме собственно пароля, для каждого пользователя в системе хранятся дополнительные сведения, '
        'для чего отведено 12 байт на одного пользователя. ', '',
    )
    plan = build_context_repair_plan(value)
    assert plan.answer == '400'
    assert 'дополнительные сведения' not in plan.solution_html
    assert r'8\cdot 50=400' in plan.solution_html


def test_italic_and_semantic_letters_preserve_the_condition():
    value = context()
    condition = value['normalized_content']['sections'][0]
    condition['html'] = condition['html'].replace('А, В, C', '<i>А</i>, <i>В</i>, <var data-math-identifier="C">C</var>')
    before = deepcopy(value)
    plan = build_context_repair_plan(value)
    assert value == before
    assert plan.condition_html == condition['html']
    assert plan.answer == '1000'
    condition['html'] = condition['html'].replace('<i>А</i>', '<i class="unknown">А</i>')
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)


def element_context(length=290, size=1012, count='32\u202f768'):
    text = (
        'В базе данных хранится информация об объектах определённой структуры. '
        f'Каждый объект описывается как последовательность из {length} простых элементов, '
        f'при этом всего используется {size} различных простых элементов. '
        'Каждое описание объекта записывается как последовательность кодов простых элементов, '
        'при этом код каждого элемента содержит одинаковое для всех элементов минимально возможное число битов, '
        'а для описания в целом отводится минимально возможное целое число байтов. '
        f'Сколько Кбайтов потребуется для хранения {count} описаний, построенных по такой схеме? '
        'В ответе запишите только число — количество Кбайтов.'
    )
    value = context()
    value['normalized_content']['sections'][0]['html'] = '<p>' + text + '</p>'
    return value


def test_each_description_is_rounded_before_multiplying_and_converting_units():
    plan = build_context_repair_plan(element_context())
    assert plan.answer == '11616'
    assert r'\frac{2900}{8}=362{,}5' in plan.solution_html
    assert r'\left\lceil 362{,}5\right\rceil=363' in plan.solution_html
    assert r'363\cdot 32768=11894784' in plan.solution_html
    assert r'\frac{11894784}{1024}=11616' in plan.solution_html
    assert 'одного элемента' in plan.solution_html
    assert 'парол' not in plan.solution_html


@pytest.mark.parametrize('old,new', [('Кбайтов', 'Мбайтов'), ('минимально возможное число битов', 'произвольное число битов')])
def test_description_unit_or_encoding_changes_are_rejected(old, new):
    value = element_context()
    condition = value['normalized_content']['sections'][0]
    condition['html'] = condition['html'].replace(old, new)
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)


def test_non_integral_kbyte_answer_is_not_rounded():
    with pytest.raises(UnsupportedCondition, match='not an integer'):
        build_context_repair_plan(element_context(count='1'))


def test_mixed_case_alphabet_counts_uppercase_and_lowercase_letters():
    record = parse_total_record(
        'При регистрации в компьютерной системе для каждого пользователя формируется индивидуальный идентификатор, состоящий из 14 символов. '
        'Для построения идентификатора используют только латинские буквы (26 заглавных и 26 строчных букв). '
        'В базе данных для хранения сведений о каждом пользователе отведено одинаковое минимально возможное целое число байт. '
        'При этом используют посимвольное кодирование идентификаторов, все символы кодируют одинаковым минимально возможным количеством бит. '
        'Кроме идентификатора для каждого пользователя в системе хранятся дополнительные сведения, для чего выделено 19 байт на каждого пользователя. '
        'Сколько байт нужно для хранения сведений о 25 пользователях?'
    )
    assert (record.size, record.extra, record.users) == (52, 19, 25)
    assert record.alphabet_formula == '26+26=52'
