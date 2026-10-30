"""Fair-coin sequences, counts and the equivalent football draw experiment."""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from html import escape
from itertools import product
from math import comb
from operator import eq, ge, gt, le

from bs4 import BeautifulSoup

from .common import (
    COUNT,
    UnsupportedCondition,
    count,
    finish,
    line,
    normalize,
    probability,
    require_content,
    rounding,
)

_TOSSES = {"однажды": 1, "дважды": 2, "трижды": 3, "четырежды": 4}
_COMPARISONS = {"exact": eq, "at-least": ge, "at-most": le, "majority": gt}
_COIN = re.compile(
    r"В случайном эксперименте симметричную монету бросают (?P<n>однажды|дважды|трижды|четырежды|\d+ раз(?:а)?)\. Найдите вероятность того, что (?P<event>.+)\."
)
_FOOTBALL = re.compile(
    rf"Перед началом футбольного матча судья бросает монетку, чтобы определить, какая из команд начнет игру с мячом\. Команда «(?P<team>[^«»]+)» играет (?P<n>{COUNT}) матч(?:а|ей)? с разными командами\. Найдите вероятность того, что в этих (?:(?:играх «(?P=team)» выиграет жребий)|(?:матчах команда «(?P=team)» начнет игру с мячом)) (?P<event>.+)\."
)


@dataclass(frozen=True)
class CoinCase:
    throws: int
    comparison: str
    successes: int
    side: int = 1
    sequence: tuple[int, ...] = ()
    team: str = ""
    places: int | None = None


def _sequence(event: str, n: int) -> tuple[int, ...] | None:
    match = re.fullmatch(
        r"наступит исход (?P<seq>[ОРOP]+) \((?P<explanation>[^()]+)\)", event
    )
    if match is None:
        return None
    sequence = match["seq"].replace("O", "О").replace("P", "Р")
    if len(sequence) != n:
        raise UnsupportedCondition("coin sequence length disagrees with the experiment")
    bits = tuple(1 if letter == "О" else 0 for letter in sequence)
    explanation = match["explanation"]
    if (
        n == 2
        and explanation
        == f"в первый раз выпадает {'орел' if bits[0] else 'решка'}, во второй — {'орел' if bits[1] else 'решка'}"
    ):
        return bits
    repeated = re.fullmatch(
        rf"(?:оба раза|все (?P<n>{COUNT}) раза) выпа(?:дет|дает) (?P<side>орел|решка)",
        explanation,
    )
    if (
        repeated
        and (n == 2 if repeated["n"] is None else count(repeated["n"]) == n)
        and len(set(bits)) == 1
        and bits[0] == (1 if repeated["side"] == "орел" else 0)
    ):
        return bits
    raise UnsupportedCondition("coin sequence conflicts with its verbal explanation")


def _event(event: str, n: int, team: str, places: int | None) -> CoinCase:
    sequence = _sequence(event, n)
    if sequence is not None:
        return CoinCase(n, "sequence", 0, sequence=sequence, places=places)
    if match := re.fullmatch(
        rf"(?P<side>орел|решка) выпадет ровно (?P<k>{COUNT}) раз(?:а)?", event
    ):
        return CoinCase(
            n, "exact", count(match["k"]), int(match["side"] == "орел"), places=places
        )
    if match := re.fullmatch(
        rf"(?P<side>орел|решка) выпадет (?:оба раза|все (?P<k>{COUNT}) раза)", event
    ):
        if n == 2 if match["k"] is None else count(match["k"]) == n:
            return CoinCase(n, "exact", n, int(match["side"] == "орел"), places=places)
        raise UnsupportedCondition("all-throws wording disagrees with the throw count")
    if match := re.fullmatch(
        rf"выпадет хотя бы (?P<k>{COUNT}) (?P<side>орла|орлов|решки|решек)", event
    ):
        return CoinCase(
            n,
            "at-least",
            count(match["k"]),
            int(match["side"].startswith("ор")),
            places=places,
        )
    if match := re.fullmatch(
        r"(?P<side>орел|решка) выпала? больше раз, чем (?P<other>орел|решка)", event
    ):
        if match["side"] == match["other"]:
            raise UnsupportedCondition("coin sides in a comparison must differ")
        return CoinCase(n, "majority", 0, int(match["side"] == "орел"), places=places)
    if team and (
        match := re.fullmatch(
            rf"(?P<kind>ровно|не более|не менее) (?P<k>{COUNT}) раз(?:а)?", event
        )
    ):
        kind = {"ровно": "exact", "не более": "at-most", "не менее": "at-least"}[
            match["kind"]
        ]
        return CoinCase(n, kind, count(match["k"]), team=team, places=places)
    raise UnsupportedCondition("unsupported complete coin event")


def parse(text: str) -> CoinCase:
    text, places = rounding(normalize(text))
    if match := _COIN.fullmatch(text):
        n = _TOSSES[match["n"]] if match["n"] in _TOSSES else int(match["n"].split()[0])
        return _event(match["event"], n, "", places)
    if match := _FOOTBALL.fullmatch(text):
        return _event(match["event"], count(match["n"]), match["team"], places)
    raise UnsupportedCondition("unsupported fair-coin experiment")


