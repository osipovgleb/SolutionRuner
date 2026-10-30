"""A conditional record maximum in a tournament won by the stronger team."""

import re
from fractions import Fraction
from html import escape
from itertools import combinations
from math import comb, factorial

from . import solution_diagrams as diagrams
from .bernoulli import fmt, result
from .common import UnsupportedCondition, line, normalize
from .without_replacement import integer

_ORDINALS = (
    "первый",
    "второй",
    "третий",
    "четвертый",
    "пятый",
    "шестой",
    "седьмой",
    "восьмой",
    "девятый",
    "десятый",
    "одиннадцатый",
    "двенадцатый",
    "тринадцатый",
    "четырнадцатый",
    "пятнадцатый",
    "шестнадцатый",
    "семнадцатый",
    "восемнадцатый",
    "девятнадцатый",
    "двадцатый",
)
_PAST = r"(?:\d+|одной|двух|трех|четырех|пяти|шести|семи|восьми|девяти|десяти)"
_PATTERN = re.compile(
    rf"В викторине участвуют (?P<n>\d+) команд\. Все команды разной силы, и в каждой встрече выигрывает та команда, которая сильнее\. В первом раунде встречаются две случайно выбранные команды\. Ничья невозможна\. Проигравшая команда выбывает из викторины, а победившая команда играет со следующим случайно выбранным соперником\. Известно, что в первых (?P<k>{_PAST}) играх победила команда А\. Какова вероятность того, что эта команда выиграет (?P<next>"
    + "|".join(_ORDINALS)
    + r"|\d+(?:-й)?) раунд\?"
)
_PDF = "42e02105-7c04-445a-866c-8159f3c00697"
_PROOF_URL = "https://math-ege.sdamgia.ru/get_file?id=135669"


def record_ranks(n, k):
    if (
        not isinstance(n, int)
        or not isinstance(k, int)
        or not 3 <= n <= 30
        or not 1 <= k <= n - 2
    ):
        raise UnsupportedCondition(
            "the tournament needs a next opponent after 1–28 wins among 3–30 teams"
        )
    total = comb(n, k + 1)
    return tuple(
        (r, comb(r - 1, k), Fraction(r - k - 1, n - k - 1)) for r in range(k + 1, n + 1)
    ), total


def _input(context):
    content, condition, answer, solution, text = diagrams.read(context)
    match = _PATTERN.fullmatch(normalize(text))
    if match is None:
        raise UnsupportedCondition("unsupported complete record-tournament condition")
    n, k = int(match["n"]), integer(match["k"])
    following = (
        _ORDINALS.index(match["next"]) + 1
        if match["next"] in _ORDINALS
        else int(match["next"].removesuffix("-й"))
    )
    if following != k + 1:
        raise UnsupportedCondition(
            "the requested round must immediately follow the known wins"
        )
    record_ranks(n, k)
    if any(
        a.get("asset_id") != _PDF or a.get("kind") != "attachment"
        for a in content.get("assets", [])
    ):
        raise UnsupportedCondition(
            "only the audited general proof attachment is supported"
        )
    return content, condition, answer, solution, n, k


def _proof(content):
    assets = content.get("assets", [])
    if assets:
        asset = assets[0]
        key = escape(asset["asset_key"], quote=True)
        url = escape(asset.get("url") or "/assets/" + _PDF, quote=True)
        link = f'<a data-asset-id="{_PDF}" data-asset-key="{key}" href="{url}" rel="noreferrer noopener" target="_blank">ЕГЭ-викторина</a>'
        keys = (asset["asset_key"],)
    else:
        link = f'<a href="{_PROOF_URL}" rel="noreferrer noopener" target="_blank">ЕГЭ-викторина</a>'
        keys = ()
    return (
        "<p>Другое доказательство приведено в работе И. В. Яковлева " + link + ".</p>",
        keys,
    )


def _permutation_cases(n, k, rows, value):
    factor = factorial(k) * factorial(n - k - 1)
    total = factorial(n) // (k + 1)
    html = "<p>Способ 4. Рассмотрим случаи по силе A среди всех команд. Нумеруем силы от 1 до n. При ранге r первые k соперников выбираются среди r−1 более слабых. Перестановок остальных команд, согласованных с известными победами:</p>"
    html += line(r"N_r=C_{r-1}^k k!(n-k-1)!")
    html += "<table><tbody><tr><th>Ранг A</th><th>Перестановки</th><th>Вероятность следующей победы</th></tr>"
    for r, ways, p in reversed(rows):
        html += (
            f"<tr><td>{r}</td><td>{ways * factor}</td><td>"
            + line(fmt(p))
            + "</td></tr>"
        )
    html += "</tbody></table>" + line(rf"N={total}")
    html += line(
        r"P="
        + "+".join(
            rf"\frac{{{ways * factor}}}{{{total}}}\cdot {fmt(p)}"
            for _, ways, p in reversed(rows)
        )
        + "="
        + fmt(value)
    )
    return html


