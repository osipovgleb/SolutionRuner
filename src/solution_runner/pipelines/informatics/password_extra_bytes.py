"""Compute whole-byte password storage and per-user additional information."""

import re
from fractions import Fraction

from solution_runner.pipelines.word_problems.common import (
    UnsupportedCondition, decimal_latex, finalize, require_content,
)


_CONDITION = re.compile(
    r"При регистрации в компьютерной системе каждому пользователю выдаётся пароль, "
    r"состоящий из (?P<length>[1-9]\d*) символов и содержащий только символы из "
    r"(?P<size>[1-9]\d*)-символьного набора: (?P<alphabet>[^.]+)\. "
    r"В базе данных для хранения сведений о каждом пользователе отведено одинаковое "
    r"и минимально возможное целое число байт\. При этом используют посимвольное "
    r"кодирование паролей, все символы кодируют одинаковым и минимально возможным "
    r"количеством бит\. Кроме собственно пароля, для каждого пользователя в системе "
    r"хранятся дополнительные сведения, для чего выделено целое число байт; "
    r"это число одно и то же для всех пользователей\. Для хранения сведений о "
    r"(?P<users>[1-9]\d*) пользователях потребовалось (?P<total>[1-9]\d*) байт\. "
    r"Сколько байт выделено для хранения дополнительных сведений об одном пользователе\? "
    r"В ответе запишите только целое число [—–] количество байт\."
)


def _formula(latex: str) -> str:
    return f'<p><span data-inline-latex="{latex}"></span></p>'


def build_context_repair_plan(context):
    _, condition, answer_section, solution_section, text = require_content(
        context, allow_inline_latex=True,
    )
    # Source typography may contain a word joiner after the alphabet-size hyphen.
    match = _CONDITION.fullmatch(text.replace("\u2060", ""))
    if match is None:
        raise UnsupportedCondition("condition is outside the password-extra-bytes template")
    length, size, users, total = (int(match[key]) for key in ("length", "size", "users", "total"))
    alphabet = [symbol.strip() for symbol in match["alphabet"].split(",")]
    if size < 2 or len(alphabet) != size or len(set(alphabet)) != size or any(len(s) != 1 for s in alphabet):
        raise UnsupportedCondition("alphabet does not match its declared size")
    bits = (size - 1).bit_length()
    password_bits = length * bits
    password_bytes = (password_bits + 7) // 8
    byte_count = decimal_latex(Fraction(password_bits, 8))
    rounding = (
        '<p>Память под пароль выделяется целым числом байт, '
        'поэтому округляем полученный объём вверх.</p>'
        + _formula(rf"\left\lceil {byte_count}\right\rceil={password_bytes}\;\text{{байт}}")
        if password_bits % 8 else ''
    )
    per_user, remainder = divmod(total, users)
    extra = per_user - password_bytes
    if remainder or extra < 0:
        raise UnsupportedCondition("memory allocation is inconsistent with whole bytes per user")
    solution = (
        '<p>Согласно условию, в пароле могут быть использованы '
        f'{size} символов. С помощью <span data-inline-latex="N"></span> бит можно закодировать '
        '<span data-inline-latex="2^N"></span> различных вариантов. '
        'Найдём минимальное число бит для одного символа.</p>'
        + _formula(rf"2^{{{bits-1}}} &lt; {size} \leq 2^{{{bits}}}")
        + _formula(rf"N={bits}")
        + f'<p>Для хранения всех {length} символов пароля нужно следующее число бит. '
        'Чтобы перевести биты в байты, разделим на 8 — число бит в одном байте.</p>'
        + _formula(rf"{bits}\cdot {length}={password_bits}\;\text{{бит}}")
        + _formula(rf"\frac{{{password_bits}}}{{8}}={byte_count}\;\text{{байт}}")
        + rounding
        + '<p>Пусть количество памяти под дополнительные сведения об одном пользователе равно '
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