def outcomes(case: CoinCase):
    if not 1 <= case.throws <= 6:
        raise UnsupportedCondition("coin enumeration supports one to six throws")
    domain = list(product((1, 0), repeat=case.throws))
    if case.comparison == "sequence":
        return domain, [row for row in domain if row == case.sequence]
    comparator = _COMPARISONS.get(case.comparison)
    if comparator is None:
        raise UnsupportedCondition("unknown coin comparison")
    threshold = (
        Fraction(case.throws, 2) if case.comparison == "majority" else case.successes
    )
    return domain, [
        row
        for row in domain
        if comparator(sum(bit == case.side for bit in row), threshold)
    ]


def render(case: CoinCase, parent_solution_html: str) -> tuple[str, str]:
    if not parent_solution_html.strip():
        raise UnsupportedCondition(
            "the parent solution is required to preserve coin methods"
        )
    domain, favorable = outcomes(case)
    rich = "Формула Бернулли" in BeautifulSoup(
        parent_solution_html, "html.parser"
    ).get_text(" ", strip=True).replace("\u00ad", "")

    def display(row):
        if case.team:
            return "".join(map(str, row))
        if case.throws == 2 and not rich:
            return "–".join("орел" if bit else "решка" for bit in row)
        return "".join("О" if bit else "Р" for bit in row)

    listed = ", ".join(display(row) for row in domain)
    selected = ", ".join(display(row) for row in favorable) or "нет"
    intro = (
        f"<p>Обозначим выигрыш жребия командой «{escape(case.team)}» цифрой 1, проигрыш — цифрой 0.</p>"
        if case.team
        else "<p>Обозначим орла буквой О, решку — буквой Р. Все последовательности равновозможны.</p>"
    )
    html = intro + "<p>Возможные исходы: " + listed + ".</p>"
    html += line(rf"N_{{\mathrm{{общ}}}}={len(domain)}")
    html += (
        "<p>Благоприятные исходы: "
        + selected
        + ".</p>"
        + line(rf"N_{{\mathrm{{благ}}}}={len(favorable)}")
    )
    answer, calculation = probability(len(favorable), len(domain), case.places)
    html += calculation
    if not rich:
        return answer, html
    n, m = case.throws, len(favorable)
    html += "<p>Каждое бросание даёт два варианта, поэтому можно подсчитать исходы с помощью правила произведения:</p>"
    html += line(rf"N_{{\mathrm{{общ}}}}=2^{{{n}}}={len(domain)}")
    html += (
        "<p>Требуемому событию соответствуют последовательности: "
        + selected
        + ".</p>"
        + calculation
    )
    ks = sorted({sum(bit == case.side for bit in row) for row in favorable})
    fixed_sequence = case.comparison == "sequence"
    combinations = (
        "1" if fixed_sequence else "+".join(rf"C_{{{n}}}^{{{k}}}" for k in ks) or "0"
    )
    count_by_combinations = 1 if fixed_sequence else sum(comb(n, k) for k in ks)
    if count_by_combinations != m:
        raise UnsupportedCondition(
            "a fixed sequence cannot use a count-only combinatorial method"
        )
    html += (
        "<p>Приведём комбинаторное решение. Порядок сторон задан полностью, поэтому имеется ровно одна благоприятная последовательность:</p>"
        if fixed_sequence
        else "<p>Приведём решение, основанное на комбинаторных формулах. Выбираем позиции требуемой стороны монеты:</p>"
    )
    html += (
        line(rf"N_{{\mathrm{{общ}}}}=2^{{{n}}}={len(domain)}")
        + line(rf"N_{{\mathrm{{благ}}}}={combinations}={m}")
        + calculation
    )
    html += "<p>Приведём решение, использующее теоремы о вероятностях. Вероятность каждой последовательности равна произведению вероятностей независимых бросаний. Благоприятные последовательности несовместны, поэтому их вероятности складываются:</p>"
    html += (
        line(
            rf"P={m}\cdot\left(\frac{{1}}{{2}}\right)^{{{n}}}=\frac{{{m}}}{{{len(domain)}}}"
        )
        + calculation
    )
    bernoulli = (
        "+".join(
            ("" if fixed_sequence else rf"C_{{{n}}}^{{{k}}}")
            + rf"\left(\frac{{1}}{{2}}\right)^{{{k}}}\left(\frac{{1}}{{2}}\right)^{{{n - k}}}"
            for k in ks
        )
        or "0"
    )
    html += (
        "<p>Для заданной последовательности перемножим вероятности всех её сторон. Комбинаторный множитель не нужен, поскольку порядок фиксирован:</p>"
        if fixed_sequence
        else "<p>Формула Бернулли. Сложим вероятности всех допустимых количеств выпадений требуемой стороны:</p>"
    )
    html += line("P=" + bernoulli) + calculation
    html += "<p>В общем случае вероятность ровно k успехов в n независимых испытаниях с вероятностью успеха p равна:</p>"
    html += line(r"P_n(k)=C_n^k p^k(1-p)^{n-k}")
    return answer, html


def build_context_repair_plan(context, *, parent_solution_html: str = ""):
    _, condition, answer_section, solution, text = require_content(
        context, allow_inline_latex=True
    )
    answer, html = render(parse(text), parent_solution_html)
    return finish(condition, answer_section, solution, answer, html)
