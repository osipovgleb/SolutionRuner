"""Audited total-storage conditions with one uniformly encoded field per record."""

from dataclasses import dataclass
import re

from solution_runner.pipelines.word_problems.common import UnsupportedCondition

from .password_extra_bytes_condition import _alphabet


@dataclass(frozen=True)
class TotalRecord:
    length: int
    size: int
    users: int
    extra: int = 0
    genitive: str = 'пароля'
    locative: str = 'пароле'
    accusative: str = 'пароль'
    entity: str = 'пользователе'
    entities: str = 'пользователей'
    unit: str = 'байт'
    items: str = 'символов'
    item: str = 'символа'
    alphabet_formula: str = ''


_POS = r'[1-9]\d*(?: \d{3})*'
_SUFFIX = r'(?: В ответе запишите только целое число [—–] количество байт\.)?'


def _integer(token):
    return int(token.replace(' ', ''))


def _total_alphabet(descriptor):
    letters = re.fullmatch(r' и содержащий только символы из ([1-9]\d*)-буквенного набора (.+)', descriptor)
    if letters:
        descriptor = f' и содержащий только символы из {letters[1]}-символьного набора: {letters[2]}'
    if descriptor in (
        ' и содержащий только символы из 26-символьного латинского алфавита, используются только прописные буквы',
        '. В качестве символов используют прописные буквы латинского алфавита, то есть 26 различных символов',
    ):
        return 26, ''
    subset = re.fullmatch(r'\. Для построения идентификатора используют только прописные латинские буквы \(([1-9]\d*) букв\)', descriptor)
    if subset:
        size = int(subset[1])
        if not 2 <= size <= 26:
            raise UnsupportedCondition('invalid Latin-letter subset size')
        return size, ''
    subset = re.fullmatch(r'\. Для построения идентификатора используют ([1-9]\d*) букв из определённого набора', descriptor)
    if subset and int(subset[1]) >= 2:
        return int(subset[1]), ''
    if descriptor == '. Для построения идентификатора используют только латинские буквы (26 заглавных и 26 строчных букв)':
        return 52, r'26+26=52'
    return _alphabet(descriptor)


def _ending(text):
    patterns = (
        r'Определите объём памяти(?: \(в байтах\))?, необходимый для хранения (?:сведений|данных) о '
        rf'(?P<users>{_POS}) (?P<entities>пользователях|объектах)\.(?: \(Ответ дайте в байтах\.\))?',
        rf'Сколько байт нужно (?:выделить )?для хранения сведений о (?P<users>{_POS}) (?P<entities>пользователях)\?',
    )
    for pattern in patterns:
        match = re.fullmatch(pattern + _SUFFIX, text)
        if match:
            return _integer(match['users']), match['entities']
    raise UnsupportedCondition('unsupported total-storage question or unit')


def parse_total_record(text):
    text = ' '.join(text.replace('\u2060', '').split())
    text = re.sub(r'\bбайта\b', 'байт', text.replace('байтов', 'байт').replace('битов', 'бит'))
    text = text.replace('кодируются', 'кодируют')
    header, separator, body = text.partition('. В базе данных ')
    prefix = 'При регистрации в компьютерной системе '
    match = re.fullmatch(prefix + r'каждому пользователю выдаётся (?P<kind>пароль|идентификатор), состоящий из (?P<length>[1-9]\d*) символов(?P<alphabet>.+)', header)
    identifier = re.fullmatch(prefix + r'для каждого пользователя формируется индивидуальный идентификатор, состоящий из (?P<length>[1-9]\d*) символов(?P<alphabet>.+)', header)
    if separator and (match or identifier):
        kind = match['kind'] if match else 'идентификатор'
        match = match or identifier
        size, alphabet_formula = _total_alphabet(match['alphabet'])
        if size == 68 and int(match['length']) < 4:
            raise UnsupportedCondition('password is too short for mandatory symbol classes')
        gen, loc, plural = ('пароля', 'пароле', 'паролей') if kind == 'пароль' else ('идентификатора', 'идентификаторе', 'идентификаторов')
        encoding = re.match(
            r'для хранения (?:сведений о каждом пользователе|каждого пароля) отведено одинаковое(?: и)? минимально возможное целое число байт\. '
            rf'При этом используют посимвольное кодирование {plural}, все символы кодируют одинаковым(?: и)? минимально возможным количеством бит\. ', body)
        if encoding:
            tail = body[encoding.end():]
            extra = 0
            field = re.match(rf'Кроме (?:собственно )?{gen},? для каждого (?P<entity>пользователя|объекта) в системе хранятся дополнительные сведения, '
                             r'для чего (?:отведено|выделено) (?P<extra>0|[1-9]\d*) байт(?: на (?:одного пользователя|каждого пользователя|один объект))?\. ', tail)
            if field:
                extra = int(field['extra'])
                tail = tail[field.end():]
            users, entities = _ending(tail)
            if field and (field['entity'] == 'объекта') != (entities == 'объектах'):
                raise UnsupportedCondition('extra field and record count use different entities')
            return TotalRecord(int(match['length']), size, users, extra, gen, loc, kind,
                               'объекте' if entities == 'объектах' else 'пользователе',
                               'объектов' if entities == 'объектах' else 'пользователей', alphabet_formula=alphabet_formula)
    return _other_total_record(text)


