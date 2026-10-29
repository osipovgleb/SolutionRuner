"""Explain separate alignment or joint bit packing on a pass with two department integers."""

from fractions import Fraction

from solution_runner.pipelines.word_problems.common import UnsupportedCondition, decimal_latex, finalize

from .pass_department import _bytes
from .pass_two_departments_condition import parse_two_departments_record
from .password_extra_bytes_condition import read_content
from .password_storage import encoding_bits_steps, formula, storage_steps


def _byte_steps(bit_count, byte_count):
    decimal = decimal_latex(Fraction(bit_count, 8))
    html = formula(rf'\frac{{{bit_count}}}{{8}}={decimal}\;\text{{байт}}')
    if bit_count % 8:
        html += (
            '<p>Получили нецелое число байт, поэтому округляем его вверх.</p>'
            + formula(rf'\left\lceil {decimal}\right\rceil={byte_count}\;\text{{байт}}')
        )
    return html


def _department_range_intro(record):
    if record.packing == 'joint':
        return 'Код подразделения состоит из двух чисел. '
    adjective = 'двузначное' if record.department_min == 10 else 'трёхзначное'
    plural = 'двузначных' if record.department_min == 10 else 'трёхзначных'
    return (
        f'По условию код подразделения состоит из двух {plural} чисел. '
        f'Наименьшее {adjective} число — {record.department_min}, '
        f'а наибольшее — {record.department_max}. '
    )


def build_context_repair_plan(context):
    _, condition, answer_section, solution_section, text = read_content(context)
    record = parse_two_departments_record(text)
    code_steps = storage_steps if record.packing == 'separate' else encoding_bits_steps
    code_storage, intro = code_steps(
        record.length, record.size, genitive='личного кода', locative='личном коде',
        alphabet_formula=record.alphabet_formula, alphabet_intro=record.alphabet_intro,
        **({'accusative': 'личный код'} if record.packing == 'separate' else {}),
    )
    bits = record.department_max.bit_length()
    solution = (
        intro
        + '<p>' + _department_range_intro(record) + 'Каждое число лежит в диапазоне '
        f'от {record.department_min} до {record.department_max} и записывается как двоичное число. '
        'При записи числа <span data-inline-latex="k"></span> битами можно представить целые числа '
        'от 0 до <span data-inline-latex="2^k-1"></span>. '
        f'Поэтому найдём минимальное число бит, достаточное для записи наибольшего значения — {record.department_max}.</p>'
        + formula(rf'2^{{{bits-1}}}\leq {record.department_max} &lt; 2^{{{bits}}}')
        + formula(rf'k={bits}')
    )
    if record.packing == 'separate':
        one_number_bytes = (bits + 7) // 8
        department_bytes = 2 * one_number_bytes
        used_bytes = code_storage + department_bytes
        solution += (
            '<p>По условию каждое из двух чисел подразделения занимает отдельное целое число байт. '
            'Переведём объём одного числа в байты: разделим число бит на 8 — число бит в одном байте.</p>'
            + _byte_steps(bits, one_number_bytes)
            + f'<p>Одно число занимает {_bytes(one_number_bytes)}. '
            'В коде подразделения два таких числа, поэтому умножим объём одного числа на 2.</p>'
            + formula(rf'{one_number_bytes}\cdot 2={department_bytes}\;\text{{байт}}')
        )
        equation = formula(rf'{code_storage}+{department_bytes}+x={record.total}')
        result = lambda extra: formula(rf'x={record.total}-{code_storage}-{department_bytes}={extra}')
        used_explanation = (
            f'Из них {_bytes(code_storage)} занимает личный код '
            f'и {_bytes(department_bytes)} — два числа подразделения. '
        )
    else:
        department_bits = 2 * bits
        used_bits = code_storage + department_bits
        used_bytes = (used_bits + 7) // 8
        solution += (
            f'<p>Для записи одного числа подразделения нужно {_bit_count(bits)}. '
            'В коде подразделения два таких числа, поэтому умножим число бит для одного числа на 2.</p>'
            + formula(rf'{bits}\cdot 2={department_bits}\;\text{{бит}}')
            + f'<p>Личный код занимает {_bit_count(code_storage)}, а два числа подразделения — {_bit_count(department_bits)}. '
            'По условию они записываются подряд и только вместе занимают целое число байт. '
            'Поэтому сначала сложим их объёмы в битах.</p>'
            + formula(rf'{code_storage}+{department_bits}={used_bits}\;\text{{бит}}')
            + '<p>Теперь переведём общий объём в байты: разделим число бит на 8 — число бит в одном байте.</p>'
            + _byte_steps(used_bits, used_bytes)
        )
        equation = formula(rf'{used_bytes}+x={record.total}')
        result = lambda extra: formula(rf'x={record.total}-{used_bytes}={extra}')
        used_explanation = f'Личный код и два числа подразделения вместе занимают {_bytes(used_bytes)}. '
    extra = record.total - used_bytes
    if extra < 0:
        raise UnsupportedCondition('pass fields exceed its total byte allocation')
    solution += (
        f'<p>Всего на пропуске выделено {_bytes(record.total)}. ' + used_explanation
        + 'Пусть на дополнительные сведения выделено <span data-inline-latex="x"></span> байт. '
        'Составим уравнение и найдём оставшийся объём.</p>'
        + equation + result(extra)
    )
    return finalize(
        condition, answer_section, solution_section, extra, solution,
        rewrite_existing_solution=str((solution_section or {}).get('html') or '') != solution,
    )


def _bit_count(value):
    ending = 'а' if value % 10 in (2, 3, 4) and value % 100 not in (12, 13, 14) else ''
    return f'{value} бит{ending}'
