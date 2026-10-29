"""Compute whole-byte password storage and per-user additional information."""

from fractions import Fraction

from solution_runner.pipelines.word_problems.common import (
    UnsupportedCondition, decimal_latex, finalize,
)


from .password_extra_bytes_condition import parse_record, read_content


def _formula(latex: str) -> str:
    return f'<p><span data-inline-latex="{latex}"></span></p>'


def build_context_repair_plan(context):
    _, condition, answer_section, solution_section, text = read_content(context)
    record = parse_record(text)
    length, size, users, total = record.length, record.size, record.users, record.total
    bits = (size - 1).bit_length()
    password_bits = length * bits
    password_bytes = (password_bits + 7) // 8
    byte_count = decimal_latex(Fraction(password_bits, 8))
    rounding = (
        f'<p>Память под {record.accusative} выделяется целым числом байт, '
        'поэтому округляем полученный объём вверх.</p>'
        + _formula(rf"\left\lceil {byte_count}\right\rceil={password_bytes}\;\text{{байт}}")
        if password_bits % 8 else ''
    )
    per_user, remainder = divmod(total, users)
    extra = per_user - password_bytes
    if remainder or extra < 0:
        raise UnsupportedCondition("memory allocation is inconsistent with whole bytes per user")
    solution = (
        f'<p>Согласно условию, в {record.locative} могут быть использованы '
        f'{size} символов. С помощью <span data-inline-latex="N"></span> бит можно закодировать '
        '<span data-inline-latex="2^N"></span> различных вариантов. '
        'Найдём минимальное число бит для одного символа.</p>'
        + (_formula(record.alphabet_formula) if record.alphabet_formula else '')
        + _formula(rf"2^{{{bits-1}}} &lt; {size} \leq 2^{{{bits}}}")
        + _formula(rf"N={bits}")
        + f'<p>Для хранения всех {length} символов {record.genitive} нужно следующее число бит. '
        'Чтобы перевести биты в байты, разделим на 8 — число бит в одном байте.</p>'
        + _formula(rf"{bits}\cdot {length}={password_bits}\;\text{{бит}}")
        + _formula(rf"\frac{{{password_bits}}}{{8}}={byte_count}\;\text{{байт}}")
        + rounding
        + f'<p>Пусть количество памяти под дополнительные сведения об одном {record.entity} равно '
        '<span data-inline-latex="x"></span> байт. Составим уравнение для общего объёма памяти.</p>'
        + _formula(rf"{users}\cdot({password_bytes}+x)={total}")
        + _formula(rf"{password_bytes}+x=\frac{{{total}}}{{{users}}}={per_user}")
        + _formula(rf"x={per_user}-{password_bytes}={extra}")
    )
    current_solution = str((solution_section or {}).get("html") or "")
    return finalize(
        condition, answer_section, solution_section, extra, solution,
        rewrite_existing_solution=current_solution != solution,
    )
