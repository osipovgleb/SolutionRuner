"""Parse audited single-code records with an unknown whole-byte extra field."""

from copy import deepcopy
from dataclasses import dataclass
import re

from bs4 import BeautifulSoup

from solution_runner.pipelines.word_problems.common import UnsupportedCondition, require_content


@dataclass(frozen=True)
class Record:
    length: int
    size: int
    users: int
    total: int
    genitive: str = 'пароля'
    locative: str = 'пароле'
    accusative: str = 'пароль'
    entity: str = 'пользователе'
    alphabet_formula: str = ''


def read_content(context):
    # Some source alphabets use semantic <var> tags for individual letters.
    # Unwrap only verified single-letter identifiers in the parsing copy.
    copy = deepcopy(context)
    for section in (copy.get('normalized_content') or {}).get('sections', []):
        if section.get('key') != 'condition':
            continue
        soup = BeautifulSoup(section.get('html', ''), 'html.parser')
        changed = False
        for tag in soup.find_all('var'):
            letter = tag.get_text()
            if (set(tag.attrs) == {'data-math-identifier'} and len(letter) == 1
                    and letter.isalpha() and tag['data-math-identifier'] == letter
                    and not tag.find(True)):
                tag.unwrap()
                changed = True
        if changed:
            section['html'] = str(soup)
    parsed = require_content(copy, allow_inline_latex=True)
    original = require_content(context, allow_inline_latex=True) if copy == context else None
    if original is not None:
        return original
    condition = next(s for s in context['normalized_content']['sections'] if s['key'] == 'condition')
    return parsed[0], condition, parsed[2], parsed[3], parsed[4]


def _alphabet(descriptor):
    match = re.fullmatch(r' и содержащий только символы из ([1-9]\d*)-символьного набора: (.+)', descriptor)
    if match:
        size = int(match[1])
        letters = [x.strip() for x in match[2].split(',')]
        if size < 2 or len(letters) != size or len(set(letters)) != size or any(len(x) != 1 for x in letters):
            raise UnsupportedCondition('alphabet does not match its declared size')
        return size, ''
    if re.fullmatch(r' и содержащий только символы из 26-символьного набора (?:латинского алфавита|прописных латинских букв)', descriptor):
        return 26, ''
    if descriptor == ' и содержащий цифры и прописные символы латинского алфавита (всего 36 возможных символов)':
        return 36, r'10+26=36'
    if descriptor in (
        ' и содержащий только прописные символы латинского алфавита (таких символов 26)',
        ' и содержащий только заглавные буквы латинского алфавита — всего 26 возможных символов',
        ' и содержащий только заглавные буквы латинского 26-символьного алфавита',
    ):
        return 26, ''
    if descriptor == ' и содержащий только прописные буквы латинского 26-символьного алфавита и десять цифр':
        return 36, r'26+10=36'
    if descriptor == ' и содержащий только символы из 62-символьного набора, содержащего все латинские буквы (заглавные и строчные) и десятичные цифры':
        return 62, r'2\cdot26+10=62'
    if re.fullmatch(r'\. Для построения идентификатора используют только (?:строчные|заглавные|прописные) латинские буквы \(26 букв\)', descriptor):
        return 26, ''
    if descriptor == ('. Из соображений информационной безопасности каждый пароль должен содержать хотя бы 1 десятичную цифру, '
                       'как прописные, так и строчные латинские буквы (в латинском алфавите 26 букв), '
                       'а также не менее 1 символа из 6-символьного набора: «&», «#», «$», «*», «!», «@»'):
        return 68, r'10+2\cdot26+6=68'
    raise UnsupportedCondition('unsupported single-code alphabet description')


_ANSWER_SUFFIX = r'(?: В ответе запишите только целое число [—–] количество байт\.)?'
_QUESTION = r'Сколько байт выделено для хранения дополнительных сведений об одном пользователе\?'


