"""Shared explanatory steps for the whole-byte storage of one password or code."""

from fractions import Fraction

from solution_runner.pipelines.word_problems.common import decimal_latex


def formula(latex: str) -> str:
    return f'<p><span data-inline-latex="{latex}"></span></p>'


def storage_steps(length, size, *, genitive='пароля', locative='пароле', accusative='пароль', alphabet_formula='', items='символов', item='символа'):
    bits = (size - 1).bit_length()
    password_bits = length * bits
    password_bytes = (password_bits + 7) // 8
    byte_count = decimal_latex(Fraction(password_bits, 8))
    bit_word = 'бита' if bits % 10 in (2, 3, 4) and bits % 100 not in (12, 13, 14) else 'бит'
    rounding = (
        f'<p>Память под {accusative} выделяется целым числом байт, '
        'поэтому округляем полученный объём вверх.</p>'
        + formula(rf"\left\lceil {byte_count}\right\rceil={password_bytes}\;\text{{байт}}")
        if password_bits % 8 else ''
    )
    html = (
        f'<p>Согласно условию, в {locative} могут быть использованы '
        f'{size} {items}. С помощью <span data-inline-latex="N"></span> бит можно закодировать '
        '<span data-inline-latex="2^N"></span> различных вариантов. '
        f'Найдём минимальное число бит для одного {item}.</p>'
        + (formula(alphabet_formula) if alphabet_formula else '')
        + formula(rf"2^{{{bits-1}}} &lt; {size} \leq 2^{{{bits}}}")
        + formula(rf"N={bits}")
        + f'<p>Для хранения одного {item} {genitive} нужно {bits} {bit_word}. '
        f'Всего в {locative} {length} {items}, поэтому умножим число бит для одного {item} на количество {items}. '
        'Чтобы перевести биты в байты, разделим на 8 — число бит в одном байте.</p>'
        + formula(rf"{bits}\cdot {length}={password_bits}\;\text{{бит}}")
        + formula(rf"\frac{{{password_bits}}}{{8}}={byte_count}\;\text{{байт}}")
        + rounding
    )
    return password_bytes, html
