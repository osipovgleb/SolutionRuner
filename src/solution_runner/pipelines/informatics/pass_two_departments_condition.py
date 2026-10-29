"""Audit the distinct byte-alignment policies of passes with two department integers."""

from dataclasses import dataclass
import re
from typing import Literal

from solution_runner.pipelines.word_problems.common import UnsupportedCondition


@dataclass(frozen=True)
class TwoDepartmentsRecord:
    length: int
    letters: int
    department_min: int
    department_max: int
    packing: Literal['separate', 'joint']
    total: int

    @property
    def size(self):
        return self.letters + 10

    @property
    def alphabet_formula(self):
        return f'{self.letters}+10={self.size}'

    @property
    def alphabet_intro(self):
        return (
            f'Согласно условию, в личном коде можно использовать {self.letters} допустимых заглавных букв '
            'и 10 цифр — от 0 до 9. Буквы и цифры являются разными символами, '
            'поэтому их количества складываем. '
        )


_HEADER = (
    r'Каждый (?:сотрудник|работник) предприятия получает электронный пропуск, на котором записаны личный код сотрудника, '
    r'код подразделения и некоторая дополнительная информация\. '
    r'Личный код состоит из ([1-9]\d*) символов, каждый из которых может быть одной из ([1-9]\d*) '
    r'допустимых заглавных букв или одной из 10 цифр\. '
)
_ENCODING = r'используют посимвольное кодирование, все символы кодируют одинаковым минимально возможным количеством бит\. '
_TAIL = (
    r'Всего на пропуске хранится ([1-9]\d*) байт(?:а)? данных\. '
    r'Сколько байт выделено для хранения дополнительных сведений об одном сотруднике\? '
    r'В ответе запишите только целое число — количество байт\.'
)


def parse_two_departments_record(text):
    text = ' '.join(text.replace('\u2060', '').replace('байтов', 'байт').replace('битов', 'бит').split())
    separate = re.fullmatch(
        _HEADER
        + r'Для записи личного кода на пропуске отведено минимально возможное целое число байт\. При этом '
        + _ENCODING
        + r'Код подразделения состоит из двух (двузначных|трёхзначных) чисел, каждое из которых кодируется '
        r'как двоичное число и занимает минимально возможное целое число байт\. '
        + _TAIL, text,
    )
    if separate:
        length, letters, digits, total = separate.groups()
        count = 2 if digits == 'двузначных' else 3
        return TwoDepartmentsRecord(int(length), int(letters), 10 ** (count - 1), 10 ** count - 1, 'separate', int(total))
    joint = re.fullmatch(
        _HEADER + r'Для записи личного кода ' + _ENCODING
        + r'Код подразделения состоит из двух натуральных чисел, не превышающих ([1-9]\d*), '
        r'каждое из которых кодируется как двоичное число и занимает минимально возможное целое число бит\. '
        r'Личный код и код подразделения записываются подряд и вместе занимают минимально возможное целое число байт\. '
        + _TAIL, text,
    )
    if joint and int(joint[3]) >= 2:
        return TwoDepartmentsRecord(int(joint[1]), int(joint[2]), 1, int(joint[3]), 'joint', int(joint[4]))
    raise UnsupportedCondition('condition is outside the two-department-integer pass templates')
