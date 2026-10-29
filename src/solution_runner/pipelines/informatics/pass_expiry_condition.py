"""Parse separately byte-aligned personal codes and packed expiry dates."""

from dataclasses import dataclass
import re
from typing import Literal

from solution_runner.pipelines.word_problems.common import UnsupportedCondition


@dataclass(frozen=True)
class ExpiryRecord:
    length: int
    size: int
    year_max: int
    first_year: int
    last_year: int
    date_unit: Literal['day', 'month']
    unit_max: int

    @property
    def unit_name(self):
        return 'дня в году' if self.date_unit == 'day' else 'месяца'


def parse_expiry_record(text):
    text = ' '.join(text.replace('\u2060', '').replace('байтов', 'байт').replace('битов', 'бит').split())
    match = re.fullmatch(
        r'Каждый сотрудник предприятия получает электронный пропуск, на котором записаны личный код сотрудника '
        r'и срок действия пропуска\. Личный код состоит из ([1-9]\d*) символов, каждый из которых может быть '
        r'одной из 26 заглавных латинских букв( или 10 цифр)?\. '
        r'Для записи кода на пропуске отведено минимально возможное целое число байт, '
        r'при этом используют посимвольное кодирование, все символы кодируют одинаковым минимально возможным количеством бит\. '
        r'Срок действия записывается как номер года \(число от 0 до ([1-9]\d*), означающее год от ([1-9]\d*) до ([1-9]\d*)\) '
        r'и номер (дня в году|месяца) \(число от 1 до ([1-9]\d*)\)\. '
        r'Номер года и номер (дня|месяца) записаны на пропуске как двоичные числа, '
        r'каждое из них занимает минимально возможное число бит, а два числа вместе — минимально возможное число байт\. '
        r'Сколько байт занимает вся информация на пропуске\? В ответе запишите только целое число — количество байт\.', text,
    )
    if not match:
        raise UnsupportedCondition('condition is outside the separately aligned code-and-expiry template')
    length, digits, year_max, first, last, unit, unit_max, repeated_unit = match.groups()
    year_max, first, last, unit_max = map(int, (year_max, first, last, unit_max))
    date_unit = 'day' if unit == 'дня в году' else 'month'
    if last - first != year_max:
        raise UnsupportedCondition('year labels do not match the encoded year-number range')
    if repeated_unit != ('дня' if date_unit == 'day' else 'месяца'):
        raise UnsupportedCondition('date component names are inconsistent')
    if unit_max != (366 if date_unit == 'day' else 12):
        raise UnsupportedCondition('unsupported day-of-year or month-number range')
    return ExpiryRecord(int(length), 36 if digits else 26, year_max, first, last, date_unit, unit_max)
