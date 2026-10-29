"""Explain the separate byte allocation of a personal code and an expiry date."""

from solution_runner.pipelines.word_problems.common import finalize

from .pass_department import _bytes
from .pass_expiry_condition import parse_expiry_record
from .pass_two_departments import _bit_count, _byte_steps
from .password_extra_bytes_condition import read_content
from .password_storage import formula, storage_steps


def build_context_repair_plan(context):
    _, condition, answer_section, solution_section, text = read_content(context)
    record = parse_expiry_record(text)
    counted_items = 'символов'
    if record.length % 100 not in (11, 12, 13, 14):
        if record.length % 10 == 1:
            counted_items = 'символ'
        elif record.length % 10 in (2, 3, 4):
            counted_items = 'символа'
    code_bytes, solution = storage_steps(
        record.length, record.size, genitive='личного кода', locative='личном коде', accusative='личный код',
        alphabet_formula='26+10=36' if record.size == 36 else '',
        alphabet_intro=(
            'Согласно условию, в личном коде можно использовать 26 заглавных латинских букв. '
            if record.size == 26 else ''
        ),
        counted_items=counted_items,
    )
    year_bits = record.year_max.bit_length()
    unit_bits = record.unit_max.bit_length()
    date_bits = year_bits + unit_bits
    date_bytes = (date_bits + 7) // 8
    total = code_bytes + date_bytes
    solution += (
        f'<p>Теперь найдём объём памяти для срока действия пропуска. Номер года — число от 0 до {record.year_max}: '
        f'0 означает {record.first_year} год, а {record.year_max} — {record.last_year} год. '
        'По условию кодируется именно этот номер. При записи числа <span data-inline-latex="k"></span> битами '
        'можно представить целые числа от 0 до <span data-inline-latex="2^k-1"></span>. '
        f'Поэтому найдём минимальное число бит, достаточное для записи наибольшего номера года — {record.year_max}.</p>'
        + formula(rf'2^{{{year_bits-1}}}\leq {record.year_max} &lt; 2^{{{year_bits}}}')
        + formula(rf'k={year_bits}')
        + f'<p>Номер {record.unit_name} — число от 1 до {record.unit_max}. '
        'Аналогично найдём минимальное число бит для записи наибольшего значения. '
        'Обозначим это число бит буквой <span data-inline-latex="m"></span>.</p>'
        + formula(rf'2^{{{unit_bits-1}}}\leq {record.unit_max} &lt; 2^{{{unit_bits}}}')
        + formula(rf'm={unit_bits}')
        + f'<p>Номер года занимает {_bit_count(year_bits)}, а номер {record.unit_name} — {_bit_count(unit_bits)}. '
        'По условию два числа вместе занимают минимальное целое число байт. '
        'Поэтому сначала сложим их объёмы в битах.</p>'
        + formula(rf'{year_bits}+{unit_bits}={date_bits}\;\text{{бит}}')
        + '<p>Переведём объём срока действия в байты: разделим число бит на 8 — число бит в одном байте.</p>'
        + _byte_steps(date_bits, date_bytes)
        + f'<p>Личный код занимает {_bytes(code_bytes)}, а срок действия — {_bytes(date_bytes)}. '
        'По условию для личного кода выделяется отдельное целое число байт, '
        'поэтому теперь складываем объёмы кода и срока действия в байтах.</p>'
        + formula(rf'{code_bytes}+{date_bytes}={total}\;\text{{байт}}')
    )
    return finalize(
        condition, answer_section, solution_section, total, solution,
        rewrite_existing_solution=str((solution_section or {}).get('html') or '') != solution,
    )
