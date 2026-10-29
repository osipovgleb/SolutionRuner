"""Parse passes with separately byte-aligned personal code and department number."""

from dataclasses import dataclass
from html import escape
import re

from solution_runner.pipelines.word_problems.common import UnsupportedCondition


@dataclass(frozen=True)
class PassRecord:
    length: int
    size: int
    alphabet_formula: str
    alphabet_intro: str
    department_min: int
    department_max: int
    department_name: str
    total: int
    carrier: str = 'пропуске'


def _alphabet(description):
    if description == 'одной из 26 заглавных латинских букв':
        return 26, '', 'Согласно условию, в личном коде можно использовать 26 заглавных латинских букв. '
    if description == 'одной из 26 заглавных латинских букв или одной из 10 цифр':
        return 36, '26+10=36', (
            'Согласно условию, в личном коде можно использовать 26 заглавных латинских букв '
            'и 10 цифр — от 0 до 9. Буквы и цифры являются разными символами, поэтому их количества складываем. '
        )
    match = re.fullmatch(
        r'одной из ([1-9]\d*) разрешённых (?:прописных )?латинских букв '
        r'\(([1-9]\d*) букв(?:ы)? не используется для записи кодов\) '
        r'или одной из цифр от 1 до 9 \(ноль не используется для записи кодов\)', description,
    )
    if match:
        letters, excluded = map(int, match.groups())
        if letters + excluded != 26:
            raise UnsupportedCondition('Latin alphabet exclusions are inconsistent')
        return letters + 9, f'{letters}+9={letters+9}', (
            f'Согласно условию, в личном коде можно использовать {letters} латинских букв: '
            f'из 26 букв исключены {excluded}. Также разрешены 9 цифр — от 1 до 9, без нуля. '
            'Буквы и цифры являются разными символами, поэтому их количества складываем. '
        )
    match = re.fullmatch(
        r'русской буквой \(используется ([1-9]\d*) различных букв, каждая буква может быть заглавной или строчной\) '
        r'или одной из цифр от 1 до 9 \(ноль для записи кодов не используется\)', description,
    )
    if match and 2 <= int(match[1]) <= 33:
        letters = int(match[1])
        size = 2 * letters + 9
        return size, rf'2\cdot {letters}+9={size}', (
            f'Согласно условию, разрешены {letters} различных русских букв, каждая — в заглавном и строчном вариантах. '
            f'Заглавная и строчная буквы считаются разными символами, поэтому учитываем две группы по {letters} букв. '
            'Также разрешены 9 цифр — от 1 до 9. Сложим количества букв и цифр. '
        )
    match = re.fullmatch(
        r'заглавной (русской|латинской) буквой \(используется ([1-9]\d*) различных букв\) '
        r'или одной из цифр от 0 до ([1-9])', description,
    )
    if match:
        language, letters, last = match[1], int(match[2]), int(match[3])
        if letters > (33 if language == 'русской' else 26):
            raise UnsupportedCondition('letter count exceeds the named alphabet')
        digits = last + 1
        return letters + digits, f'{letters}+{digits}={letters+digits}', (
            f'Согласно условию, разрешены {letters} заглавных букв и цифры от 0 до {last}. '
            f'С учётом нуля это {digits} цифр. Буквы и цифры являются разными символами, поэтому их количества складываем. '
        )
    match = re.fullmatch(
        r'одной из ([1-9]\d*) допустимых заглавных букв или одной из 8 цифр '
        r'\(цифры 0 и 3 не используются\)', description,
    )
    if match:
        letters = int(match[1])
        return letters + 8, f'{letters}+8={letters+8}', (
            f'Согласно условию, разрешены {letters} заглавных букв и 8 цифр: '
            'из 10 десятичных цифр исключены 0 и 3. '
            'Буквы и цифры являются разными символами, поэтому их количества складываем. '
        )
    raise UnsupportedCondition('unsupported personal-code alphabet')


