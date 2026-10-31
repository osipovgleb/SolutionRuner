"""Known annual factors extend the existing compound-capitalization rule."""

import re
from dataclasses import dataclass

import sympy as sp

from ..applied.physical_questions import VALUE, scalar
from .common import UnsupportedCondition

_MONEY = rf"(?:\d{{1,3}}(?: \d{{3}})+|{VALUE})"
_NAME = r"[А-ЯЁ][а-яё]+"
_YEAR = r"\d{4}"
_QUOTED = r'(?:«[А-ЯЁа-яё -]+»|"[А-ЯЁа-яё -]+")'
_PROFIT = rf"Бизнесмен (?P<name>{_NAME}) получил в (?P<start>{_YEAR}) году прибыль в размере (?P<capital>{_MONEY}) рублей\. Каждый следующий год его прибыль увеличивалась на (?P<rate>{VALUE})% по сравнению с предыдущим годом\. Сколько рублей (?:(?P<earned>заработал) (?P<asked_name>{_NAME})|(?P<profit>составила прибыль) (?P<genitive>{_NAME})) за (?P<end>{_YEAR}) год\?"
_COMPANIES = rf"Компания (?P<name1>{_QUOTED}) начала инвестировать средства в перспективную отрасль в (?P<start1>{_YEAR}) году, имея капитал в размере (?P<capital1>{_MONEY}) долларов\. Каждый год, начиная с (?P<profit1>{_YEAR}) года, она получала прибыль, которая составляла (?P<rate1>{VALUE})% от капитала предыдущего года\. А компания (?P<name2>{_QUOTED}) начала инвестировать средства в другую отрасль в (?P<start2>{_YEAR}) году, имея капитал в размере (?P<capital2>{_MONEY}) долларов, и, начиная с (?P<profit2>{_YEAR}) года, ежегодно получала прибыль, составляющую (?P<rate2>{VALUE})% от капитала предыдущего года\. На сколько долларов капитал одной из компаний был больше капитала другой к концу (?P<end>{_YEAR}) года, если прибыль из оборота не изымалась\?"


@dataclass(frozen=True)
class Annual:
    name: str
    start: int
    end: int
    capital: sp.Rational
    rate: sp.Rational

    @property
    def periods(self):
        return self.end - self.start

    @property
    def factor(self):
        return 1 + self.rate / 100

    @property
    def result(self):
        return self.capital * self.factor**self.periods


def annual(name, start, end, capital, rate):
    a = Annual(
        name, int(start), int(end), scalar(capital.replace(" ", "")), scalar(rate)
    )
    if a.periods <= 0 or a.capital <= 0 or a.rate <= 0:
        raise UnsupportedCondition(
            "positive initial amount, annual increase and chronological years are required"
        )
    return a


@dataclass(frozen=True)
class Analysis:
    kind: str
    accounts: tuple[Annual, ...]
    result: sp.Rational


def analyze(text):
    match = re.fullmatch(_PROFIT, text)
    if match:
        name = match["name"]
        if match["asked_name"] != name and (
            not match["profit"]
            or not name.endswith(("в", "н"))
            or match["genitive"] != name + "а"
        ):
            raise UnsupportedCondition(
                "the requested businessman's name must match the annual profit data"
            )
        a = annual(name, match["start"], match["end"], match["capital"], match["rate"])
        return Analysis("profit", (a,), a.result)
    match = re.fullmatch(_COMPANIES, text)
    if match:
        accounts = tuple(
            annual(
                match["name" + str(i)][1:-1],
                match["start" + str(i)],
                match["end"],
                match["capital" + str(i)],
                match["rate" + str(i)],
            )
            for i in (1, 2)
        )
        if accounts[0].name == accounts[1].name or any(
            int(match["profit" + str(i)]) != a.start + 1
            for i, a in enumerate(accounts, 1)
        ):
            raise UnsupportedCondition(
                "distinct companies must reinvest starting in the year after their initial capital"
            )
        result = abs(accounts[0].result - accounts[1].result)
        if result == 0:
            raise UnsupportedCondition(
                "one company's final capital must be greater than the other"
            )
        return Analysis("companies", accounts, result)
    raise UnsupportedCondition(
        "the complete compound-capitalization question must be recognized"
    )
