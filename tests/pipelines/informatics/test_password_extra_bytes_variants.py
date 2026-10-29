from copy import deepcopy

import pytest

from solution_runner.pipelines.informatics.password_extra_bytes import build_context_repair_plan
from solution_runner.pipelines.informatics.profiles import PROFILES
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


def standard(header, *, identifier=False):
    noun, plural = ('идентификатора', 'идентификаторов') if identifier else ('пароля', 'паролей')
    return wrap(
        'При регистрации в компьютерной системе ' + header
        + '. В базе данных для хранения сведений о каждом пользователе отведено одинаковое минимально возможное целое число байт. '
        f'При этом используют посимвольное кодирование {plural}, все символы кодируют одинаковым минимально возможным количеством бит. '
        f'Кроме {noun} для каждого пользователя в системе хранятся дополнительные сведения, '
        'для чего выделено целое число байт, одно и то же для всех пользователей. '
        'Для хранения сведений о 20 пользователях потребовалось 400 байт. '
        'Сколько байт выделено для хранения дополнительных сведений об одном пользователе?'
    )


def wrap(text):
    return {'normalized_content': {'format': 'teacherhelper-normalized', 'schema_version': 3,
                                  'assets': [], 'sections': [{'key': 'condition', 'html': '<p>' + text + '</p>', 'asset_keys': []}]}}


@pytest.mark.parametrize('description,size,answer,formula', [
    (' и содержащий только символы из 26-символьного набора латинского алфавита', 26, '13', ''),
    (' и содержащий цифры и прописные символы латинского алфавита (всего 36 возможных символов)', 36, '12', '10+26=36'),
    (' и содержащий только прописные буквы латинского 26-символьного алфавита и десять цифр', 36, '12', '26+10=36'),
    (' и содержащий только символы из 62-символьного набора, содержащего все латинские буквы (заглавные и строчные) и десятичные цифры', 62, '12', r'2\cdot26+10=62'),
])
def test_alphabet_classes_and_rounding(description, size, answer, formula):
    value = standard('каждому пользователю выдаётся пароль, состоящий из 10 символов' + description)
    before = deepcopy(value)
    plan = build_context_repair_plan(value)
    assert value == before
    assert plan.answer == answer
    assert f' &lt; {size} ' in plan.solution_html
    if formula:
        assert formula in plan.solution_html


def test_mandatory_classes_still_use_uniform_symbol_encoding():
    description = ('. Из соображений информационной безопасности каждый пароль должен содержать хотя бы 1 десятичную цифру, '
                   'как прописные, так и строчные латинские буквы (в латинском алфавите 26 букв), '
                   'а также не менее 1 символа из 6-символьного набора: «&amp;», «#», «$», «*», «!», «@»')
    value = standard('каждому пользователю выдаётся пароль, состоящий из 9 символов' + description)
    plan = build_context_repair_plan(value)
    assert plan.answer == '12'
    assert r'10+2\cdot26+6=68' in plan.solution_html
    assert r'\frac{63}{8}=7{,}875' in plan.solution_html
    value['normalized_content']['sections'][0]['html'] = value['normalized_content']['sections'][0]['html'].replace('9 символов', '3 символов')
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)


def test_identifier_keeps_its_terminology():
    value = standard('для каждого пользователя формируется индивидуальный идентификатор, состоящий из 10 символов. '
                     'Для построения идентификатора используют только строчные латинские буквы (26 букв)', identifier=True)
    plan = build_context_repair_plan(value)
    assert plan.answer == '13'
    assert 'идентификатора' in plan.solution_html
    assert 'парол' not in plan.solution_html


@pytest.mark.parametrize('descriptor,answer,formula', [
    ('одной из 26 заглавных или строчных латинских букв', '12', r'2\cdot26=52'),
    ('одной из 10 первых латинских букв (A, B, C, D, E, F, G, H, I, J)', '15', ''),
])
def test_objects_keep_case_sensitive_alphabet_and_entity(descriptor, answer, formula):
    value = wrap('Каждый объект, зарегистрированный в информационной системе, получает уникальный код из 10 символов, каждый из которых может быть '
                 + descriptor + '. Для представления кода используют посимвольное кодирование, все символы кодируют одинаковым минимально возможным количеством битов, '
                 'а для кода в целом выделяется минимально возможное целое количество байтов. '
                 'Кроме того, для каждого объекта в системе выделен одинаковый объём памяти для хранения содержательной информации. '
                 'Для хранения данных (код и содержательная информация) о 20 объектах потребовалось 400 байт. '
                 'Сколько байтов выделено для хранения содержательной информации об одном объекте?')
    plan = build_context_repair_plan(value)
    assert plan.answer == answer
    assert 'об одном объекте' in plan.solution_html
    assert 'парол' not in plan.solution_html
    if formula:
        assert formula in plan.solution_html


def test_semantic_alphabet_letters_preserve_original_condition():
    value = standard('каждому пользователю выдаётся пароль, состоящий из 10 символов и содержащий только символы из 2-символьного набора: '
                     '<var data-math-identifier="A">A</var>, <var data-math-identifier="B">B</var>')
    before = deepcopy(value)
    plan = build_context_repair_plan(value)
    assert value == before
    assert plan.condition_html == before['normalized_content']['sections'][0]['html']
    assert plan.answer == '18'
    value['normalized_content']['sections'][0]['html'] = plan.condition_html.replace('data-math-identifier="A"', 'data-math-identifier="Z"')
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)


@pytest.mark.parametrize('old,new', [('400 байт', '401 байт'), ('Сколько байт выделено', 'Сколько бит выделено'),
                                    ('минимально возможным количеством бит', 'максимально возможным количеством бит')])
def test_changed_units_or_encoding_do_not_write(old, new):
    value = standard('каждому пользователю выдаётся пароль, состоящий из 10 символов и содержащий только символы из 26-символьного набора латинского алфавита')
    condition = value['normalized_content']['sections'][0]
    condition['html'] = condition['html'].replace(old, new)
    with pytest.raises(UnsupportedCondition):
        build_context_repair_plan(value)


def test_all_audited_groups_share_the_existing_rule():
    assert len(PROFILES) == 20
    assert len({p.source_group_id for p in PROFILES}) == 20
    assert {p.content_rule_key for p in PROFILES} == {'informatics-password-extra-bytes'}