def _definition(text):
    match = re.fullmatch(r'состоит из ([1-9]\d*) символов, каждый из которых может быть (.+)', text)
    if match:
        return int(match[1]), *_alphabet(match[2])
    match = re.fullmatch(
        r'состоит из ([1-9]\d*) букв\. Для формирования кодов используется ([1-9]\d*) различных букв, '
        r'каждая из которых может быть заглавной или строчной', text,
    )
    if match:
        length, letters = map(int, match.groups())
        return length, 2 * letters, rf'2\cdot {letters}={2*letters}', (
            f'Согласно условию, разрешены {letters} различных букв, каждая — в заглавном и строчном вариантах. '
            'Заглавная и строчная буквы считаются разными символами, '
            f'поэтому учитываем две группы по {letters} букв. '
        )
    raise UnsupportedCondition('unsupported personal-code definition')


def _department(description):
    match = re.fullmatch(r'целое число от 1 до ([1-9]\d*)', description)
    if not match:
        match = re.fullmatch(r'натуральное число, не превышающее ([1-9]\d*)', description)
    if match and int(match[1]) >= 2:
        return 1, int(match[1])
    digits = {'целое трёхзначное число': 3, 'целое четырёхзначное число': 4}.get(description)
    if digits:
        return 10 ** (digits - 1), 10 ** digits - 1
    raise UnsupportedCondition('unsupported department number')


def parse_pass_record(text):
    text = ' '.join(text.replace('\u2060', '').replace('байтов', 'байт').replace('битов', 'бит').split())
    match = re.fullmatch(
        r'Каждый сотрудник предприятия получает электронный пропуск, на котором записаны личный код сотрудника, '
        r'(номер|код) подразделения и некоторая дополнительная информация\. Личный код (.+?)\. '
        r'Для записи кода на пропуске отведено минимально возможное целое число байт'
        r'(?:, при этом|\. При этом) используют посимвольное кодирование, '
        r'все символы кодируют одинаковым минимально возможным количеством бит\. '
        r'(Номер|Код) подразделения — (.+?), он записан на пропуске как двоичное число '
        r'и занимает минимально возможное целое число байт\. '
        r'Всего на пропуске хранится ([1-9]\d*) байт(?:а)? данных\. '
        r'Сколько байт выделено для хранения дополнительных сведений (?:об одном сотруднике|о сотруднике)\? '
        r'В ответе запишите только целое число — количество байт\.', text,
    )
    if match:
        if match[1].capitalize() != match[3]:
            raise UnsupportedCondition('department field names are inconsistent')
        length, size, formula, intro = _definition(match[2])
        low, high = _department(match[4])
        return PassRecord(length, size, formula, intro, low, high, f'{match[3]} подразделения', int(match[5]))
    return _parse_card(text)


def _parse_card(text):
    match = re.fullmatch(
        r'Сотрудникам компании выдают электронную карту, на которой записаны их личный код, '
        r'номер подразделения \(целое число от 1 до ([1-9]\d*)\) и дополнительная информация\. '
        r'Личный код содержит ([1-9]\d*) символов и может включать латинские буквы из 26-символьного латинского алфавита '
        r'\(заглавные и строчные буквы различаются\), десятичные цифры и специальные знаки из набора ([@#$%^&*()]+)\. '
        r'Для хранения кода используется посимвольное кодирование, все символы кодируются одинаковым минимально возможным количеством бит, '
        r'для записи кода отводится минимально возможное целое число байт\. '
        r'Номер подразделения кодируется отдельно и занимает минимально возможное целое число байт\. '
        r'Известно, что на карте хранится всего ([1-9]\d*) байт данных\. '
        r'Сколько байт занимает дополнительная информация\?', text,
    )
    if not match or int(match[1]) < 2 or len(set(match[3])) != len(match[3]):
        raise UnsupportedCondition('condition is outside the separately aligned pass template')
    special = len(match[3])
    size = 52 + 10 + special
    return PassRecord(int(match[2]), size, rf'2\cdot26+10+{special}={size}', (
        'Согласно условию, разрешены 26 заглавных и 26 строчных латинских букв, 10 десятичных цифр '
        f'и {special} специальных знаков из набора {escape(match[3])}. '
        'Заглавные и строчные буквы считаются разными символами. '
        'Сложим количества символов всех групп. '
    ), 1, int(match[1]), 'Номер подразделения', int(match[4]), 'карте')
