"""Shared explanatory steps for the whole-byte storage of one password or code."""

from fractions import Fraction
import re

from solution_runner.pipelines.word_problems.common import UnsupportedCondition, decimal_latex


def formula(latex: str) -> str:
    return f'<p><span data-inline-latex="{latex}"></span></p>'


def _alphabet_explanation(expression, locative, size):
    letters_and_digits = (
        f'Согласно условию, в {locative} можно использовать 26 заглавных латинских букв '
        'и 10 цифр — от 0 до 9. Буквы и цифры являются разными символами, '
        'поэтому общее количество допустимых символов найдём сложением. '
    )
    explanations = {
        '26+10=36': letters_and_digits,
        '10+26=36': letters_and_digits,
        r'2\cdot26=52': (
            f'Согласно условию, в {locative} можно использовать 26 заглавных и 26 строчных латинских букв. '
            'Заглавная и строчная буквы считаются разными символами. '
            'Поэтому учитываем две группы по 26 букв. '
        ),
        '26+26=52': (
            f'Согласно условию, в {locative} можно использовать 26 заглавных и 26 строчных латинских букв. '
            'Заглавная и строчная буквы считаются разными символами, поэтому складываем количества букв двух групп. '
        ),
        r'2\cdot26+10=62': (
            f'Согласно условию, в {locative} можно использовать заглавные и строчные латинские буквы, а также десятичные цифры. '
            'В каждой группе букв по 26 символов, а цифр от 0 до 9 — 10. '
            'Заглавные и строчные буквы считаются разными символами, поэтому складываем количества символов всех трёх групп. '
        ),
        r'10+2\cdot26+6=68': (
            f'Согласно условию, в {locative} можно использовать 10 десятичных цифр, '
            '26 заглавных и 26 строчных латинских букв, а также 6 специальных символов. '
            'Все эти группы различны, поэтому общее количество допустимых символов найдём сложением. '
        ),
    }
    if expression in explanations:
        return explanations[expression]
    special = re.fullmatch(r'10\+([1-9]\d*)=([1-9]\d*)', expression)
    if special and int(special[2]) == size == 10 + int(special[1]):
        return (
            f'Согласно условию, в {locative} можно использовать десятичные цифры '
            f'и {special[1]} символов из специального набора. '
            'Десятичных цифр от 0 до 9 всего 10. '
            'Цифры и символы специального набора образуют разные группы, поэтому их количества складываем. '
        )
    raise UnsupportedCondition('unsupported composite alphabet explanation')


def encoding_bits_steps(length, size, *, genitive='пароля', locative='пароле', alphabet_formula='', alphabet_intro='', items='символов', item='символа', byte_conversion_hint=False):
    """Explain uniform symbol encoding without rounding a field to whole bytes."""
    bits = (size - 1).bit_length()
    password_bits = length * bits
    bit_word = 'бита' if bits % 10 in (2, 3, 4) and bits % 100 not in (12, 13, 14) else 'бит'
    opening = alphabet_intro or (
        _alphabet_explanation(alphabet_formula, locative, size)
        if alphabet_formula else f'Согласно условию, в {locative} могут быть использованы {size} {items}. '
    )
    html = (
        '<p>' + opening
        + 'С помощью <span data-inline-latex="N"></span> бит можно закодировать '
        '<span data-inline-latex="2^N"></span> различных вариантов. '
        f'Найдём минимальное число бит для одного {item}.</p>'
        + (formula(alphabet_formula) if alphabet_formula else '')
        + formula(rf"2^{{{bits-1}}} &lt; {size} \leq 2^{{{bits}}}")
        + formula(rf"N={bits}")
        + f'<p>Для хранения одного {item} {genitive} нужно {bits} {bit_word}. '
        f'Всего в {locative} {length} {items}, поэтому умножим число бит для одного {item} на количество {items}. '
        + ('Чтобы перевести биты в байты, разделим на 8 — число бит в одном байте.' if byte_conversion_hint else '')
        + '</p>'
        + formula(rf"{bits}\cdot {length}={password_bits}\;\text{{бит}}")
    )
    return password_bits, html


def storage_steps(length, size, *, genitive='пароля', locative='пароле', accusative='пароль', alphabet_formula='', alphabet_intro='', items='символов', item='символа'):
    password_bits, html = encoding_bits_steps(
        length, size, genitive=genitive, locative=locative, alphabet_formula=alphabet_formula,
        alphabet_intro=alphabet_intro, items=items, item=item, byte_conversion_hint=True,
    )
    password_bytes = (password_bits + 7) // 8
    byte_count = decimal_latex(Fraction(password_bits, 8))
    html += formula(rf"\frac{{{password_bits}}}{{8}}={byte_count}\;\text{{байт}}")
    if password_bits % 8:
        html += (
            f'<p>Память под {accusative} выделяется целым числом байт, '
            'поэтому округляем полученный объём вверх.</p>'
            + formula(rf"\left\lceil {byte_count}\right\rceil={password_bytes}\;\text{{байт}}")
        )
    return password_bytes, html