def parse_record(text):
    text = ' '.join(text.replace('\u2060', '').replace('Байт', 'байт').split())
    text = text.replace('байтов', 'байт').replace('битов', 'бит')
    header, separator, body = text.partition('. В базе данных ')
    prefix = r'При регистрации в компьютерной системе '
    password = re.fullmatch(prefix + r'каждому пользователю выдаётся пароль, состоящий из ([1-9]\d*) символов(.+)', header)
    identifier = re.fullmatch(prefix + r'для каждого пользователя формируется индивидуальный идентификатор, состоящий из ([1-9]\d*) символов(.+)', header)
    if separator and (password or identifier):
        match = password or identifier
        size, alphabet_formula = _alphabet(match[2])
        gen, loc, acc, plural = ('пароля', 'пароле', 'пароль', 'паролей') if password else ('идентификатора', 'идентификаторе', 'идентификатор', 'идентификаторов')
        if alphabet_formula and size == 68 and int(match[1]) < 4:
            raise UnsupportedCondition('password is too short for its mandatory symbol classes')
        tail = re.fullmatch(
            r'для хранения (?:сведений о каждом пользователе|каждого пароля) отведено одинаковое(?: и)? минимально возможное целое число байт\. '
            rf'При этом используют посимвольное кодирование {plural}, все символы кодируют одинаковым(?: и)? минимально возможным количеством бит\. '
            rf'Кроме(?:, собственно, | (?:собственно )?){gen},? для каждого пользователя (?:в )?системе хранятся дополнительные сведения, для чего выделено '
            r'(?:целое число байт[;,] (?:это число )?одно и то же для всех пользователей|одинаковое целое количество байт на каждого пользователя)\. '
            r'Для хранения (?:сведений|информации) о ([1-9]\d*) пользователях потребовалось ([1-9]\d*) байт\. '
            + _QUESTION + _ANSWER_SUFFIX, body,
        )
        if tail:
            return Record(int(match[1]), size, int(tail[1]), int(tail[2]), gen, loc, acc, alphabet_formula=alphabet_formula)
    return _parse_code_record(text)


def _parse_code_record(text):
    server = r'При регистрации на сервере каждый пользователь получает уникальный персональный код, состоящий из ([1-9]\d*) символ(?:ов|а), каждый из которых может быть (.+?)\. '
    objects = r'Каждый объект, зарегистрированный в информационной системе, получает уникальный код из ([1-9]\d*) символов, каждый из которых может быть (.+?)\. '
    header = re.match(server, text) or re.match(objects, text)
    if not header:
        raise UnsupportedCondition('condition is outside the single-code extra-bytes template')
    descriptor = header[2]
    if descriptor == 'одной из 26 заглавных латинских букв':
        size, formula = 26, ''
    elif descriptor == 'одной из 26 заглавных латинских букв или одной из 10 цифр':
        size, formula = 36, r'26+10=36'
    elif descriptor == 'одной из 26 заглавных или строчных латинских букв':
        size, formula = 52, r'2\cdot26=52'
    elif descriptor == 'одной из 10 первых латинских букв (A, B, C, D, E, F, G, H, I, J)':
        size, formula = 10, ''
    else:
        raise UnsupportedCondition('unsupported code alphabet')
    is_server = text.startswith('При регистрации на сервере ')
    extra = (r'При этом в базе данных сервера формируется запись, содержащая этот код и дополнительную информацию о пользователе\. ' if is_server else '')
    extra += (r'Для представления кода используют посимвольное кодирование, все символы кодируют одинаковым минимально возможным количеством бит, '
              r'а для кода в целом выделяется минимально возможное целое количество байт\. ')
    if is_server:
        extra += (r'Для хранения данных о ([1-9]\d*) пользователях потребовалось ([1-9]\d*) байт\. '
                  r'Сколько байт выделено для хранения дополнительной информации об одном пользователе\?')
    else:
        extra += (r'Кроме того, для каждого объекта в системе выделен одинаковый объём памяти для хранения содержательной информации\. '
                  r'Для хранения данных \(код и содержательная информация\) о ([1-9]\d*) объектах потребовалось ([1-9]\d*) байт\. '
                  r'Сколько байт выделено для хранения содержательной информации об одном объекте\?')
    tail = re.fullmatch(extra + _ANSWER_SUFFIX, text[header.end():])
    if not tail:
        raise UnsupportedCondition('code record is outside the whole-byte extra-information template')
    return Record(int(header[1]), size, int(tail[1]), int(tail[2]), 'кода', 'коде', 'код',
                  'пользователе' if is_server else 'объекте', formula)