def _other_total_record(text):
    match = re.fullmatch(
        r'Для регистрации на сайте некоторой страны пользователю необходимо придумать пароль длиной ровно ([1-9]\d*) символов\. '
        r'В пароле можно использовать только прописные буквы английского алфавита, то есть 26 символов\. '
        r'Информация о пользователе хранится с помощью минимально возможного целого количества байт\. '
        r'Каждый символ в пароле кодируется одинаковым и минимально возможным количеством бит\. '
        r'Для хранения дополнительной информации на одного пользователя отводится (0|[1-9]\d*) байт\. '
        rf'Определите объем памяти в байтах, необходимый для хранения информации о ({_POS}) пользователях\.', text)
    if match:
        return TotalRecord(int(match[1]), 26, _integer(match[3]), int(match[2]))
    match = re.fullmatch(
        r'Каждый объект, зарегистрированный в информационной системе, получает уникальный код из ([1-9]\d*) символов, '
        r'каждый из которых может быть одной из 26 заглавных латинских букв или одной из 10 цифр\. '
        r'Для представления кода используют посимвольное кодирование, все символы кодируют одинаковым минимально возможным количеством бит, '
        r'а для кода в целом выделяется минимально возможное целое количество байт\. '
        r'Кроме того, для каждого объекта в системе выделено (0|[1-9]\d*) байт для хранения содержательной информации\. '
        rf'Сколько байт потребуется для хранения данных \(код и содержательная информация\) о ({_POS}) объектах\?'+_SUFFIX, text)
    if match:
        return TotalRecord(int(match[1]), 36, _integer(match[3]), int(match[2]), 'кода', 'коде', 'код',
                           'объекте', 'объектов', alphabet_formula=r'26+10=36')
    match = re.fullmatch(
        r'При регистрации в компьютерной системе каждому пользователю выдается идентификатор из ([1-9]\d*) символа, '
        r'каждый из которых может быть десятичной цифрой или одним из ([1-9]\d*) символов из специального набора\. '
        r'Каждый символ кодируется с помощью одинакового и минимального количества бит\. '
        r'Идентификатор же записывается в памяти с помощью минимально возможного целого количества байт\. '
        rf'Сколько килобайт потребуется для хранения идентификаторов ({_POS}) пользователей\?', text)
    if match:
        size = int(match[2]) + 10
        return TotalRecord(int(match[1]), size, _integer(match[3]), genitive='идентификатора', locative='идентификаторе',
                           accusative='идентификатор', unit='Кбайт', alphabet_formula=rf'10+{match[2]}={size}')
    match = re.fullmatch(
        r'В базе данных хранится информация об объектах определённой структуры\. '
        r'Каждый объект описывается как последовательность из ([1-9]\d*) простых элементов, '
        r'при этом всего используется ([1-9]\d*) различных простых элемент(?:ов|а)\. '
        r'Каждое описание объекта записывается как последовательность кодов простых элементов, '
        r'при этом код каждого элемента содержит одинаковое для всех элементов минимально возможное число бит, '
        r'а для описания в целом отводится минимально возможное целое число байт\. '
        rf'Сколько Кбайт(?:ов)? потребуется для хранения ({_POS}) описаний, построенных по такой схеме\? '
        r'В ответе запишите только число [—–] количество Кбайт(?:ов)?\.', text)
    if match and int(match[2]) >= 2:
        return TotalRecord(int(match[1]), int(match[2]), _integer(match[3]), genitive='описания', locative='описании',
                           accusative='описание', entities='описаний', unit='Кбайт', items='элементов', item='элемента')
    raise UnsupportedCondition('condition is outside the single-field total-storage templates')
