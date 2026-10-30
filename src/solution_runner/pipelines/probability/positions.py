"""Audited Russian cardinal cases and positions in a random order."""

from .common import UnsupportedCondition, count

_STEMS = {
    "перв": 1,
    "втор": 2,
    "четверт": 4,
    "пят": 5,
    "шест": 6,
    "седьм": 7,
    "восьм": 8,
    "девят": 9,
    "десят": 10,
    "одиннадцат": 11,
    "двенадцат": 12,
    "тринадцат": 13,
    "четырнадцат": 14,
    "пятнадцат": 15,
    "шестнадцат": 16,
    "семнадцат": 17,
    "восемнадцат": 18,
    "девятнадцат": 19,
    "двадцат": 20,
}
ORDINAL = r"[а-я]+(?: [а-я]+)?"


def ordinal(token: str) -> int:
    token = token.replace("ё", "е")
    if token in ("третьим", "третьей", "третий", "третью", "третья"):
        return 3
    for stem, value in _STEMS.items():
        if token in {
            stem + ending
            for ending in ("ым", "ой", "ый", "ом", "ую", "ые", "ыми", "ая")
        }:
            return value
    parts = token.split()
    if len(parts) == 2:
        tens, unit = count(parts[0]), ordinal(parts[1])
        if tens >= 20 and tens % 10 == 0 and 1 <= unit <= 9:
            return tens + unit
    raise UnsupportedCondition("unsupported rank word")


def rank(token: str, total: int) -> int:
    value = (
        total
        if token in ("последним", "последний", "последней", "последнюю")
        else ordinal(token)
    )
    if not 1 <= value <= total:
        raise UnsupportedCondition("requested position lies outside the experiment")
    return value
