"""Compute the extra information on a pass with two separately aligned fields."""

from fractions import Fraction

from solution_runner.pipelines.word_problems.common import UnsupportedCondition, decimal_latex, finalize

from .pass_department_condition import parse_pass_record
from .password_extra_bytes_condition import read_content
from .password_storage import formula, storage_steps


def _bytes(value):
    ending = '' if value % 100 in (11, 12, 13, 14) else ('а' if value % 10 in (2, 3, 4) else '')
    return f'{value} байт{ending}'


def build_context_repair_plan(context):
    _, condition, answer_section, solution_section, text = read_content(context)
    record = parse_pass_record(text)
    code_bytes, intro = storage_steps(
        record.length, record.size, genitive='личного кода', locative='личном коде', accusative='личный код',
        alphabet_formula=record.alphabet_formula, alphabet_intro=record.alphabet_intro,
    )
    # The department is stored as the binary integer itself, not a renumbered label.
    bits = record.department_max.bit_length()
    department_bytes = (bits + 7) // 8
    byte_count = decimal_latex(Fraction(bits, 8))
    extra = record.total - code_bytes - department_bytes
    if extra < 0:
        raise UnsupportedCondition('pass fields exceed its total byte allocation')
    department_genitive = 'кода подразделения' if record.department_name.startswith('Код') else 'номера подразделения'
    solution = (
        intro
        + f'<p>Теперь найдём объём памяти для {department_genitive}. {record.department_name} — '
        f'целое число от {record.department_min} до {record.department_max}. '
        'При записи числа <span data-inline-latex="k"></span> битами можно представить целые числа '
        'от 0 до <span data-inline-latex="2^k-1"></span>. '
        f'Поэтому число бит выбираем так, чтобы можно было записать наибольшее значение — {record.department_max}.</p>'
        + formula(rf'2^{{{bits-1}}}\leq {record.department_max} &lt; 2^{{{bits}}}')
        + formula(rf'k={bits}')
        + f'<p>По условию {record.department_name.lower()} хранится отдельно от личного кода и занимает целое число байт. '
        'Разделим число бит на 8 — число бит в одном байте.</p>'
        + formula(rf'\frac{{{bits}}}{{8}}={byte_count}\;\text{{байт}}')
        + (
            '<p>Получили нецелое число байт, поэтому округляем его вверх.</p>'
            + formula(rf'\left\lceil {byte_count}\right\rceil={department_bytes}\;\text{{байт}}')
            if bits % 8 else ''
        )
        + f'<p>Всего на {record.carrier} выделено {_bytes(record.total)}. Из них {_bytes(code_bytes)} занимает личный код '
        f'и {_bytes(department_bytes)} — {record.department_name.lower()}. Пусть на дополнительные сведения выделено '
        '<span data-inline-latex="x"></span> байт. Составим уравнение и найдём оставшийся объём.</p>'
        + formula(rf'{code_bytes}+{department_bytes}+x={record.total}')
        + formula(rf'x={record.total}-{code_bytes}-{department_bytes}={extra}')
    )
    return finalize(
        condition, answer_section, solution_section, extra, solution,
        rewrite_existing_solution=str((solution_section or {}).get('html') or '') != solution,
    )