def _subset_cases(n, k, rows, total, value):
    html = "<p>Способ 5. Переберём наборы сил первых k+1 участников. В каждом наборе A — самая сильная. Все наборы равновозможны. Среди ещё не игравших команд следующий соперник выбирается равновероятно:</p>"
    html += line(rf"N=C_{{{n}}}^{{{k + 1}}}={total}")
    if total <= 40:
        html += "<table><tbody><tr><th>Первые k+1 сил, A последняя</th><th>Оставшиеся силы</th><th>Вероятность победы A</th></tr>"
        for group in combinations(range(1, n + 1), k + 1):
            remaining = tuple(r for r in range(1, n + 1) if r not in group)
            p = Fraction(sum(r < group[-1] for r in remaining), len(remaining))
            html += (
                "<tr><td>"
                + ", ".join(map(str, group))
                + "</td><td>"
                + ", ".join(map(str, remaining))
                + "</td><td>"
                + line(fmt(p))
                + "</td></tr>"
            )
        html += "</tbody></table>"
    html += "<p>Тот же подсчёт можно сгруппировать по наибольшему рангу r. Выбираем k меньших рангов, оставшихся более слабых команд r−1−k, а всех ещё не игравших n−k−1:</p>"
    html += (
        "<table><tbody><tr><th>r</th><th>Наборов</th><th>Вероятность победы</th></tr>"
    )
    for r, ways, p in rows:
        html += f"<tr><td>{r}</td><td>{ways}</td><td>" + line(fmt(p)) + "</td></tr>"
    html += "</tbody></table>" + line(
        r"P=\frac{1}{C_n^{k+1}}\sum_{r=k+1}^n C_{r-1}^k\frac{r-1-k}{n-k-1}"
    )
    html += line(
        r"P="
        + "+".join(rf"\frac{{{ways}}}{{{total}}}\cdot {fmt(p)}" for _, ways, p in rows)
        + "="
        + fmt(value)
    )
    return html


def build_context_repair_plan(context):
    content, condition, answer_section, solution, n, k = _input(context)
    rows, total = record_ranks(n, k)
    value = sum((Fraction(ways, total) * p for _, ways, p in rows), Fraction(0))
    html = f"<p>Способ 1. Команда A уже обыграла {k} соперников. Расставим их по возрастанию силы, A стоит последней. Следующая команда может занимать любое из {k + 2} равновероятных мест вставки. В {k + 1} из них она слабее A:</p>"
    html += line(rf"P=\frac{{{k + 1}}}{{{k + 2}}}={fmt(value)}")
    html += "<p>В общем случае после k побед имеется k+2 мест вставки; вероятность следующей победы равна (k+1)/(k+2), а поражения — 1/(k+2). Общее число команд не входит в ответ, но очередной соперник должен ещё оставаться.</p>"
    proof, keys = _proof(content)
    html += proof
    html += "<p>Способ 2. Подсчитаем перестановки всех команд по силе. Зафиксированные k проигравших стоят слева от A, их взаимный порядок произволен. Остальные команды размещаются без ограничений. Для следующей победы ещё один соперник должен оказаться левее A:</p>"
    denominator = factorial(n) // (k + 1)
    numerator = factorial(n) // (k + 2)
    html += line(rf"N=k!(k+2)(k+3)\cdots n=\frac{{n!}}{{k+1}}={denominator}")
    html += line(rf"M=(k+1)!(k+3)\cdots n=\frac{{n!}}{{k+2}}={numerator}")
    html += line(
        rf"P=\frac{{M}}{{N}}=\frac{{{numerator}}}{{{denominator}}}={fmt(value)}"
    )
    html += f"<p>Способ 3. Найдём вероятность победы следующего соперника X. Он победит тогда и только тогда, когда окажется сильнейшим среди {k + 2} уже выбранных команд. Его относительное место равновероятно:</p>"
    html += line(rf"P(X\text{{ победит}})=\frac1{{{k + 2}}}")
    html += line(rf"P(A\text{{ победит}})=1-\frac1{{{k + 2}}}={fmt(value)}")
    html += _permutation_cases(n, k, rows, value) + _subset_cases(
        n, k, rows, total, value
    )
    html += "<p>Способ 6. Обозначим Vₖ событие, что A сильнейшая среди первых k+1 команд, а Vₖ₊₁ — сильнейшая среди первых k+2. Второе событие содержится в первом. По симметрии и формуле условной вероятности:</p>"
    html += line(rf"P(V_k)=\frac1{{{k + 1}}},\quad P(V_{{k+1}})=\frac1{{{k + 2}}}")
    html += line(
        rf"P(V_{{k+1}}\mid V_k)=\frac{{P(V_{{k+1}})}}{{P(V_k)}}=\frac1{{{k + 2}}}:\frac1{{{k + 1}}}={fmt(value)}"
    )
    answer, html = result(value, html)
    return diagrams.repair(condition, answer_section, solution, answer, html, keys)
